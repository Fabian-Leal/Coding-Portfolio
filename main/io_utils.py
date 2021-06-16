import datetime as dt
import numpy as np
import pandas as pd


# %% Leer excels
#x = {
#    'folder_path': r'C:\Users\srmun\Desktop\SCM\Pega\SPSA\2020\Compensacion de horas extra\2020 09 24',
#    'Curvas': ['Horario Kronos', 'Horario Actual', 'Forecast'],
#    'Archivos': ['Input Curvas', 'Input Horario']}


# %% Funcion para leer la data de CC y JC
# Data CC -> dfh, dft
# Data JC -> dfj
def leer(dataframes):
    # Leemos todas las curvas
    dfh = dataframes[0]
    dft = dataframes[1]
    dfh = dfh.rename({'SEDE': 'Sede', 'EVENTDTM': 'Fecha'}, axis=1)
    dfh = dfh.rename({'ORGNM': 'Sede'}, axis=1)
    dft = dft.rename({'PERSONNUM': 'ID', 'EVENTDTM': 'Fecha', 'PUESTO': 'Puesto',
                      'TIENDA': 'Sede', 'REFRIGERIO': 'Refrigerio'}, axis=1)
    dft = dft.rename({'personnum': 'ID'}, axis=1)
    dfh = dfh.rename({'CATEGORYNM': 'Sede', 'DRIVER': 'Tipo_Curva', 'BUSINESSDT': 'Fecha'}, axis=1)
    dfh['Fecha'] = pd.to_datetime(dfh['Fecha'])
    dft['Fecha'] = pd.to_datetime(dft['Fecha'])
    dfh.replace({'04 - Scheduled Kronos': 'Horario_Kronos',
                 'Horario Actual': 'Horario_Actual',
                 '01 - Forecast': 'Labor'}, inplace=True)
    # DataFrame de Jorge
    dfj = dataframes[2]
    dfj = dfj.rename({'SEDE': 'Sede', 'FECHA': 'Fecha', 'SALDO_HE': 'SALDO HE',
                      'HORAS_POR_RECUPERAR':'HORAS POR RECUPERAR'}, axis=1)
    # Calculamos las horas extra (Saldo_HE - Horas_por_recuperar)
    dfj.loc[dfj['HORAS POR RECUPERAR'] > 0, 'Horas'] = 0
    dfj.loc[(dfj['HORAS POR RECUPERAR'] == 0) & (dfj['SALDO HE'] >= 0),
            'Horas'] = dfj['SALDO HE'][dfj['HORAS POR RECUPERAR'] == 0]
    dfj.rename({'DNI': 'ID'}, axis=1, inplace=True)

    dft['ID'] = dft['ID'].astype(str)
    dfj['ID'] = dfj['ID'].astype(str)
    
    # Agregar alarma de horarios duplicados
    alarma = dft[dft.duplicated(subset=['ID','Fecha'],keep=False)]
    
    # Eliminar horarios duplicados
    dft.drop_duplicates(subset = ['ID','Fecha'],inplace=True,ignore_index=True)
    
    
    return dfh, dft, dfj, alarma


# %% Reordenamos la matriz para nuestra conveniencia
# input -> dfh
# output -> dfh (reorganizado)
def reordenar(dfh):
    dfh_aux = []
    dfh['Fecha'] = pd.to_datetime(dfh['Fecha'])
    for s in dfh.Sede.unique():
        for i in dfh.Fecha.unique():
            for j in dfh.columns[3:]:
                dfh_aux.append([s,
                                i,
                                j])
    dfh_aux = pd.DataFrame(data=dfh_aux, columns=['Sede', 'Fecha', 'Hora'])
    # Ahora agregamos Labor y Horario Actual
    dfh_aux['Labor'] = 0
    dfh_aux['Horario_Actual'] = 0
    dfh_aux['Horario_Kronos'] = 0
    for s in dfh.Sede.unique():
        for i in dfh.Fecha.unique():
            for j in dfh.columns[3:]:
                Labor = dfh.loc[(dfh['Tipo_Curva'] == 'Labor') & (dfh['Fecha'] == i) & (
                            dfh['Sede'] == s), j].values
                Horario_Actual = dfh.loc[
                    (dfh['Tipo_Curva'] == 'Horario_Actual') & (dfh['Fecha'] == i) & (
                                dfh['Sede'] == s), j].values
                Horario_Kronos = dfh.loc[
                    (dfh['Tipo_Curva'] == 'Horario_Kronos') & (dfh['Fecha'] == i) & (
                                dfh['Sede'] == s), j].values
                Labor = 0 if Labor.size == 0 else Labor[0]
                Horario_Actual = 0 if Horario_Actual.size == 0 else Horario_Actual[0]
                Horario_Kronos = 0 if Horario_Kronos.size == 0 else Horario_Kronos[0]
                dfh_aux.loc[(dfh_aux['Fecha'] == i) & (dfh_aux['Hora'] == j) & (
                            dfh_aux['Sede'] == s), 'Labor'] = Labor
                dfh_aux.loc[(dfh_aux['Fecha'] == i) & (dfh_aux['Hora'] == j) & (
                            dfh_aux['Sede'] == s), 'Horario_Actual'] = Horario_Actual
                dfh_aux.loc[(dfh_aux['Fecha'] == i) & (dfh_aux['Hora'] == j) & (
                            dfh_aux['Sede'] == s), 'Horario_Kronos'] = Horario_Kronos
    # Eliminamos y renombramos para liberar espacio
    dfh = dfh_aux.copy()
    # Calculamos Holgura
    dfh['Holgura_Actual'] = dfh['Horario_Actual'] - dfh['Labor']
    dfh['Holgura_Kronos'] = dfh['Horario_Kronos'] - dfh['Labor']
    # Debemos transformar Hora -> datetime.time
    dfh['Hora'] = dfh.Hora.map(lambda x: x[6:])
    dfh['Hora'] = dfh.Hora.map(lambda x: dt.time(int(x[1:3]), 15 * (int(x[4:]) - 1)))
    # tambien combinamos dfh.Hora con la fecha
    for f in range(0, len(dfh)):
        fecha = dfh.Fecha[f]
        hora = dfh.Hora[f]
        dfh.loc[f, 'Hora'] = dt.datetime.combine(fecha, hora)
    dfh.insert(2, 'Semana', dfh['Fecha'].map(lambda x: x.week))
    return dfh


# %% Ahora calculamos la apertura y cierre de la Sede
# Definimos la apertura cuando el labor es mayor a 0
# input -> dfh
# output -> dfac
def apertura_cierre(dfh):
    dfac = []
    for s in dfh.Sede.unique():
        for f in dfh.Fecha.unique():
            operacion = dfh['Hora'][dfh['Labor'] > 0][dfh['Fecha'] == f].values
            apertura = 0
            cierre = 0
            for i in range(0, len(operacion) - 1):
                if (apertura == 0) and (
                        (dt.timedelta(hours=operacion[i].hour, minutes=operacion[i].minute) +
                         dt.timedelta(seconds=900)) == dt.timedelta(hours=operacion[i + 1].hour,
                                                                    minutes=operacion[
                                                                        i + 1].minute)):
                    apertura = operacion[i]
            operacion = operacion[::-1]
            for i in range(0, len(operacion) - 1):
                if (cierre == 0) and (
                        (dt.timedelta(hours=operacion[i].hour, minutes=operacion[i].minute) -
                         dt.timedelta(seconds=900)) == dt.timedelta(hours=operacion[i + 1].hour,
                                                                    minutes=operacion[
                                                                        i + 1].minute)):
                    cierre = operacion[i]
            dfac.append([s, f, apertura, cierre])
    dfac = pd.DataFrame(dfac, columns=['Tienda', 'Fecha', 'Apertura', 'Cierre'])
    dias = dfac.Fecha.map(lambda x: x.day_name())
    semanas = dfac.Fecha.map(lambda x: x.week)
    dfac.insert(2, 'Dia', dias)
    dfac.insert(2, 'Semana', semanas)
    return dfac


# %% Procesamos la data de Jorge
# Creamos dataframe con los trabajadores y sus bolsas, solo tomamos los con hhee > 0
# input -> dft,dfj
# output -> manipula dft, agrega el turno, la entrada y la salida de los trabajadores
def procesa_dft(dft, dfj):
    # Concatenamos los turnos de los trabajadores con la bolsa de hhee
    dft['Fecha'] = pd.to_datetime(dft['Fecha'])
    dft = pd.merge(dft, dfj[['ID', 'Horas']], how='left', on='ID')
    dft.reset_index(drop=True, inplace=True)
    # Separamos el turno en entrada y salida
    dft['TURNO'] = dft['TURNO'].str.split('-', 0)
    dft['Entrada'] = dft.TURNO.map(lambda x: x[0])
    dft['Salida'] = dft.TURNO.map(lambda x: x[1])
    dft['Entrada'] = dft.Entrada.map(lambda x: dt.time(int(x.split(':')[0]), int(x.split(':')[1])))
    dft['Salida'] = dft.Salida.map(lambda x: dt.time(int(x.split(':')[0]), int(x.split(':')[1])))

    # Separamos el refrigerio en breakin y breakout

    dft.loc[dft.Refrigerio.isna(),'Refrigerio'] = '0-0'
    dft['Refrigerio'] = dft['Refrigerio'].str.split('-',0)
    dft['BreakIn'] = dft.Refrigerio.map(lambda x: x[0])
    dft['BreakOut'] = dft.Refrigerio.map(lambda x: x[1])
    dft['BreakIn'] = dft.BreakIn[dft.BreakIn!='0'].map(lambda x: dt.time(int(x.split(':')[0]),int(x.split(':')[1])))
    dft['BreakOut'] = dft.BreakOut[dft.BreakOut!='0'].map(lambda x: dt.time(int(x.split(':')[0]),int(x.split(':')[1])))

    # Combinamos con la Fecha
    for f in range(0, len(dft)):
        fecha = dft.Fecha[f]
        entrada = dft.Entrada[f]
        salida = dft.Salida[f]
        dft.loc[f, 'Entrada'] = dt.datetime.combine(fecha, entrada)
        dft.loc[f, 'Salida'] = dt.datetime.combine(fecha, salida)
        # ahora combinamos con breakin y breakout
        breakin = dft.BreakIn[f]
        breakout = dft.BreakOut[f]
        if breakin is not np.nan:
            dft.loc[f, 'BreakIn'] = dt.datetime.combine(fecha, breakin)
            dft.loc[f, 'BreakOut'] = dt.datetime.combine(fecha, breakout)

    dft = dft[['Sede', 'ID', 'Fecha', 'Entrada', 'Salida',
               'BreakIn', 'BreakOut',
               'Horas']]
    # Le cortamos la hora a la fecha
    dft['Fecha'] = dft['Fecha'].map(lambda x: dt.datetime.strptime(str(x)[:10], '%Y-%m-%d'))
    return dft


# %% Esta funcion redondea el turno (entrada o salida), las entradas las redondea hacia adelante
# y las salidas hacia atras
# input -> turno, entrada_o_salida
# output -> turno_redondeado
def redondear(turno, entrada_o_salida):
    minutos = turno.minute
    hora = turno.hour
    if entrada_o_salida == 'entrada':
        if minutos in range(1, 15):
            minutos = 15
        elif minutos in range(16, 30):
            minutos = 30
        elif minutos in range(31, 45):
            minutos = 45
        elif minutos in range(46, 60):
            # aqui cambiamos la hora tb
            hora = hora + 1
            minutos = 0
    elif entrada_o_salida == 'salida':
        if minutos in range(1, 15):
            minutos = 0
        elif minutos in range(16, 30):
            minutos = 15
        elif minutos in range(31, 45):
            minutos = 30
        elif minutos in range(46, 60):
            minutos = 45
    turno_redondeado = dt.datetime(turno.year, turno.month, turno.day, hora, minutos)
    return turno_redondeado


# %% Funcion que calcula cuantas horas trabaja un trabajador para todas las semanas
# input -> dft
# output -> df_jornada (DataFrame con las horas de trabajo de los trabajadores para todas las semanas)
def jornada(dft):
    jornada = []
    dft.insert(3, 'Semana', dft['Fecha'].map(lambda x: x.week))
    for semana in dft.Semana.unique():
        for i in dft.ID[dft.Semana == semana].unique():
            jornada_horas = (dft.loc[(dft['ID'] == i) &
                                     (dft['Semana'] == semana), 'Salida'] - dft.loc[
                                 (dft['ID'] == i) &
                                 (dft['Semana'] == semana), 'Entrada']).sum().total_seconds() / 3600
            jornada.append([semana, i, jornada_horas])
    df_jornada = pd.DataFrame(jornada, columns=['Semana', 'ID', 'Jornada'])
    return df_jornada


# %% Funcion para calcular la columna Horario_Real según el input de horarios
# input -> dft, dfh
# output -> procesa y crea una columna extra en dfh (Horario_Real)
def horario_real(dft, dfh):
    for s in dfh.Sede.unique():
        print(s)
        for h in dfh.Hora.unique():
            dfh.loc[(dfh['Hora'] == h) &
                    (dfh['Sede'] == s),
                    'Horario_Actual_Real'] = len(dft.loc[(dft['Entrada']<=h)&
                                                                    (dft['Salida']>h)&
                                                                    ((dft['BreakIn']<h)&(dft['BreakOut']<=h)|
                                                                     (dft['BreakIn']>h)&(dft['BreakOut']>=h)|
                                                                     (dft['BreakIn'].isna())|(dft['BreakOut'].isna()))&
                                                                    (dft['Sede']==s),'ID'].unique())
    dfh['Holgura_Actual_Real'] = dfh['Horario_Actual_Real'] - dfh['Labor']


# %% Funcion para ver los empleados que estan en cada
# input -> fecha, hora
# output -> lista
def hhee(dft, fecha, hora):
    lista = dft[dft['Fecha'] == fecha][dft['Entrada'] <= hora].copy()
    lista.sort_values(by='Horas', ascending=False, inplace=True)
    lista.reset_index(drop=True, inplace=True)
    return lista

