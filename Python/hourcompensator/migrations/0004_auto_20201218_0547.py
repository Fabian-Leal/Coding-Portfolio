# Generated by Django 3.0.7 on 2020-12-18 05:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hourcompensator', '0003_auto_20201126_1642'),
    ]

    operations = [
        migrations.AddField(
            model_name='hourcompensatortask',
            name='delete_request',
            field=models.FileField(blank=True, default=None, null=True, upload_to='hourcompensator/http/'),
        ),
        migrations.AddField(
            model_name='hourcompensatortask',
            name='delete_response',
            field=models.FileField(blank=True, default=None, null=True, upload_to='hourcompensator/http/'),
        ),
        migrations.AddField(
            model_name='hourcompensatortask',
            name='shift_request',
            field=models.FileField(blank=True, default=None, null=True, upload_to='hourcompensator/http/'),
        ),
        migrations.AddField(
            model_name='hourcompensatortask',
            name='shift_response',
            field=models.FileField(blank=True, default=None, null=True, upload_to='hourcompensator/http/'),
        ),
    ]
