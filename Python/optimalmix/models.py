from celery.result import AsyncResult
from django.db import models
from scmix.choices import PlanStatus
from scmix.spanish_choices import BOOTSTRAP_SPANISH_PLAN_STATUS, BOOTSTRAP_THREAD_STATUS_SPANISH_DICT


class MixPlan(models.Model):
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='mix_plans')
    name = models.CharField(max_length=32)
    status = models.CharField(max_length=1, choices=PlanStatus.as_django_tuples(), default=PlanStatus.PENDING.value)
    parameters = models.TextField()
    demand_attach = models.FileField(upload_to='optimalmix/demands/')
    parameters_attach = models.FileField(upload_to='optimalmix/input/', null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True, default=None)
    created_by = models.ForeignKey('accounts.Manager', null=True, blank=True, on_delete=models.SET_NULL, related_name='mix_plans')

    def get_status_bootstrap(self):
        return BOOTSTRAP_SPANISH_PLAN_STATUS.get(self.status)

    def __str__(self):
        return "{}| name:{}".format(self.id, self.name)

    class Meta:
        db_table = 'MixPlan'


class MixTask(models.Model):
    plan = models.ForeignKey(MixPlan, on_delete=models.CASCADE, related_name='tasks')
    store = models.CharField(max_length=32)
    parameters = models.TextField(blank=True, default="{}")
    finished = models.BooleanField(default=False)
    results = models.FileField(upload_to='optimalmix/results/', blank=True, null=True, default=None)
    celery_task_id = models.CharField(max_length=64, blank=True, default="")
    error_stack_trace = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(blank=True, null=True, default=None)
    ended_at = models.DateTimeField(blank=True, null=True, default=None)

    def get_status_bootstrap(self):
        if self.finished:
            if self.error_stack_trace:
                return 'Error', 'danger'
            else:
                return 'Terminado', 'success'
        if self.celery_task_id:
            try:
                celery_task = AsyncResult(self.celery_task_id)
                celery_task_state = celery_task.state
                if celery_task_state in BOOTSTRAP_THREAD_STATUS_SPANISH_DICT:
                    thread_status = BOOTSTRAP_THREAD_STATUS_SPANISH_DICT[celery_task_state]
                else:
                    thread_status = (celery_task_state, 'info')
            except:
                thread_status = ('No obtenido', 'secondary')
        else:
            thread_status = ('Sin ID', 'secondary')
        return thread_status

    def show_cancel_btn(self):
        if not self.finished and self.celery_task_id:
            try:
                celery_task = AsyncResult(self.celery_task_id)
                celery_task_state = celery_task.state
                return celery_task_state in ['PENDING', 'RECEIVED', 'STARTED', 'LOADING_PARAMETERS', 'LOADING_CONSTRAINTS', 'OPTIMIZING']
            except:
                return False
        return False

    def __str__(self):
        return "{}| store:{}, plan:{}".format(self.id, self.store, self.plan)

    class Meta:
        db_table = 'MixTask'
