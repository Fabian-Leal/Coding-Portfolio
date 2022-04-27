from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django_ajax.decorators import ajax
from os.path import join
from scmix.celery import app
from scmix.choices import PlanStatus
from specialevents.models import SpecialEventsPlan, DriverTask
from specialevents.tasks import detect_specialevents
from xlsxwriter.workbook import Workbook
import io, json, pandas as pd

days_parameters = ['days_min', 'days_max', 'days_step']
sensitivity_parameters = ['sensitivity_min', 'sensitivity_max', 'sensitivity_step']


@login_required
def index(request):
    plans = SpecialEventsPlan.objects.all()
    return render(request, 'specialevents/index.html', {'plans': plans})


@login_required
def new_plan(request):
    if request.method == 'POST':
        data = request.POST
        parameters = {}
        for iter_parameter in days_parameters:
            parameters[iter_parameter] = int(data[iter_parameter])
        for iter_parameter in sensitivity_parameters:
            parameters[iter_parameter] = float(data[iter_parameter])
        df = pd.read_excel(request.FILES['events'])
        drivers = list(df.columns)
        drivers.remove('FECHA')
        #stores = data.getlist('store')
        if len(drivers) == 0:
            messages.error(request, "No se seleccionaron drivers")
            return render(request, 'specialevents/new-plan.html', {})
        if " - " not in data['range']:
            messages.error(request, "Error en la deteccion de fechas")
            return render(request, 'specialevents/new-plan.html', {})
        range_list = data['range'].split(' - ')
        parameters['start_date'] = range_list[0]
        parameters['end_date'] = range_list[1]
        plan = SpecialEventsPlan.objects.create(
            name=data['name'],
            parameters=json.dumps(parameters),
            events_attach=request.FILES['events'],
            company=request.user.company,
            created_by=request.user
        )
        df = pd.read_excel(plan.events_attach)
        first_row = 0
        driver = df['DRIVER'].iloc[0]
        rows = len(df['DRIVER'])
        i = 0
        for value in df['DRIVER']:
            if value != driver:
                driver = value
                first_row = i
            if ((i + 1) < rows and driver != df['DRIVER'].iloc[i + 1]) or ((i + 1) == rows):
                last_row = i + 1
                task = DriverTask.objects.create(
                    plan=plan,
                    name=driver,
                    first_row=first_row,
                    last_row=last_row
                )
                res = detect_specialevents.delay(task.id)
                task.celery_task_id = res.id
                task.save()
            i += 1
        #for driver in drivers:
        #    task = DriverTask.objects.create(
        #        plan=plan,
        #        name=driver
        #    )
        #    res = detect_specialevents.delay(task.id)
        #    task.celery_task_id = res.id
        #    task.save()
        messages.success(request, "La tarea se creo exitosamente")
        return redirect('specialevents:plan_detail', plan.id)
    return render(request, 'specialevents/new-plan.html', {})


@login_required
def plan_detail(request, plan_id):
    plan = SpecialEventsPlan.objects.get(id=plan_id)
    parameters = json.loads(plan.parameters)
    return render(request, 'specialevents/plan-detail.html', {
        'plan': plan,
        'parameters': parameters
    })


@login_required
def plan_results(request, plan_id):
    plan = SpecialEventsPlan.objects.get(id=plan_id)
    drivers = plan.drivers.exclude(results='').order_by('name')
    if drivers:
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        workbook = writer.book
        col_format = workbook.add_format({'num_format': '0.00%'})
        if ('format' in request.GET) and (request.GET['format'] == 'one-sheet'):
            worksheet = None
            i = 0
            for driver in drivers:
                absolute_path = join(settings.MEDIA_ROOT, driver.results.name)
                df = pd.read_excel(absolute_path, sheet_name='Resumen')
                df.to_excel(writer, sheet_name='Resultados', index=False, startrow=1, startcol=i*3)
                if worksheet is None:
                    worksheet = writer.sheets['Resultados']
                worksheet.write(0, i*3, driver.name)
                worksheet.set_column(2+(i*3), 2+(i*3), None, col_format)
                i += 1
        else:
            for driver in drivers:
                absolute_path = join(settings.MEDIA_ROOT, driver.results.name)
                df = pd.read_excel(absolute_path, sheet_name='Resumen')
                df.to_excel(writer, sheet_name=driver.name[:31], index=False)
                worksheet = writer.sheets[driver.name[:31]]
                worksheet.set_column('C2:C', None, col_format)
        writer.save()
        response = HttpResponse(output.getvalue(),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response['Content-Disposition'] = "attachment; filename=" + plan.name + '.xlsx'
        return response
    messages.error(request, "No se encontraron resultados")
    return redirect('specialevents:plan_detail', plan_id)


@login_required
def cancel_plan(request, plan_id):
    plan = SpecialEventsPlan.objects.get(id=plan_id)
    drivers = plan.drivers.all()
    for driver in drivers:
        try:
            app.control.revoke(driver.celery_task_id, terminate=True)
        except:
            pass
    plan.status = PlanStatus.CANCELLED.value
    plan.save()
    messages.info(request, "Se cancelaron las tareas planificadas")
    return redirect('specialevents:plan_detail', plan_id)


@ajax
@login_required
def cancel_task(request, task_id):
    task = DriverTask.objects.get(id=task_id)
    try:
        app.control.revoke(task.celery_task_id, terminate=True)
        plan = task.plan
        plan.status = PlanStatus.CANCELLED.value
        plan.save()
    except:
        return {'status': 'Error', 'message': 'Error al cancelar la tarea'}
    return {'status': 'Success', 'message': 'Tarea cancelada exitosamente'}
