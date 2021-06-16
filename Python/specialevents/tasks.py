from celery import shared_task
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from os.path import join
from scmix.choices import PlanStatus
from scmix.utils import send_plan_finished_email
from specialevents.main import SpecialEvents
from specialevents.models import DriverTask
import json, pandas as pd, time, traceback


@shared_task(name='detect-specialevents', bind=True)
def detect_specialevents(self, task_id):
    time.sleep(1)
    task = DriverTask.objects.get(id=task_id)
    task.started_at = timezone.now()
    task.save()
    plan = task.plan
    if plan.status == PlanStatus.PENDING.value:
        plan.status = PlanStatus.STARTED.value
        plan.save()
    try:
        self.update_state(state='LOADING_PARAMETERS')
        parameters = json.loads(plan.parameters)
        df = pd.read_excel(plan.events_attach)
        df = df.iloc[task.first_row:task.last_row, :]
        driver_instance = SpecialEvents(parameters, df, task.name)
        self.update_state(state='RUNNING')
        driver_instance.run()
        self.update_state(state='FINISHED')
        results = driver_instance.results
        keys = list(results.keys())
        keys.sort()
        if keys:
            path = join('specialevents', 'results', str(task_id) + '.xlsx')
            absolute_path = join(settings.MEDIA_ROOT, path)
            writer = pd.ExcelWriter(absolute_path, engine='xlsxwriter')
            for key in keys:
                if key == 'Resumen':
                    results[key].to_excel(writer, sheet_name=key, index=False)
                    workbook = writer.book
                    worksheet = writer.sheets['Resumen']
                    format = workbook.add_format({'num_format': '0.00%'})
                    worksheet.set_column('C2:C', None, format)
                else:
                    results[key].to_excel(writer, sheet_name=key)
            writer.save()
            writer.close()
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
    unfinished_tasks = plan.drivers.filter(finished=False).count()
    if unfinished_tasks == 0:
        plan.ended_at = timezone.now()
        if plan.status == PlanStatus.STARTED.value:
            plan.status = PlanStatus.FINISHED.value
        plan.save()
        send_plan_finished_email(plan, reverse('specialevents:plan_detail', kwargs={'plan_id': plan.id}))
