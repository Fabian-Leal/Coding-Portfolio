from django.contrib import admin
from hourcompensator.models import HourCompensatorPlan, HourCompensatorTask, HourCompensatorParameter

admin.site.register(HourCompensatorPlan)
admin.site.register(HourCompensatorTask)
admin.site.register(HourCompensatorParameter)
