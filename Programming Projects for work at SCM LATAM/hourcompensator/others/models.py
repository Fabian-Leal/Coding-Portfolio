from celery.result import AsyncResult
from django.db import models
from scmix.choices import PlanStatus
from scmix.spanish_choices import BOOTSTRAP_SPANISH_PLAN_STATUS, BOOTSTRAP_THREAD_STATUS_SPANISH_DICT


class HourCompensatorPlan(models.Model):
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='hour_compensator_plans')
    name = models.CharField(max_length=32)
    status = models.CharField(max_length=1, choices=PlanStatus.as_django_tuples(), default=PlanStatus.PENDING.value)
    parameters = models.TextField()
    curve_attach = models.FileField(upload_to='hourcompensator/input/curve/', blank=True, null=True, default=None)
    schedule_attach = models.FileField(upload_to='hourcompensator/input/schedule/', blank=True, null=True, default=None)
    amount_attach = models.FileField(upload_to='hourcompensator/input/amount/', blank=True, null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True, default=None)
    created_by = models.ForeignKey('accounts.Manager', on_delete=models.SET_NULL, blank=True, null=True, default=None)

    def get_status_bootstrap(self):
        return BOOTSTRAP_SPANISH_PLAN_STATUS.get(self.status)

    def has_results(self):
        return self.tasks.exclude(main_results='').count() > 0

    def __str__(self):
        return "{}| name:{}".format(self.id, self.name)

    class Meta:
        db_table = 'HourCompensatorPlan'


class HourCompensatorTask(models.Model):
    plan = models.ForeignKey(HourCompensatorPlan, on_delete=models.CASCADE, related_name='tasks')
    name = models.CharField(max_length=32, default='')
    finished = models.BooleanField(default=False)
    parameters = models.TextField(default='')
    execution_warning = models.TextField(default='{}')
    curve_attach = models.FileField(upload_to='hourcompensator/input/', blank=True, null=True,
                                    default=None)
    schedule_attach = models.FileField(upload_to='hourcompensator/input/', blank=True, null=True,
                                       default=None)
    amount_attach = models.FileField(upload_to='hourcompensator/input/', blank=True, null=True,
                                     default=None)
    curves_results = models.FileField(upload_to='hourcompensator/output/curves/', blank=True,
                                      null=True, default=None)
    compensated_schedules_results = models.FileField(
        upload_to='hourcompensator/output/compensated_schedules/', blank=True, null=True,
        default=None)
    main_results = models.FileField(
        upload_to='hourcompensator/output/', blank=True, null=True, default=None)
    fixed_curves_results = models.FileField(upload_to='hourcompensator/output/fixed_curves/',
                                            blank=True, null=True, default=None)
    unlock_request = models.FileField(upload_to='hourcompensator/http/', blank=True, null=True,
                                      default=None)
    unlock_response = models.FileField(upload_to='hourcompensator/http/', blank=True, null=True,
                                       default=None)
    absences_request = models.FileField(upload_to='hourcompensator/http/', blank=True, null=True,
                                        default=None)
    absences_response = models.FileField(upload_to='hourcompensator/http/', blank=True, null=True,
                                         default=None)
    delete_request = models.FileField(upload_to='hourcompensator/http/', blank=True, null=True,
                                      default=None)
    delete_response = models.FileField(upload_to='hourcompensator/http/', blank=True, null=True,
                                       default=None)
    shift_request = models.FileField(upload_to='hourcompensator/http/', blank=True, null=True,
                                     default=None)
    shift_response = models.FileField(upload_to='hourcompensator/http/', blank=True, null=True,
                                      default=None)
    lock_request = models.FileField(upload_to='hourcompensator/http/', blank=True, null=True,
                                    default=None)
    lock_response = models.FileField(upload_to='hourcompensator/http/', blank=True, null=True,
                                     default=None)
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
        return "{}| name:{}, plan:{}".format(self.id, self.name, self.plan)

    class Meta:
        db_table = 'HourCompensatorTask'


class HourCompensatorParameter(models.Model):
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='hour_compensator_parameters')
    name = models.CharField(max_length=32)
    parameters = models.TextField()

    def __str__(self):
        return "{}| name:{}".format(self.id, self.name)

    class Meta:
        db_table = 'HourCompensatorParameter'
