import datetime as dt, pandas as pd
import os, sys
file_path3 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
#print(file_path1, file_path2, file_path3)
sys.path.append(file_path3)
from hourcompensator.main import HourCompensator


input_folder = r'C:\Users\srmun\Desktop\SCM\Pega\SPSA\2021\Compensacion de horas\prueba'
output_folder = r'C:\Users\srmun\Desktop\SCM\Pega\SPSA\2021\Compensacion de horas\prueba'

dataframes = [pd.read_excel(input_folder + '\Input Curvas.xlsx'),
              pd.read_excel(input_folder + '\Input Horarios.xlsx'),
              pd.read_excel(input_folder + '\Reporte Saldos por Compensar.xlsx')]

parameters = {
    'current_sunday': '2020-11-22',
    'sites': ['PVEA JOCKEY PLAZA', 'PVEA VENTANILLA', 'PVEA SAN ISIDRO', 'PVEA LA MOLINA'],
    'cases_parameters': [
            {
            # Escenario 2
            'holgura_critica': 1,
            'limite_corte': 20,
            'comp_max': 1,
            'hh_ee_max': 1,
            'turno_minimo': 3,
            'k_a': 'Actual_Real',
            'maximo_compensacion_dia': 1
        }
    ]
}
'''
{
    # Escenario 0
    'holgura_critica': 0,
    'limite_corte': 20,
    'comp_max': 0.3,
    'hh_ee_max': 1,
    'turno_minimo': 3,
    'k_a': 'Actual_Real',
    'maximo_compensacion_dia': 0.1
},
{
    # Escenario 1
    'holgura_critica': 0,
    'limite_corte': 20,
    'comp_max': 0.2,
    'hh_ee_max': 0.25,
    'turno_minimo': 3,
    'k_a': 'Actual_Real',
    'maximo_compensacion_dia': 0.1
},
{
    # Escenario 2
    'holgura_critica': 1,
    'limite_corte': 20,
    'comp_max': 1,
    'hh_ee_max': 1,
    'turno_minimo': 3,
    'k_a': 'Actual_Real',
    'maximo_compensacion_dia': 1
},
{
    # Escenario 3
    'holgura_critica': 1,
    'limite_corte': 20,
    'comp_max': 0.15,
    'hh_ee_max': 0.3,
    'turno_minimo': 3,
    'k_a': 'Actual_Real',
    'maximo_compensacion_dia': 0.1
},
{
    # Escenario 4
    'holgura_critica': 2,
    'limite_corte': 20,
    'comp_max': 0.20,
    'hh_ee_max': 1,
    'turno_minimo': 3,
    'k_a': 'Actual_Real',
    'maximo_compensacion_dia': 0.1
}
'''

hour_compensator = HourCompensator(parameters, dataframes)
hour_compensator.run()

hour_compensator.dfh_new.to_csv(output_folder + 'Curvas de horarios.csv')
hour_compensator.dft_new.to_csv(output_folder + 'HorariosCompensados.csv')
#hour_compensator.dfh_new[
#    ['Sede', 'Fecha', 'Semana', 'Hora', 'Labor', 'Horario_Actual', 'Horario_Kronos',
#     'Horario_Compensado', 'Horario_Actual_Real_old', 'Holgura_Compensada']].to_csv(
#    output_folder + 'df_output.csv', sep=';', index=False)
#hour_compensator.dfh_t.to_csv(output_folder + 'Curvas Escenarios Arreglados.csv')
