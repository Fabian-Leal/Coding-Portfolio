# Generated by Django 3.0.7 on 2020-11-26 16:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hourcompensator', '0002_auto_20201031_0127'),
    ]

    operations = [
        migrations.AddField(
            model_name='hourcompensatortask',
            name='absences_request',
            field=models.FileField(blank=True, default=None, null=True, upload_to='hourcompensator/http/'),
        ),
        migrations.AddField(
            model_name='hourcompensatortask',
            name='absences_response',
            field=models.FileField(blank=True, default=None, null=True, upload_to='hourcompensator/http/'),
        ),
        migrations.AddField(
            model_name='hourcompensatortask',
            name='unlock_request',
            field=models.FileField(blank=True, default=None, null=True, upload_to='hourcompensator/http/'),
        ),
        migrations.AddField(
            model_name='hourcompensatortask',
            name='unlock_response',
            field=models.FileField(blank=True, default=None, null=True, upload_to='hourcompensator/http/'),
        ),
        migrations.AlterField(
            model_name='hourcompensatortask',
            name='compensated_schedules_results',
            field=models.FileField(blank=True, default=None, null=True, upload_to='hourcompensator/output/compensated_schedules/'),
        ),
        migrations.AlterField(
            model_name='hourcompensatortask',
            name='curves_results',
            field=models.FileField(blank=True, default=None, null=True, upload_to='hourcompensator/output/curves/'),
        ),
        migrations.AlterField(
            model_name='hourcompensatortask',
            name='fixed_curves_results',
            field=models.FileField(blank=True, default=None, null=True, upload_to='hourcompensator/output/fixed_curves/'),
        ),
    ]