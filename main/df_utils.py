# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd


# %% Funcion para hacer copia de seguridad y renombra columnas
# renombra las siguientes columnas:
# Entrada, Salida
# Horario_Actual, Holgura
# input -> dfh, dft, dfac, dfj
# output -> dfh_antiguo (con nombres cambiados), dft_antiguo (con nombres cambiados)
# -> dfac_antiguo, dfj_antiguo
def old(dfh, dft, dfac, dfj):
    dfh_antiguo = dfh.copy()
    dft_antiguo = dft.copy()
    dfac_antiguo = dfac.copy()
    dfj_antiguo = dfj.copy()

    dft_antiguo = dft_antiguo.rename(
        {'Entrada': 'Entrada_old', 'Salida': 'Salida_old', 'BreakIn': 'BreakIn_old',
         'BreakOut': 'BreakOut_old', 'Horas': 'Horas_old'}, axis=1)
    for c in dfh_antiguo.columns[5:]:
        dfh_antiguo = dfh_antiguo.rename({c: '{}_old'.format(c)}, axis=1)
    return dfh_antiguo, dft_antiguo, dfac_antiguo, dfj_antiguo


# %% Funcion para crear DataFrame con las hhee totales por tienda
# parandose en una semana determinada
# input -> dft_old
# output -> hhee
def hh_ee(dft_old, semana):
    sedes = dft_old['Sede'].unique()
    dft_old['Horas_old'].fillna(0, inplace=True)
    hhee = []
    for s in sedes:
        hh_ee_i = 0
        ids = dft_old.loc[(dft_old['Sede'] == s) & (dft_old['Semana'] == semana), 'ID'].unique()
        for i in ids:
            if dft_old.loc[(dft_old['ID'] == i) & (dft_old['Sede'] == s), 'Horas_old'].values[
                0] > 0:
                hh_ee_i += \
                dft_old.loc[(dft_old['ID'] == i) & (dft_old['Sede'] == s), 'Horas_old'].values[0]
        hhee.append([s, hh_ee_i])
    hhee = pd.DataFrame(hhee, columns=['Sede', 'HHEE Totales'])
    return hhee


# %% Funcion que renombra los DataFrames nuevos, mergea con los antiguos y calcula compensacion
# Renombra las siguientes columnas:
# Entrada, Salida
# Horario_Actual, Holgura
# input -> dfh,dft,dfh_old,dft_old
# output -> dfh_new, dft_new
def new(dfh, dft, dfh_old, dft_old):
    dft = dft.rename({'Entrada': 'Entrada_nueva',
                      'Salida': 'Salida_nueva',
                      'BreakIn': 'BreakIn_nuevo',
                      'BreakOut': 'BreakOut_nuevo',
                      'Horas': 'Horas_nueva'}, axis=1)
    dfh = dfh.rename({'Horario_Actual_Real': 'Horario_Actual_Real_nueva',
                      'Holgura_Actual_Real': 'Holgura_Actual_Real_nueva'}, axis=1)

    # mergeamos con los antiguos
    dfh_new = pd.merge(dfh, dfh_old[
        ['Sede', 'Hora', 'Horario_Kronos_old', 'Horario_Actual_old', 'Horario_Actual_Real_old',
         'Holgura_Kronos_old', 'Holgura_Actual_Real_old']],
                       on=['Sede', 'Hora'], how='left')

    dft_new = pd.merge(dft, dft_old,
                       on=['Sede', 'ID', 'Fecha'], how='left')

    # Renombramos las columnas _old
    dft_new = dft_new.rename({'Entrada_old': 'Entrada_antigua',
                              'Salida_old':'Salida_antigua',
                              'BreakIn_old':'BreakIn_antiguo',
                              'BreakOut_old':'BreakOut_antiguo'},
                             axis=1)

    # calculamos ahora la compensacion
    dft_new['Entrada_compensada'] = dft_new['Entrada_nueva'] - dft_new['Entrada_antigua']
    dft_new['Salida_compensada'] = dft_new['Salida_antigua'] - dft_new['Salida_nueva']
    dft_new['Duracion_nueva'] = dft_new['Salida_nueva'] - dft_new['Entrada_nueva']
    dft_new['Duracion_antigua'] = dft_new['Salida_antigua'] - dft_new['Entrada_antigua']

    # Transformamos la compensación de entrada y salida a minutos
    dft_new['Entrada_compensada'] = dft_new['Entrada_compensada'].map(
        lambda x: x.total_seconds() / 3600)
    dft_new['Salida_compensada'] = dft_new['Salida_compensada'].map(
        lambda x: x.total_seconds() / 3600)

    # Seleccionamos solo los que tengan horarios por compensar
    dft_new = dft_new.loc[(dft_new['Entrada_compensada']>0)|(dft_new['Salida_compensada']>0)]
    dft_new.drop_duplicates(inplace=True,ignore_index=True)

    ### Cubrimos la heuristica:
    # Cuando un trabajador tiene derecho a colación y despues de la compensación no tiene
    dft_new['Compensacion_total'] = dft_new['Entrada_compensada']+dft_new['Salida_compensada']
    for i in dft_new.ID.unique():
        for f in dft_new['Fecha'][dft_new['ID']==i].unique():
            # Duracion Antigua
            duracion_antigua = (dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),
                                            'Duracion_antigua'].values[0]/np.timedelta64(1, 's'))/3600
            # Refrigerio Antiguo
            breakin_antiguo = \
            dft_new.loc[(dft_new['ID'] == i) & (dft_new['Fecha'] == f), 'BreakIn_antiguo'].values[0]
            breakout_antiguo = \
            dft_new.loc[(dft_new['ID'] == i) & (dft_new['Fecha'] == f), 'BreakOut_antiguo'].values[
                0]
            # Duracion Nueva
            duracion_nueva =   (dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),
                                            'Duracion_nueva'].values[0]/np.timedelta64(1, 's'))/3600
            # Refrigerio Nuevo
            breakin_nuevo = dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),'BreakIn_nuevo'].values[0]
            breakout_nuevo = dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),'BreakOut_nuevo'].values[0]
            # Compensacion de entrada y salida
            entrada_compensada = dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),
                                        'Entrada_compensada'].values[0]
            salida_compensada = dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),
                                        'Salida_compensada'].values[0]

            # Compensacion_total (para ver si vale la pena quitarle el refrigerio)
            compensacion_total = dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),
                                        'Compensacion_total'].values[0]

            # Vemos si opta a colacion y si queda en horario sin colacion post compensacion
            if duracion_antigua>5 and duracion_nueva<=5 and compensacion_total>1:
                # Se gatilla y quitamos una hora a la entrada o a la salida
                if salida_compensada>=1:
                    dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),
                                        'Salida_compensada'] = salida_compensada - 1
                elif entrada_compensada>=1:
                    dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),
                                        'Entrada_compensada'] = entrada_compensada - 1
                # Si la compensacion de entrada o salida no da >1, entonces
                else:
                    complemento = 1 - entrada_compensada
                    # seteamos en 0 la Entrada_compensada
                    dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),
                                        'Entrada_compensada'] = 0
                    # y le restamos el complemento a la Salida_compensada
                    dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),
                                        'Salida_compensada'] = salida_compensada - complemento
            elif duracion_antigua>5 and duracion_nueva<=5 and compensacion_total<=1:
                # Entonces no le compensamos
                entrada_antigua = dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),
                                      'Entrada_antigua'].values[0]
                salida_antigua = dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),
                                      'Salida_antigua'].values[0]
                # Descompensamos
                dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),
                                      'Entrada_nueva'] = entrada_antigua
                dft_new.loc[(dft_new['ID']==i)&(dft_new['Fecha']==f),
                                      'Salida_nueva'] = salida_antigua

                dft_new.loc[(dft_new['ID'] == i) & (dft_new['Fecha'] == f),
                            'Entrada_compensada'] = 0
                dft_new.loc[(dft_new['ID'] == i) & (dft_new['Fecha'] == f),
                            'Salida_compensada'] = 0
            if duracion_nueva <= 5:
                # Borramos todos los refrigerios
                dft_new.loc[(dft_new['ID'] == i) & (dft_new['Fecha'] == f),
                            'BreakIn_nuevo'] = np.nan
                dft_new.loc[(dft_new['ID'] == i) & (dft_new['Fecha'] == f),
                            'BreakOut_nuevo'] = np.nan

    # Calculamos la holgura compensada
    print(dfh_new)
    dfh_new['Holgura_Compensada'] = dfh_new['Horario_Actual_Real_old'] - dfh_new['Horario_Compensado']

    # Cambiamos el formato de las fechas para claudio
    dft_new['Entrada_nueva'] = dft_new['Entrada_nueva'].dt.strftime('%d-%m-%Y %H:%M')
    dft_new['Salida_nueva'] = dft_new['Salida_nueva'].dt.strftime('%d-%m-%Y %H:%M')
    dft_new['Fecha']= dft_new['Fecha'].dt.strftime('%d-%m-%Y %H:%M')

    # Seleccionamos solo las columnas importantes
    dft_new2 = dft_new[['Sede','ID','Fecha',
                        'Entrada_nueva','Salida_nueva','BreakIn_nuevo','BreakOut_nuevo',
                        'Entrada_antigua','Salida_antigua','BreakIn_antiguo','BreakOut_antiguo',
                        'Entrada_compensada', 'Salida_compensada',
                        'Duracion_nueva', 'Duracion_antigua']]

    # dft_new
    dft_new = dft_new[['Sede', 'ID', 'Fecha',
                       'Entrada_nueva','Salida_nueva','BreakIn_nuevo','BreakOut_nuevo',
                       'Entrada_antigua','Salida_antigua','BreakIn_antiguo','BreakOut_antiguo',
                       'Entrada_compensada', 'Salida_compensada']]
    # dfh_new
    dfh_new = dfh_new[['Sede', 'Hora',
                       'Labor', 'Horario_Actual_Real_old', 'Horario_Compensado']]

    return dfh_new, dft_new, dft_new2


# %% Funcion para transponer el output de la compensacion y poder generar graficios dinamicos
def trasponer(dfh, semana):
    dfh_t = []
    dfh = dfh.loc[dfh['Semana'] == semana].copy()
    dfh.reset_index(drop=True, inplace=True)
    for e in dfh.Escenario.unique():
        for s in dfh.Sede[dfh.Escenario == e].unique():
            for h in dfh.Hora[dfh.Escenario == e].unique():
                sede = s
                hora = h
                labor = dfh.loc[(dfh['Sede'] == s) &
                                (dfh['Hora'] == h) &
                                (dfh['Escenario'] == e),
                                'Labor'].values[0]
                horario_actual_real_old = dfh.loc[(dfh['Sede'] == s) &
                                                  (dfh['Hora'] == h) &
                                                  (dfh['Escenario'] == e),
                                                  'Horario_Actual_Real_old'].values[0]
                horario_kronos_old = dfh.loc[(dfh['Sede'] == s) &
                                             (dfh['Hora'] == h) &
                                             (dfh['Escenario'] == e),
                                             'Horario_Kronos_old'].values[0]
                horario_compensado = dfh.loc[(dfh['Sede'] == s) &
                                             (dfh['Hora'] == h) &
                                             (dfh['Escenario'] == e),
                                             'Horario_Compensado'].values[0]
                dfh_t.append([sede, hora, semana,
                              'Labor',
                              labor,
                              e])
                dfh_t.append([sede, hora, semana,
                              'Horario_Actual_Real_old',
                              horario_actual_real_old,
                              e])
                dfh_t.append([sede, hora, semana,
                              'Horario_Kronos_old',
                              horario_kronos_old,
                              e])
                dfh_t.append([sede, hora, semana,
                              'Horario_Compensado',
                              horario_compensado,
                              e])
    dfh_t = pd.DataFrame(dfh_t,
                         columns=['Sede', 'Hora', 'Semana', 'Tipo_Curva', 'Valor', 'Escenario'])
    return dfh_t
