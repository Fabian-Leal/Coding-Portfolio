from celery import shared_task
from django.utils import timezone
from hourcompensator.models import HourCompensatorTask
from scmix.choices import PlanStatus
import json, pandas as pd, re, requests, traceback

from os.path import join
from django.urls import reverse
from django.conf import settings
from scmix.utils import send_plan_finished_email
from hourcompensator.main import HourCompensator
import datetime, time


@shared_task(name='run-hour-compensator', bind=True)
def run_hour_compensator(self, task_id):
    time.sleep(1)
    task = HourCompensatorTask.objects.get(id=task_id)
    plan = task.plan
    task.started_at = timezone.now()
    task.save()
    if plan.status == PlanStatus.PENDING.value:
        plan.status = PlanStatus.STARTED.value
        plan.save()
    try:
        self.update_state(state='EXECUTING_QUERIES')
        parameters = json.loads(plan.parameters)
        parameters.update(json.loads(task.parameters))
        sites = parameters['sites']
        amount_sites = sites.copy()
        translate_sites = {
            'PVEA TUMBES': 'PLAZA VEA TUMBES',
            'PVO HUANUCO': 'SPO PVO HUANUCO',
            'PVO JAEN': 'SPO PVO JAEN',
            'PVO PUCALLPA': 'SPO PVO PUCALLPA',
            'PVO TARAPOTO': 'SPO PVO TARAPOTO',
            'PVEA CUZCO SAN ANTONIO (MALL-ARZOBISPADO)': 'PVEA CUZCO SAN ANTONIO'
        }
        for i in range(len(amount_sites)):
            if amount_sites[i] in translate_sites:
                amount_sites[i] = translate_sites[amount_sites[i]]
        url = 'https://integration-kronos.scmlatam.com/api/v1/query'
        headers = {
            'Authorization': 'Bearer xQF3hDKtreiaUuBAPncc',
            'company': 'spsa'
        }
        queries = []
        sites_condition = "AND (categorynm LIKE '{}'".format(sites[0])
        for i in range(1, len(sites)):
            sites_condition += " OR categorynm LIKE '{}'".format(sites[i])
        sites_condition += ")"
        curve_query = """
            SELECT * FROM curvas_zoho
            WHERE 
            driver IN ('04 - Scheduled Kronos','01 - Forecast')
            AND BUSINESSDT>='{}'
            AND BUSINESSDT<='{}'
            {}
        """.format(parameters['range_start'], parameters['range_end'], sites_condition)
        curve_query = re.sub(' +', ' ',curve_query)
        schedule_query = "EXECUTE [dbo].[CustomHorarioActual_Store_Detalle_Break] '{}', '{}', "\
            .format(parameters['range_start'], parameters['range_end'])
        sites_condition = "('" + "','".join(amount_sites) + "')"
        amount_query = """
            SELECT PE.PERSONNUM DNI, PE.FULLNM NOMBRE,LA.LABORLEV3DSC SEDE, LA.LABORLEV7DSC PUESTO , CONVERT(VARCHAR,'{0}' ,103) FECHA, 
            ISNULL((SELECT SUM(AT.AMOUNT)/3600.00 FROM ACCRUALTRAN AT WHERE AT.ACCRUALCODEID=1 AND AT.PERSONID = PE.PERSONID
            AND AT.TYPE <> 11 AND AT.EFFECTIVEDATE >= ISNULL((SELECT MAX(AT1.EFFECTIVEDATE)
            FROM ACCRUALTRAN AT1
            WHERE AT1.PERSONID = AT.PERSONID
            AND AT1.ACCRUALCODEID = 1 AND AT1.TYPE = 3 AND AT1.EFFECTIVEDATE <= '{0}' ),'1900-01-01')
            AND AT.EFFECTIVEDATE <= '{0}' ),0) SALDO_HE,
            ISNULL((SELECT SUM(AT.AMOUNT)/3600.00 FROM ACCRUALTRAN AT WHERE AT.ACCRUALCODEID=51 AND AT.PERSONID = PE.PERSONID
            AND AT.TYPE <> 11
            AND AT.EFFECTIVEDATE >= ISNULL((SELECT MAX(AT1.EFFECTIVEDATE) FROM ACCRUALTRAN AT1 WHERE AT1.PERSONID = AT.PERSONID
            AND AT1.ACCRUALCODEID = 51 AND AT1.TYPE = 3 AND AT1.EFFECTIVEDATE <= '{0}' ),'1900-01-01')
            AND AT.EFFECTIVEDATE <= '{0}' ),0) HORAS_POR_RECUPERAR
            FROM PERSON PE, COMBHOMEACCT CH, LABORACCT LA
            WHERE CH.EMPLOYEEID=PE.PERSONID AND '{0}' BETWEEN CH.EFFECTIVEDTM AND CH.EXPIRATIONDTM-1
            AND LA.LABORACCTID = CH.LABORACCTID  
            AND LA.LABORLEV3DSC in {1}
            AND PE.PERSONNUM NOT LIKE 'JEF%'
                """.format(parameters['current_sunday'], sites_condition)
        amount_query = re.sub(' +', ' ', amount_query)
        queries.append(curve_query)
        queries.append(amount_query)
        input_paths = {}
        for site in sites:
            queries.append(schedule_query + "'{}'".format(site))
        queries_container = []
        i = 0
        while (i*30) < len(queries):
            queries_container.append(queries[i:(i+1)*30])
            i += 1
        #print(queries)
        result_data = []
        for queries_group in queries_container:
            for i in range(20):
                response = requests.post(url, json={'query': queries_group}, headers=headers,
                                         timeout=60*15)
                time.sleep(60)
                if 200 <= response.status_code < 300:
                    break
            response_dict = response.json()
            result_data += response_dict['result']
        j = 0
        for query in ['curve', 'amount', 'schedule']:
            if j < 2:
                aux_list = result_data[j]
            else:
                aux_list = []
                for element in result_data[2:]:
                    aux_list += element
            df = pd.DataFrame(aux_list)
            path = join('hourcompensator', 'input', '{}-{}.xlsx'.format(task_id, query))
            absolute_path = join(settings.MEDIA_ROOT, path)
            input_paths[query] = absolute_path
            df.to_excel(absolute_path, engine='xlsxwriter', index=False)
            getattr(task, query + '_attach').name = path
            task.save()
            j += 1
        self.update_state(state='RUNNING')
        input_dataframes = [
            pd.read_excel(input_paths['curve']),
            pd.read_excel(input_paths['schedule'], converters={'personnum':str}),
            pd.read_excel(input_paths['amount'], converters={'DNI':str})
        ]
        sites_column = {
            'curve': 'CATEGORYNM',
            'schedule': 'TIENDA',
            'amount': 'SEDE'
        }
        warnings_sites = {
            'curve': [],
            'schedule': [],
            'amount': []
        }
        ii = 0
        updated_sites = sites.copy()
        for kind in ['curve', 'schedule', 'amount']:
            df_sites = input_dataframes[ii][sites_column[kind]].unique()
            if kind != 'amount':
                iter_sites = sites
            else:
                iter_sites = amount_sites
            for site in iter_sites:
                if site not in df_sites:
                    warnings_sites[kind].append(site)
                    if kind=='schedule':
                        updated_sites.remove(site)
            ii += 1
        parameters['sites'] = updated_sites
        task.execution_warning = json.dumps(warnings_sites)
        task.save()
        hour_compensator = HourCompensator(parameters, input_dataframes)
        hour_compensator.run()
        path = join('hourcompensator', 'output', str(task.id) + '-results.xlsx')
        absolute_path = join(settings.MEDIA_ROOT, path)
        writer = pd.ExcelWriter(absolute_path, engine='xlsxwriter')
        hour_compensator.dfh_new.to_excel(writer, 'Curva de horarios', index=False)
        hour_compensator.dft_new.to_excel(writer, 'HorariosCompensados', index=False)
        hour_compensator.dft_new2.to_excel(writer, 'HorariosCompensadosDetalle', index=False)
        hour_compensator.df_hhee.to_excel(writer, 'HHEE', index=False)
        writer.save()
        task.main_results.name = path
        task.save()
        schedule_df = input_dataframes[1]
        transfer_dict = {}
        for index, row in schedule_df.iterrows():
            transfer_dict[str(row['personnum'])] = row['PUESTO']
        df = hour_compensator.dft_new
        unlock_schedules = []
        absences = []
        delete_schedules = []
        shift_schedules = []
        lock_schedules = []
        for index, row in df.iterrows():
            if row['Entrada_compensada'] == 0 and row['Salida_compensada'] == 0:
                continue
            row_date = datetime.datetime.strptime(row['Fecha'].split(' ')[0], '%d-%m-%Y').strftime('%Y-%m-%d')
            person_dict = {
                'person_number': str(row['ID']),
                'start_date': row_date,
                'end_date': row_date
            }
            unlock_schedules.append(person_dict)
            delete_schedules.append(person_dict)
            if (row['Entrada_nueva'] != row['Salida_nueva']):
                transfer = transfer_dict.get(row['ID'])
                shift_dict = {
                    'person_number': str(row['ID']),
                    'date': row_date,
                    'transfer': transfer,
                    'comment': 'COMPENSACION AUTOMATICA'
                }
                if pd.isnull(row['BreakIn_nuevo']):
                    segments = [{
                        'type': None,
                        'start_time': row['Entrada_nueva'].split(' ')[1],
                        'end_time': row['Salida_nueva'].split(' ')[1],
                        'offset_start_day': 1,
                        'offset_end_day': 1
                    }]
                else:
                    segments = [
                        {
                            'type': 'Transfer',
                            'start_time': row['Entrada_nueva'].split(' ')[1],
                            'end_time': row['BreakIn_nuevo'].strftime('%H:%M'),
                            'offset_start_day': 1,
                            'offset_end_day': 1
                        },
                        {
                            'type': 'Break',
                            'start_time': row['BreakIn_nuevo'].strftime('%H:%M'),
                            'end_time': row['BreakOut_nuevo'].strftime('%H:%M'),
                            'offset_start_day': 1,
                            'offset_end_day': 1
                        },
                        {
                            'type': 'Transfer',
                            'start_time': row['BreakOut_nuevo'].strftime('%H:%M'),
                            'end_time': row['Salida_nueva'].split(' ')[1],
                            'offset_start_day': 1,
                            'offset_end_day': 1
                        }
                    ]
                shift_dict['segments'] = segments
                shift_schedules.append(shift_dict)
            if row['Entrada_compensada'] > 0:
                absences.append({
                    'person_number': row['ID'],
                    'paycode': 'PAGO HORAS ACUMULADAS',
                    'date': row_date,
                    'start_time': row['Entrada_antigua'].strftime('%H:%M'),
                    'amount': row['Entrada_compensada'],
                    'comment': 'COMPENSACION AUTOMATICA',
                    'override': False
                })
            if row['Salida_compensada'] > 0:
                absences.append({
                    'person_number': row['ID'],
                    'paycode': 'PAGO HORAS ACUMULADAS',
                    'date': row_date,
                    'start_time': row['Salida_nueva'].split(' ')[1],
                    'amount': row['Salida_compensada'],
                    'comment': 'COMPENSACION AUTOMATICA',
                    'override': False
                })
            if int(row['Bloquear']) == 1:
                lock_schedules.append(person_dict)
        data_dict = {
            'unlock': {'unlock': unlock_schedules},
            'delete': {'delete': delete_schedules},
            'shift': {'shifts': shift_schedules},
            'absences': {'absences': absences},
            'lock': {'lock': lock_schedules}
        }
        #print(data_dict)
        for key in ['unlock', 'delete', 'shift', 'absences']:
            name = key + '_request'
            path = join('hourcompensator', 'http', '{}-{}.json'.format(task.id, name))
            absolute_path = join(settings.MEDIA_ROOT, path)
            file = open(absolute_path, 'w+')
            file.write(json.dumps(data_dict[key], indent=2))
            file.close()
            getattr(task, name).name = path
            task.save()
        urls = {
            'unlock': 'https://integration-kronos.scmlatam.com/api/v1/kronos_wfc/unlock-schedule',
            'delete': 'https://integration-kronos.scmlatam.com/api/v1/kronos_wfc/schedule',
            'shift': 'https://integration-kronos.scmlatam.com/api/v1/kronos_wfc/shift-schedule',
            'absences': 'https://integration-kronos.scmlatam.com/api/v1/kronos_wfc/absence-hours',
            'lock': 'https://integration-kronos.scmlatam.com/api/v1/kronos_wfc/lock-schedule'
        }
        for key in ['unlock', 'delete', 'shift', 'absences']:
            name = key + '_response'
            if key != 'delete':
                response = requests.post(urls[key], json=data_dict[key], headers=headers)
                print("response_status", response)
                try:
                    response_dict = response.json()
                    content = json.dumps(response_dict, indent=2)
                except json.decoder.JSONDecodeError:
                    content = response.text
                path = join('hourcompensator', 'http', '{}-{}.json'.format(task.id, name))
                absolute_path = join(settings.MEDIA_ROOT, path)
                file = open(absolute_path, 'w+')
                file.write(content)
                file.close()
                getattr(task, name).name = path
                task.save()
            else:
                for data in delete_schedules:
                    response = requests.delete(urls[key], json=data, headers=headers)
                    print("response_status", response)
                    try:
                        response_dict = response.json()
                        content = json.dumps(response_dict, indent=2)
                    except json.decoder.JSONDecodeError:
                        content = response.text
                    path = join('hourcompensator', 'http', '{}-{}.json'.format(task.id, name))
                    absolute_path = join(settings.MEDIA_ROOT, path)
                    file = open(absolute_path, 'a+')
                    file.write(content)
                    file.close()
                    getattr(task, name).name = path
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
        send_plan_finished_email(plan,
                                 reverse('hourcompensator:plan_detail', kwargs={'plan_id': plan.id}))
