from celery import shared_task
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from os.path import join
from scmix.choices import PlanStatus
from scmix.utils import send_plan_finished_email
from optimalmix.mix import OptimalMix
from optimalmix.models import MixTask
import datetime, gc, json, pandas as pd, time, traceback
from optimalmix.utils import prepare_output, adjust_mix_parameters


@shared_task(name='run-mix', bind=True)
def run_mix(self, task_id):
    time.sleep(1)
    task = MixTask.objects.get(id=task_id)
    task.started_at = timezone.now()
    task.save()
    plan = task.plan
    if plan.status == PlanStatus.PENDING.value:
        plan.status = PlanStatus.STARTED.value
        plan.save()
    try:
        self.update_state(state='LOADING_PARAMETERS')
        parameters = json.loads(plan.parameters)
        parameters.update(json.loads(task.parameters))
        adjust_mix_parameters(parameters)
        start_date = datetime.datetime.strptime(parameters['start_date'], '%d/%m/%Y').date()
        end_date = datetime.datetime.strptime(parameters['end_date'], '%d/%m/%Y').date()
        days_cycle = int(parameters['days_cycle'])
        iter_start = start_date
        df = pd.read_excel(plan.demand_attach, converters={'Tienda':str})
        df = df.loc[df['Tienda'] == task.store]
        self.update_state(state='OPTIMIZING')
        offset = 0
        solution_dict = {}
        solution = []
        zcero = parameters['zcero']
        while iter_start <= end_date:
            iter_end = iter_start + datetime.timedelta(days=days_cycle-1)
            if end_date < iter_end:
                iter_end = end_date
            else:
                iter_start_future = iter_end + datetime.timedelta(days=1)
                iter_end_future = iter_start_future + datetime.timedelta(days=days_cycle - 1)
                if end_date < iter_end_future:
                    iter_end_future = end_date
                    if (iter_end_future - iter_start_future).days < 28:
                        iter_end = iter_end_future
            iter_parameters = parameters.copy()
            iter_parameters['start_date'] = iter_start.strftime('%d/%m/%Y')
            iter_parameters['end_date'] = iter_end.strftime('%d/%m/%Y')
            iter_parameters['zcero'] = zcero
            mix = OptimalMix(iter_parameters)
            gc.collect()
            mix.load_demand(df)
            mix.load_constrains()
            mix.run_mix()
            time_range = [i for i in range(1, mix.LargoDia*((iter_end-iter_start).days+1)+1)]
            for v in ['z', 'x', 'hx', 'hc', 'hxacum', 'hxv', 'ingreso', 'nuevoscontratos',
                      'nuevosdespidos', 'egreso', 'oferta']:
                for shift in mix.Turnos:
                    for t in time_range:
                        varname = '{}[{},{}]'.format(v, t + offset, shift)
                        solution_dict[varname] = mix.solution_dict['{}[{},{}]'.format(v, t, shift)]
                        solution.append((varname, solution_dict[varname]))
            for v in ['ymas', 'ymenos']:
                for t in time_range:
                    varname = '{}[{}]'.format(v, t + offset)
                    solution_dict[varname] = mix.solution_dict['{}[{}]'.format(v, t)]
                    solution.append((varname, solution_dict[varname]))
            last_period = time_range[-1]
            print('last_period', last_period)
            print('offset', offset)
            for shift in mix.Turnos:
                zcero[shift] = solution_dict['z[{},{}]'.format(last_period + offset, shift)]
            iter_start = iter_end + datetime.timedelta(days=1)
            offset += last_period

        mix = OptimalMix(parameters)
        mix.load_demand(df)
        mix.load_constrains()
        dataframes = prepare_output(solution_dict, mix.Turnos, mix.LargoDia, start_date, end_date,
                                    mix.demanda, mix.G4Semini, mix.Turnoshx, mix.salario,
                                    mix.Periodos, mix.sobrecargo, mix.horasmensual, mix.contrato,
                                    mix.despido, mix.cu)
        self.update_state(state='FINISHED')
        #mix.prepare_output()
        path = join('optimalmix', 'results', str(task_id) + '.xlsx')
        absolute_path = join(settings.MEDIA_ROOT, path)
        writer = pd.ExcelWriter(absolute_path, engine='xlsxwriter')
        dataframes[0].to_excel(writer, sheet_name='Meses', index=False,
                              columns=['Rango inicio', 'Rango fin'] + mix.Turnos)
        dataframes[1].to_excel(writer, sheet_name='Semanas', index=False,
                             columns=['Rango inicio', 'Rango fin'] + mix.Turnos + ['hx', 'hc',
                                                                                   'oferta',
                                                                                   'ymenos',
                                                                                   'ymas',
                                                                                   'demanda'])
        dataframes[2].to_excel(writer, sheet_name='Periodos', index=False,
                               columns=['Periodo', 'Fecha'] + mix.Turnos + ['hx', 'hc', 'oferta',
                                                                            'ymenos', 'ymas', 'demanda'])
        df = pd.DataFrame(dataframes[3])
        df.to_excel(writer, sheet_name='Costos', index=False, header=False)
        df = pd.DataFrame(solution)
        df.to_excel(writer, sheet_name='Variables', index=False, header=False)
        writer.save()
        task.results.name = path
        task.save()
    except Exception as e:
        self.update_state(state='RAISE_EXC')
        task.error_stack_trace = traceback.format_exc()
        task.save()
        plan.status = PlanStatus.ERROR.value
        plan.save()
    task.finished = True
    task.ended_at = timezone.now()
    task.save()
    plan.refresh_from_db()
    unfinished_tasks = plan.tasks.filter(finished=False).count()
    if unfinished_tasks == 0:
        plan.ended_at = timezone.now()
        if plan.status == PlanStatus.STARTED.value:
            plan.status = PlanStatus.FINISHED.value
        plan.save()
        send_plan_finished_email(plan, reverse('optimalmix:plan_detail', kwargs={'plan_id': plan.id}))
