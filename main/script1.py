import datetime, json, requests, pandas as pd

headers = {
    'Authorization': 'Bearer xQF3hDKtreiaUuBAPncc',
    'company': 'spsa'
}


transfer_dict = {
    '07528103': './SPSA/DIR. OPERACIONES/PVEA BRASIL/CAJAS/CAJERO',
    '08891664': './SPSA/DIR. OPERACIONES/PVEA HIGUERETA/CAJAS/CAJERO',
    '002035185': './SPSA/DIR. OPERACIONES/PVEA HIGUERETA/CAJAS/CAJERO',
    '07502095': './SPSA/DIR. OPERACIONES/PVEA HUANCAYO/CAJAS/CAJERO',
    '09836163': './SPSA/DIR. OPERACIONES/PVEA PRO/CAJAS/CAJERO',
    '09050800': './SPSA/DIR. OPERACIONES/PVEA SALAVERRY/CAJAS/CAJERO',
    '09604564': './SPSA/DIR. OPERACIONES/PVEA SALAVERRY/CAJAS/CAJERO',
    '08338263': './SPSA/DIR. OPERACIONES/PVEA SAN BORJA/CAJAS/CAJERO',
    '09765392': './SPSA/DIR. OPERACIONES/PVEA SANTA CLARA/CAJAS/CAJERO',
    '00498026': './SPSA/DIR. OPERACIONES/PVEA TACNA/CAJAS/CAJERO',
    '01331891': './SPSA/DIR. OPERACIONES/PVEA TACNA/CAJAS/CAJERO',
    '03876567': './SPSA/DIR. OPERACIONES/PVEA TALARA/CAJAS/CAJERO',
    '09822290': './SPSA/DIR. OPERACIONES/SVEA ALAMEDA SUR/CAJAS/CAJERO'
}

df = pd.read_excel('/home/fernando/scm/spsa.xlsx', sheet_name='Hoja1', converters={'ID':str})
#df['Entrada_antigua'] = df['Entrada_antigua'].astype(str)
#df['Salida_antigua'] = df['Salida_antigua'].astype(str)
unlock_schedules = []
delete_schedules = []
shift_schedules = []
absences = []
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
    if row['ID'] in transfer_dict:
        transfer = transfer_dict[row['ID']]
    else:
        response = requests.get('https://integration-kronos.scmlatam.com/api/v1/kronos_wfc/schedule', json=person_dict, headers=headers)
        response_dict = response.json()
        transfer = response_dict['data'][0]['org_job_path']
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
            'person_number': str(row['ID']),
            'paycode': 'PAGO HORAS ACUMULADAS',
            'date': row_date,
            'start_time': row['Entrada_antigua'].strftime('%H:%M'),
            'amount': row['Entrada_compensada'],
            'comment': 'COMPENSACION AUTOMATICA',
            'override': False
        })
    if row['Salida_compensada'] > 0:
        absences.append({
            'person_number': str(row['ID']),
            'paycode': 'PAGO HORAS ACUMULADAS',
            'date': row_date,
            'start_time': row['Salida_nueva'].split(' ')[1],
            'amount': row['Salida_compensada'],
            'comment': 'COMPENSACION AUTOMATICA',
            'override': False
        })
data_dict = {
    'unlock': {'unlock': unlock_schedules},
    'absence': {'absences': absences},
    'shift': {'shifts': shift_schedules},
    'delete': {'delete': delete_schedules},
}

#for key in data_dict:
#    name = key + '_request'
#    path = join('hourcompensator', 'http', '{}-{}.json'.format(task.id, name))
#    absolute_path = join(settings.MEDIA_ROOT, path)
#    file = open(absolute_path, 'w+')
#    file.write(json.dumps(data_dict[key]))
#    print(json.dumps(data_dict[key]))
#    file.close()
#    getattr(task, key).name = path
#    task.save()



response = requests.post('https://integration-kronos.scmlatam.com/api/v1/kronos_wfc/unlock-schedule', json={'unlock': unlock_schedules}, headers=headers)
print(response)
response_dict = response.json()
print(response_dict)

for data in delete_schedules:
    response = requests.delete('https://integration-kronos.scmlatam.com/api/v1/kronos_wfc/schedule', json=data, headers=headers)
    print(response)
    response_dict = response.json()
    print(response_dict)

'''
for data in absences:
    response = requests.delete('https://integration-kronos.scmlatam.com/api/v1/kronos_wfc/absence-hours',
                               json=data, headers=headers)
    print(response)
    response_dict = response.json()
    print(response_dict)
'''


#response = requests.post('https://integration-kronos.scmlatam.com/api/v1/kronos_wfc/absence-hours', json={'absences': absences}, headers=headers)
#print(response)
#response_dict = response.json()
#print(response_dict)


response = requests.post('https://integration-kronos.scmlatam.com/api/v1/kronos_wfc/shift-schedule', json={ 'shifts': shift_schedules}, headers=headers)
print(response)
response_dict = response.json()
print(response_dict)


response = requests.post('https://integration-kronos.scmlatam.com/api/v1/kronos_wfc/absence-hours', json={'absences': absences}, headers=headers)
print(response)
response_dict = response.json()
print(response_dict)
