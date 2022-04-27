from celery import shared_task
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from os.path import join
from scmix.choices import PlanStatus
from scmix.utils import send_plan_finished_email
from coveragematrix.main import CoverageMatrix
from coveragematrix.models import CoverageMatrixTask
import json, pandas as pd, time, traceback


@shared_task(name='run-coveragematrix', bind=True)
def run_coveragematrix(self, task_id):
    time.sleep(1)
    task = CoverageMatrixTask.objects.get(id=task_id)
    task.started_at = timezone.now()
    task.save()
    plan = task.plan
    if plan.status == PlanStatus.PENDING.value:
        plan.status = PlanStatus.STARTED.value
        plan.save()
    try:
        self.update_state(state='RUNNING')
        parameters = json.loads(plan.parameters)
        parameters.update(json.loads(task.parameters))
        df1 = pd.read_excel(plan.coverage_attach, converters={'Sucursal':str})
        df1.columns = df1.columns.astype(str)
        df2 = pd.read_excel(plan.transactions_attach, converters={'Sucursal':str})
        df2.columns = df2.columns.astype(str)
        matrix_instance = CoverageMatrix(parameters, [df1, df2], task.name)
        matrix_instance.run()
        self.update_state(state='FINISHED')
        task.results = matrix_instance.results
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
        send_plan_finished_email(plan, reverse('coveragematrix:plan_detail', kwargs={'plan_id': plan.id}))
