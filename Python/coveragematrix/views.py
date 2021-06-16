from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django_ajax.decorators import ajax
from os.path import join
from scmix.celery import app
from scmix.choices import PlanStatus
from coveragematrix.models import CoverageMatrixPlan, CoverageMatrixTask
from coveragematrix.tasks import run_coveragematrix
from xlsxwriter.workbook import Workbook
import io, json, pandas as pd


@login_required
def index(request):
    plans = CoverageMatrixPlan.objects.all()
    return render(request, 'coveragematrix/index.html', {'plans': plans})


@login_required
def new_plan(request):
    if request.method == 'POST':
        data = request.POST
        parameters = {}
        parameters['coverage_units'] = data.getlist('coverage_units')
        parameters['transaction_units'] = data.getlist('transaction_units')
        parameters['merge_coverage_units'] = data['merge_coverage_units'] == '1'
        parameters['merge_transaction_units'] = data['merge_transaction_units'] == '1'
        parameters['iterations'] = int(data['iterations'])
        if parameters['merge_coverage_units']:
            iter_coverage_units = ['Combinacion']
        else:
            iter_coverage_units = parameters['coverage_units']
        if parameters['merge_transaction_units']:
            iter_transaction_units = ['Combinacion']
        else:
            iter_transaction_units = parameters['transaction_units']
        parameters['merge_transaction_units'] = data['merge_transaction_units'] == '1'
        if " - " not in data['range']:
            messages.error(request, "Error en la deteccion de fechas")
            return render(request, 'specialevents/new-plan.html', {})
        range_list = data['range'].split(' - ')
        parameters['start_date'] = range_list[0]
        parameters['end_date'] = range_list[1]
        plan = CoverageMatrixPlan.objects.create(
            name=data['name'],
            parameters=json.dumps(parameters),
            coverage_attach=request.FILES['coverage'],
            transactions_attach=request.FILES['transactions'],
            company=request.user.company,
            created_by=request.user
        )
        df = pd.read_excel(plan.coverage_attach)
        sites = df['Sucursal'].unique()
        for site in sites:
            for coverage_unit in iter_coverage_units:
                for transaction_unit in iter_transaction_units:
                    aux_parameters = {
                        'coverage_unit': coverage_unit,
                        'transaction_unit': transaction_unit
                    }
                    task = CoverageMatrixTask.objects.create(
                        plan=plan,
                        name=site,
                        parameters=json.dumps(aux_parameters)
                    )
                    res = run_coveragematrix.delay(task.id)
                    task.celery_task_id = res.id
                    task.save()
        messages.success(request, "La tarea se creo exitosamente")
        return redirect('coveragematrix:plan_detail', plan.id)
    return render(request, 'coveragematrix/new-plan.html', {})


@login_required
def plan_detail(request, plan_id):
    plan = CoverageMatrixPlan.objects.get(id=plan_id)
    parameters = json.loads(plan.parameters)
    return render(request, 'coveragematrix/plan-detail.html', {
        'plan': plan,
        'parameters': parameters
    })


@login_required
def plan_results(request, plan_id):
    plan = CoverageMatrixPlan.objects.get(id=plan_id)
    tasks = plan.tasks.exclude(results='').order_by('name')
    if tasks:
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        results = tasks.first().results
        columns = len(results[1:-1].split(','))
        data = []
        for task in tasks:
            results = task.results[1:-1].split(',')
            results.insert(0, task.name)
            results.insert(1, task.get_coverage_unit())
            results.insert(2, task.get_transaction_unit())
            data.append(results)
        columns_list = ['Tienda', 'Unidad de cobertura', 'Unidad de transaccion']
        for i in range(columns):
            columns_list.append(i+1)
        df = pd.DataFrame(data, columns=columns_list)
        df.to_excel(writer, sheet_name='Resultados', index=False)
        writer.save()
        response = HttpResponse(output.getvalue(),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response['Content-Disposition'] = "attachment; filename=" + plan.name + '.xlsx'
        return response
    messages.error(request, "No se encontraron resultados")
    return redirect('coveragematrix:plan_detail', plan_id)


@login_required
def cancel_plan(request, plan_id):
    plan = CoverageMatrixPlan.objects.get(id=plan_id)
    tasks = plan.tasks.all()
    for task in tasks:
        try:
            app.control.revoke(task.celery_task_id, terminate=True)
        except:
            pass
    plan.status = PlanStatus.CANCELLED.value
    plan.save()
    messages.info(request, "Se cancelaron las tareas planificadas")
    return redirect('coveragematrix:plan_detail', plan_id)


@ajax
@login_required
def cancel_task(request, task_id):
    task = CoverageMatrixTask.objects.get(id=task_id)
    try:
        app.control.revoke(task.celery_task_id, terminate=True)
        plan = task.plan
        plan.status = PlanStatus.CANCELLED.value
        plan.save()
    except:
        return {'status': 'Error', 'message': 'Error al cancelar la tarea'}
    return {'status': 'Success', 'message': 'Tarea cancelada exitosamente'}
