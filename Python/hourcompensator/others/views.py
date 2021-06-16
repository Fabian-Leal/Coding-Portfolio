from accounts.models import Manager
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from hourcompensator.models import HourCompensatorPlan, HourCompensatorTask, HourCompensatorParameter
from hourcompensator.tasks import run_hour_compensator
from os.path import join
import datetime, json, io, pandas as pd, os

case_parameters = ['holgura_critica', 'limite_corte', 'comp_max', 'hh_ee_max', 'turno_minimo',
                   'k_a', 'maximo_compensacion_dia']


@login_required
def index(request):
    plans = HourCompensatorPlan.objects.all()
    return render(request, 'hourcompensator/index.html', {'plans': plans})


@login_required
def plan_detail(request, plan_id):
    plan = HourCompensatorPlan.objects.get(id=plan_id)
    parameters = json.loads(plan.parameters)
    return render(request, 'hourcompensator/plan-detail.html', {
        'plan': plan,
        'parameters': parameters,
        'current_sunday': datetime.datetime.strptime(parameters['current_sunday'], '%Y-%m-%d').date(),
        'range_start': datetime.datetime.strptime(parameters['range_start'], '%Y-%m-%d').date(),
        'range_end': datetime.datetime.strptime(parameters['range_end'], '%Y-%m-%d').date()
    })


@login_required
def task_detail(request, plan_id, task_id):
    task = HourCompensatorTask.objects.get(id=task_id)
    parameters = json.loads(task.plan.parameters)
    parameters.update(json.loads(task.parameters))
    warnings = json.loads(task.execution_warning)
    show_warning_tab = False
    for kind in ['curve', 'schedule', 'amount']:
        if kind in warnings and len(warnings[kind]) > 0:
            show_warning_tab = True
            break
    return render(request, 'hourcompensator/task-detail.html', {
        'task': task,
        'parameters': parameters,
        'warnings': warnings,
        'show_warning_tab': show_warning_tab,
        'current_sunday': datetime.datetime.strptime(parameters['current_sunday'], '%Y-%m-%d').date(),
        'range_start': datetime.datetime.strptime(parameters['range_start'], '%Y-%m-%d').date(),
        'range_end': datetime.datetime.strptime(parameters['range_end'], '%Y-%m-%d').date()
    })


@csrf_exempt
def run_plan(request):
    data = request.body.decode('utf-8')
    parameters_list = data.split('&')
    data_dict = {}
    for parameter in parameters_list:
        aux_var = parameter.split('=')
        data_dict[aux_var[0]] = aux_var[1]
    if request.method == 'POST' and data_dict['authorization'] == '25ryECjDP8hWdH3v':
        manager_id = int(data_dict['manager_id'])
        manager = Manager.objects.get(id=manager_id)
        if 'date' in data_dict:
            pivot = datetime.datetime.strptime(data_dict['date'], '%Y-%m-%d').date()
        else:
            pivot = datetime.date.today()
        current_sunday = pivot + datetime.timedelta(days=6-pivot.weekday())
        next_monday = current_sunday + datetime.timedelta(days=1)
        next_sunday = next_monday + datetime.timedelta(days=6)
        parameters_ids = data_dict['parameters_ids'].split('-')
        parameters = {
            'current_sunday': current_sunday.strftime('%Y-%m-%d'),
            'range_start': next_monday.strftime('%Y-%m-%d'),
            'range_end': next_sunday.strftime('%Y-%m-%d')
        }
        parameters_str = json.dumps(parameters)
        plan = HourCompensatorPlan.objects.create(
            name=str(pivot),
            company=manager.company,
            created_by=manager,
            parameters=parameters_str
        )
        for parameter_id in parameters_ids:
            parameters_object = HourCompensatorParameter.objects.get(id=int(parameter_id))
            task = HourCompensatorTask.objects.create(plan=plan, name=parameters_object.name,
                                                      parameters=parameters_object.parameters)
            res = run_hour_compensator.delay(task.id)
            task.celery_task_id = res.id
            task.save()
        return HttpResponse('Inicio ejecucion de la tarea')
    return HttpResponse('Request incorrecta')


@login_required
def plan_results(request, plan_id):
    plan = HourCompensatorPlan.objects.get(id=plan_id)
    tasks = plan.tasks.exclude(main_results='').order_by('name')
    if tasks:
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df1 = pd.DataFrame()
        df2 = pd.DataFrame()
        df3 = pd.DataFrame()
        df4 = pd.DataFrame()
        for task in tasks:
            absolute_path = join(settings.MEDIA_ROOT, task.main_results.name)
            dict_df = pd.read_excel(absolute_path, sheet_name=None)
            df1 = df1.append(dict_df['Curva de horarios'], ignore_index=True)
            df2 = df2.append(dict_df['HorariosCompensados'], ignore_index=True)
            df3 = df3.append(dict_df['HorariosCompensadosDetalle'], ignore_index=True)
            df4 = df4.append(dict_df['HHEE'], ignore_index=True)
        df1.to_excel(writer, sheet_name='Curva de horarios', index=False)
        df2.to_excel(writer, sheet_name='HorariosCompensados', index=False)
        df3.to_excel(writer, sheet_name='HorariosCompensadosDetalle', index=False)
        df4.to_excel(writer, sheet_name='HHEE')
        writer.save()
        response = HttpResponse(output.getvalue(),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response['Content-Disposition'] = "attachment; filename=Resultados-" + plan.name + '.xlsx'
        return response
    messages.error(request, "No se encontraron resultados")
    return redirect('specialevents:plan_detail', plan_id)
