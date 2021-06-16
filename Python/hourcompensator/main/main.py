import pandas as pd
from hourcompensator.main.io_utils import leer, reordenar, apertura_cierre, procesa_dft, jornada, horario_real
from hourcompensator.main.utils import compensador, horario_compensado_final
from hourcompensator.main.df_utils import old, hh_ee, new, trasponer
import datetime as dt


class HourCompensator:
    def __init__(self, parameters, dataframes):
        self.dfh, self.dft, self.dfj, self.alarma = leer(dataframes)
        # Recordar que en dfj seleccionamos solo las acumuladas a la fecha
        # **** Esto debería cambiar, los saldos de HHEE en el mes presente no deberían
        # Considerar los del mes pasado
        # dfj = dfj.loc[dfj['Fecha']==pd.Timestamp(2020,8,16)]
        # dfj.reset_index(drop=True,inplace=True)

        # %% Creacion de DataFrames necesarios
        # Como primer approach veremos la primera semana de septiembre
        # 1ero, llamamos la funcion reordenar para ordener la matriz
        # según nuestra conveniencia y después le agregamos la columna Semana
        self.dfh = reordenar(self.dfh)

        # 2do, calculamos la apertura y cierre de la Sede
        # Definimos la apertura cuando el labor es mayor a 0
        self.dfac = apertura_cierre(self.dfh)

        # 3ero, creamos dataframe con los trabajadores y sus bolsas, solo con los con hhee > 0
        self.dft = procesa_dft(self.dft, self.dfj)

        # 4to, se procesa la funcion horario_real que crea en dfh las columnas
        # Horario Real y Holgura Real calculado según los trabajadores reales
        horario_real(self.dft, self.dfh)

        # 5to, calculamos cuantas horas trabajan los trabajadores para todas las semanas
        self.df_jornada = jornada(self.dft)

        # Se crearon los siguientes DataFrames
        # dfh -> Horarios de la tienda
        # dft -> Horarios de los trabajadores
        # dfac -> Apertura y cierre por fecha del local
        # dfj -> Bolsa de horas
        # df_jornada -> Horas trabajadas según jornada semanal por empleado

        # %% Hacemos copias para el output final
        # obtenemos proxima semana
        current_sunday = dt.datetime.strptime(parameters['current_sunday'], '%Y-%m-%d')
        self.prox_semana = (current_sunday + dt.timedelta(days=7)).isocalendar()[1]
        self.dfh_old, self.dft_old, self.dfac_old, self.dfj_old = old(self.dfh, self.dft, self.dfac, self.dfj)
        self.df_hhee = hh_ee(self.dft_old, self.prox_semana)

        # %% A jugar (aquí se compensa)
        #  1ero, seleccionamos la semana a compensar
        self.semana_a_compensar = self.prox_semana  # despues se transformara a la prox_semana

        # 2do, definimos el input de la sede y semana a evaluar
        self.sedes = parameters['sites']  ##['PVEA JOCKEY PLAZA', 'PVEA VENTANILLA', 'PVEA SAN ISIDRO']
        #self.cases = parameters['cases']
        self.cases_parameters = parameters['cases_parameters']

        self.dft_output = pd.DataFrame()
        self.dfh_output = pd.DataFrame()
        self.dfh_new = None
        self.dft_new = None
        self.dft_new2 = None
        self.dfh_t = None
        self.ver = []

    def run(self):
        i = 0
        for parametros in self.cases_parameters:
            i += 1
            #parametros = parametros_escenarios['parametros'][escenario - 1]
            holgura_critica = parametros['holgura_critica']
            limite_corte = parametros['limite_corte']
            comp_max = parametros['comp_max']
            hh_ee_max = parametros['hh_ee_max']
            turno_minimo = parametros['turno_minimo']
            k_a = parametros['k_a']
            maximo_compensacion_dia = parametros['maximo_compensacion_dia']
            for sede in self.sedes:
                dft_input = self.dft.loc[
                    (self.dft['Sede'] == sede) & (self.dft['Semana'] == self.semana_a_compensar)].copy()
                dft_input.reset_index(drop=True, inplace=True)
                dfh_input = self.dfh.loc[
                    (self.dfh['Sede'] == sede) & (self.dfh['Semana'] == self.semana_a_compensar)].copy()
                dfh_input.reset_index(drop=True, inplace=True)
                # compensamos las entradas y las salidas
                dfh_final, dft_final = compensador(self.semana_a_compensar, dfh_input, dft_input,
                                                   holgura_critica, limite_corte, comp_max,
                                                   turno_minimo, k_a, hh_ee_max, self.df_hhee,
                                                   maximo_compensacion_dia)
                horario_compensado_final(dfh_final, dft_final)
                dfh_final['Escenario'] = i
                self.dft_output = self.dft_output.append(dft_final, ignore_index=True)
                self.dfh_output = self.dfh_output.append(dfh_final, ignore_index=True)

        # %% Preparamos output para Kronos
        # llamamos funcion para renombrar, mergear con dfs viejos y calcular compensacion
        self.dfh_new, self.dft_new, self.dft_new2 = new(self.dfh_output, self.dft_output, self.dfh_old, self.dft_old)
        self.dfh_new['Holgura_Compensada'] = self.dfh_new['Horario_Actual_Real_old'] - self.dfh_new[
            'Horario_Compensado']
        drop_list = []
        for index, row in self.dft_new.iterrows():
            row_date = row['Fecha'].split(' ')[0]
            print(row_date)
            if row_date in ['12-02-2021', '13-02-2021', '14-02-2021']:
                drop_list.append(index)
        self.dft_new = self.dft_new.drop(drop_list)
        self.dft_new2 = self.dft_new2.drop(drop_list)
        df_compensado = self.dft_new.groupby('Sede')[
                            ['Entrada_compensada', 'Salida_compensada']].sum()
        df_compensado['Total compensado'] = df_compensado['Entrada_compensada'] + df_compensado[
            'Salida_compensada']
        df_compensado.drop(['Entrada_compensada', 'Salida_compensada'], axis=1, inplace=True)
        df_compensado.reset_index(drop=False, inplace=True)
        self.df_hhee = pd.merge(self.df_hhee, df_compensado, how='left', on='Sede')

        # Calculamos cuantas son las horas totales de planificacion
        self.dft_old['Horas Planificadas'] = (self.dft_old['Salida_old'] - self.dft_old['Entrada_old']).map(
            lambda x: x.total_seconds() / 3600) - (self.dft_old['BreakOut_old'] - self.dft_old[
            'BreakIn_old']).notna().astype(int)
        horas_planificadas = self.dft_old.groupby('Sede')['Horas Planificadas'].sum().to_frame()
        horas_planificadas.reset_index(drop=False, inplace=True)
        self.df_hhee = pd.merge(horas_planificadas, self.df_hhee, how='left', on='Sede')

        # Parche
        # vemos las horas planificadas para cada uno
        block = self.dft_old.groupby('ID').sum()['Horas Planificadas'].to_frame()
        block.reset_index(drop=False, inplace=True)
        jornadas_posibles = [19.5, 22.5, 23.5, 48]
        block['Bloquear'] = 1
        block.loc[~block['Horas Planificadas'].isin(jornadas_posibles), 'Bloquear'] = 0
        no_bloquear = block['ID'][block['Horas Planificadas']].dropna().unique().tolist()
        self.dft_new['Bloquear'] = 1
        self.dft_new.loc[self.dft_new['ID'].isin(no_bloquear), 'Bloquear'] = 0
