from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django_ajax.decorators import ajax
from optimalmix.tasks import run_mix
from optimalmix.models import MixPlan, MixTask
from optimalmix.utils import get_parameters_dict, adjust_mix_parameters
from optimalmix.variables import SHIFT_PARAMETERS_LABELS, SHIFT_BOOLEAN_PARAMETERS_LABELS
from scmix.celery import app
from scmix.choices import PlanStatus
import ast, csv, datetime, io, json, pandas as pd

shift_parameters = ['salario', 'largosem', 'largomen', 'cotainf', 'cotasup', 'diaslabmin',
                    'diaslabmax', 'zcero', 'productividad', 'ausentismo', 'rotacion', 'contrato',
                    'despido']
shift_boolean_parameters = ['Turnoshx', 'Turnoslegales']
scalar_parameters = ['ppto', 'sobrecargo', 'cu', 'co', 'slmin', 'opmin', 'opmax',
                     'SemCambioDotacion', 'horasmensual', 'mip_gap', 'days_cycle']
timerange_parameters = ['open_start_time', 'open_end_time', 'close_start_time', 'close_end_time']


@login_required
def index(request):
    plans = MixPlan.objects.all()
    return render(request, 'optimalmix/index.html', {'plans': plans})


@login_required
def new_plan(request):
    if request.method == 'POST':
        data = request.POST
        i = 0
        shifts = []
        iter_str = 'shift[{}]'.format(i)
        while iter_str in data:
            shifts.append(data[iter_str])
            i += 1
            iter_str = 'shift[{}]'.format(i)
        parameters = {}
        if i <= 0:
            messages.error(request, 'No se seleccionaron turnos')
            return render(request, 'optimalmix/new-plan.html', {})
        df = None
        if request.FILES['parameters']:
            df = pd.read_excel(request.FILES['parameters'])
            parameters = get_parameters_dict(df, 'General')
            adjust_mix_parameters(parameters)
        else:
            parameters['Turnos'] = shifts
            for iter_parameter in shift_parameters:
                aux_dict = {}
                for shift in shifts:
                    aux_dict[shift] = float(data[iter_parameter + '[' + shift + ']'])
                parameters[iter_parameter] = aux_dict
            for iter_parameter in shift_boolean_parameters:
                parameters[iter_parameter] = data.getlist(iter_parameter)
            for iter_parameter in scalar_parameters:
                parameters[iter_parameter] = float(data[iter_parameter])
        stores = data.getlist('store')
        parameters['time_shifts'] = int(data['time_shifts'])
        #parameters['weekday_kind'] = data['timerange_kind'] == "1"
        #if not parameters['weekday_kind']:
        #    for parameter in timerange_parameters:
        #        parameters[parameter] = []
        #        i = 0
        #        while True:
        #            parameter_key = parameter + '[{}]'.format(i)
        #            if parameter_key in data:
        #                parameters[parameter].append(data[parameter_key])
        #            else:
        #                break
        #            i += 1
        #else:
        #    for parameter in timerange_parameters:
        #        parameters[parameter] = []
        #    for i in range(7):
        #        for parameter in timerange_parameters:
        #            parameters[parameter].append(data[parameter+'[{}][0]'.format(i)])
        if len(stores) == 0:
            messages.error(request, "No se seleccionaron tiendas")
            return render(request, 'optimalmix/new-plan.html', {})
        if " - " not in data['range'] or len(data['sheet_start_date']) == 0 or len(data['sheet_end_date']) == 0:
            messages.error(request, "Error en la deteccion de fechas")
            return render(request, 'optimalmix/new-plan.html', {})
        range_list = data['range'].split(' - ')
        parameters['start_date'] = range_list[0]
        start_date = datetime.datetime.strptime(parameters['start_date'], '%d/%m/%Y').date()
        parameters['end_date'] = range_list[1]
        end_date = datetime.datetime.strptime(parameters['end_date'], '%d/%m/%Y').date()
        #start_weekday = start_date.weekday()
        #end_weekday = end_date.weekday()
        #offset = ((end_weekday-start_weekday+1)%7)
        #if offset != 0:
        #    end_date = end_date - datetime.timedelta(days=offset)
        parameters['end_date'] = end_date.strftime('%d/%m/%Y')
        parameters['sheet_start_date'] = data['sheet_start_date']
        parameters['sheet_end_date'] = data['sheet_end_date']
        plan = MixPlan.objects.create(
            name=data['name'],
            parameters=json.dumps(parameters),
            demand_attach=request.FILES['demand'],
            parameters_attach=request.FILES['parameters'],
            company=request.user.company,
            created_by=request.user
        )
        for store in stores:
            if df is not None:
                store_parameters = get_parameters_dict(df, store)
            else:
                store_parameters = '{}'
            task = MixTask.objects.create(
                plan=plan,
                store=store,
                parameters=json.dumps(store_parameters)
            )
            res = run_mix.delay(task.id)
            task.celery_task_id = res.id
            task.save()
        messages.success(request, "La tarea se creo exitosamente")
        return redirect('optimalmix:plan_detail', plan.id)
    return render(request, 'optimalmix/new-plan.html', {})


@login_required
def plan_detail(request, plan_id):
    plan = MixPlan.objects.get(id=plan_id)
    parameters = json.loads(plan.parameters)
    return render(request, 'optimalmix/plan-detail.html', {
        'plan': plan,
        'parameters': parameters,
        'shift_parameters': SHIFT_PARAMETERS_LABELS,
        'scalar_parameters': scalar_parameters,
        'shift_boolean_parameters': SHIFT_BOOLEAN_PARAMETERS_LABELS,
        'tasks_with_results': plan.tasks.exclude(results='')
    })


@login_required
def task_detail(request, plan_id, task_id):
    task = MixTask.objects.get(id=task_id)
    parameters = json.loads(task.plan.parameters)
    parameters.update(json.loads(task.parameters))
    adjust_mix_parameters(parameters)
    return render(request, 'optimalmix/task-detail.html', {
        'task': task,
        'parameters': parameters,
        'shift_parameters': SHIFT_PARAMETERS_LABELS,
        'scalar_parameters': scalar_parameters,
        'shift_boolean_parameters': SHIFT_BOOLEAN_PARAMETERS_LABELS
    })


@login_required
def cancel_plan(request, plan_id):
    plan = MixPlan.objects.get(id=plan_id)
    tasks = plan.tasks.all()
    for task in tasks:
        try:
            app.control.revoke(task.celery_task_id, terminate=True)
        except:
            pass
    plan.status = PlanStatus.CANCELLED.value
    plan.save()
    messages.info(request, "Se cancelaron las tareas planificadas")
    return redirect('optimalmix:plan_detail', plan_id)


@ajax
@login_required
def cancel_task(request, task_id):
    task = MixTask.objects.get(id=task_id)
    try:
        app.control.revoke(task.celery_task_id, terminate=True)
        plan = task.plan
        plan.status = PlanStatus.CANCELLED.value
        plan.save()
    except:
        return {'status': 'Error', 'message': 'Error al cancelar la tarea'}
    return {'status': 'Success', 'message': 'Tarea cancelada exitosamente'}


#@login_required
#def task_results(request, task_id):
#    task = MixTask.objects.get(id=task_id)
#    response = HttpResponse(content_type='text/csv')
#    response['Content-Disposition'] = 'attachment; filename="' + task.store + '.csv"'
#    list_of_results = ast.literal_eval(task.results)
#    writer = csv.writer(response)
#    for row in list_of_results:
#        writer.writerow(row)
#    return response


@login_required
def plan_parameters(request, plan_id):
    plan = MixPlan.objects.get(id=plan_id)
    if plan.parameters:
        parameters = json.loads(plan.parameters)
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        shifts = parameters['Turnos']
        sheet_values = []
        for iter_parameter in shift_parameters:
            aux_dict = {'Turnos': iter_parameter}
            for shift in shifts:
                if iter_parameter in parameters and shift in parameters[iter_parameter]:
                    tmp_value = parameters[iter_parameter][shift]
                    aux_dict[shift] = int(tmp_value) if tmp_value.is_integer() else tmp_value
                else:
                    aux_dict[shift] = None
            sheet_values.append(aux_dict)
        for iter_parameter in shift_boolean_parameters:
            aux_dict = {'Turnos': iter_parameter}
            for shift in shifts:
                if iter_parameter in parameters and shift in parameters[iter_parameter]:
                    aux_dict[shift] = "Si"
                else:
                    aux_dict[shift] = "No"
            sheet_values.append(aux_dict)
        for iter_parameter in scalar_parameters:
            aux_dict = {'Turnos': iter_parameter}
            tmp_value = parameters.get(iter_parameter)
            if tmp_value is not None:
                aux_dict[shifts[0]] = int(tmp_value) if tmp_value.is_integer() else tmp_value
            else:
                aux_dict[shifts[0]] = None
            sheet_values.append(aux_dict)
        #for iter_parameter in constraint_parameters:
        #    aux_dict = {
        #        'Turnos': iter_parameter,
        #        shifts[0]: "Si" if parameters.get(iter_parameter) else "No"
        #    }
        #    sheet_values.append(aux_dict)
        df = pd.DataFrame(sheet_values)
        df.to_excel(writer, sheet_name="Parametros", index=False)
        writer.save()
        response = HttpResponse(output.getvalue(),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response['Content-Disposition'] = "attachment; filename=Parametros-" + plan.name + '.xlsx'
        return response
    messages.error(request, "No se encontraron resultados")
    return redirect('optimalmix:plan_detail:plan_detail', plan_id)
