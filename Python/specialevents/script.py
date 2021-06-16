import dateutil
import numpy as np
import pandas as pd
import dateutil.relativedelta as re
from datetime import datetime,timedelta
import csv, operator
from main import SpecialEvents


print(datetime.now())
df = pd.read_csv("/home/fernando/scm/suite/eventos/Prueba.csv", sep=",")
print(df)
for value in df['FECHA']:
    print(value, type(value))

parameters = {
    'days_min': 4,
    'days_max': 6,
    'days_step': 1,
    'sensitivity_min': 1.25,
    'sensitivity_max': 1.5,
    'sensitivity_step': 0.25,
    'start_date': '02/01/2020',
    'end_date': '30/11/2020'
}

driver_instance = SpecialEvents(parameters, df, 'AGUADILLA_MALL_KIOSK-SALES')
driver_instance.run()
results = driver_instance.results
keys = list(results.keys())
keys.sort()
if keys:
    path = r'Special_Event_CAJAS_TVENTA_MX_SUMMARY_FS.xlsx'
    writer = pd.ExcelWriter(path, engine='xlsxwriter')
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

print(datetime.now())
