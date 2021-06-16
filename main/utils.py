# -*- coding: utf-8 -*-
from hourcompensator.main.io_utils import redondear
import datetime as dt
import numpy as np
import datetime as dt
import numpy as np
import pandas as pd


# %% funciones de compensación
# Hacemos funcion para compensar la entrada
# ahora tenemos que asignar refrigerio
# input -> dfs,dft,dfh,holgura_critica,limite_corte, comp_max (% de maximo de hhee a compensar según las horas planificadas), turno_minimo
# k_a (indicar si se compensa según la Holgura_Kronos (Kronos) u Holgura_Actual (Actual))
# output -> out_dfh,out_dft,horas_compensadas  (copia de: dfh + dft + contador de horas compensadas)
def compensar_entrada(semana, dft, dfh, holgura_critica, limite_corte, comp_max,
                      horas_compensadas_salida, turno_minimo, k_a, hh_ee_max, df_hhee,
                      maximo_compensacion_dia):
    dft = dft.copy()
    dfh = dfh.copy()
    horas_compensadas = 0
    for s in dfh['Sede'].unique():
        max_hh_ee = df_hhee.loc[df_hhee['Sede'] == s, 'HHEE Totales'].values[0] * hh_ee_max
        horas_planificacion_semana = dfh.loc[
            (dfh['Semana'] == semana) & (dfh['Sede'] == s), 'Horario_{}'.format(k_a)].sum()
        max_por_compensar = horas_planificacion_semana * comp_max
        maximo_compensacion_dia = maximo_compensacion_dia * \
                                  df_hhee.loc[df_hhee['Sede'] == s, 'HHEE Totales'].values[0]
        for f in dfh['Fecha'][dfh['Semana'] == semana].unique():
            # ordenamos por mayor a menor horas el df por compensar
            comp = dft.loc[(dft['Fecha'] == f) & (dft['Sede'] == s)].copy()
            comp.sort_values(by='Horas', ascending=False, inplace=True)
            ids = comp.ID.unique()
            horas_compensadas_dia = 0
            for i in ids:
                if comp.Horas[comp.ID == i][comp.Fecha == f][comp.Sede == s].values[0] >= 0.25:
                    # guardamos entrada y salida para ver si podemos compensar
                    entrada = comp.loc[
                        (comp.ID == i) & (comp.Fecha == f) & (comp.Sede == s), 'Entrada'].values[0]
                    salida = comp.loc[
                        (comp.ID == i) & (comp.Fecha == f) & (comp.Sede == s), 'Salida'].values[0]
                    entrada = redondear(entrada, 'entrada')
                    salida = redondear(salida, 'salida')
                    # anillamos condiciones para ver si podemos seguir compensando
                    for c in range(limite_corte - 1, -1, -1):
                        if (np.all((dfh['Holgura_{}'.format(k_a)][dfh['Sede'] == s][
                                        dfh['Fecha'] == f][dfh['Hora'] >= entrada][dfh['Hora'] <= (
                                entrada + dt.timedelta(
                            seconds=c * 15 * 60))].values > holgura_critica)) and
                                (comp.Horas[comp.ID == i][comp.Fecha == f].values[0] >= 0.25 * (
                                        c + 1)) and
                                (((salida - (entrada + dt.timedelta(
                                    seconds=(c + 1) * 15 * 60))).total_seconds() / 3600 >= turno_minimo) or
                                 ((salida - (entrada + dt.timedelta(
                                     seconds=(c + 1) * 15 * 60))).total_seconds() / 3600 == 0)) and
                                ((horas_compensadas + (
                                        c + 1) * 15 + horas_compensadas_salida) / 60 <= max_hh_ee) and
                                ((horas_compensadas + (
                                        c + 1) * 15 + horas_compensadas_salida) / 60 <= max_por_compensar)):
                            # %% agregamos las restricciones de los refrigerios
                            entrada_nueva = dft.loc[(dft.ID == i) & (dft.Fecha == f) &
                                                    (dft.Sede == s), 'Entrada'].values[
                                                0] + dt.timedelta(seconds=(c + 1) * 15 * 60)
                            if ((salida - entrada_nueva).total_seconds() / 3600 >= 5.25):
                                # Capturamos el refrigerio
                                refrigerio = \
                                dft.loc[(dft.ID == i) & (dft.Fecha == f), 'BreakIn'].values[0]
                                # Primero vemos si tiene asignado el refrigerio
                                if refrigerio is not np.nan:
                                    refrigerio = refrigerio

                                else:
                                    # ponemos cualquier cosa
                                    refrigerio = dt.datetime(2020, 1, 1, 0, 0)

                                # Sumamos la hora de refrigerio a la holgura
                                dfh['Holgura_Refrigerio'] = dfh[
                                    'Holgura_{}'.format(k_a)]  # creamos col. auxiliar

                                dfh.loc[((dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                         (dfh['Hora'] >= refrigerio) & (dfh['Hora'] < (
                                                    refrigerio + dt.timedelta(seconds=3600))) &
                                         (dfh['Hora'] >= entrada_nueva)),
                                        'Holgura_Refrigerio'] = dfh.loc[((dfh['Sede'] == s) & (
                                            dfh['Fecha'] == f) &
                                                                         (dfh[
                                                                              'Hora'] >= refrigerio) & (
                                                                                     dfh['Hora'] < (
                                                                                         refrigerio + dt.timedelta(
                                                                                     seconds=3600))) &
                                                                         (dfh[
                                                                              'Hora'] >= entrada_nueva)),
                                                                        'Holgura_Refrigerio'] + 1

                                # Verificamos si podemos asignar el refrigerio en otro lado
                                # Condiciones:
                                # 1) 3 horas despues de la entrada
                                # 2) 2 horas antes de la salida de la entrada
                                # 3) Si la entrada es antes de las 14:00
                                # 3.1) Entre las 11:30 y 16:30
                                # 3.2) Tiene que trabajar 1 hora despues de volver del refrigerio

                                # Vemos si entra antes de las 14:00
                                if entrada_nueva.time() <= dt.time(14, 0):
                                    l1 = dt.datetime.combine(pd.to_datetime(f), dt.time(11, 30))
                                    l2 = dt.datetime.combine(pd.to_datetime(f), dt.time(16, 30))
                                    holgura_refrigerio = dfh.loc[
                                        ((dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                         (dfh['Hora'] >= (entrada_nueva + dt.timedelta(
                                             seconds=3600 * 1))) &
                                         (dfh['Hora'] <= (
                                                     salida - dt.timedelta(seconds=3600 * 1))) &
                                         (dfh['Hora'] >= l1) &
                                         (dfh['Hora'] <= l2)),
                                        'Holgura_Refrigerio'].values
                                    franja_refrigerio = dfh.loc[
                                        ((dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                         (dfh['Hora'] >= (entrada_nueva + dt.timedelta(
                                             seconds=3600 * 1))) &
                                         (dfh['Hora'] <= (
                                                     salida - dt.timedelta(seconds=3600 * 1))) &
                                         (dfh['Hora'] >= l1) &
                                         (dfh['Hora'] <= l2)),
                                        'Hora'].values
                                    # Entonces revisamos si tiene holgura para asignar el refrigerio
                                    if len(holgura_refrigerio) >= 4:
                                        for r in range(0, len(holgura_refrigerio) - 4):
                                            if np.all(
                                                    holgura_refrigerio[r:r + 4] > holgura_critica):
                                                # Entonces asignamos refrigerio y compensamos
                                                # 0 sumamos la holgura de donde estaba el refrigerio antes
                                                dfh.loc[((dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                                         (dfh['Hora'] >= refrigerio) & (
                                                                     dfh['Hora'] < (
                                                                         refrigerio + dt.timedelta(
                                                                     seconds=3600))) &
                                                         (dfh['Hora'] >= entrada_nueva)),
                                                        'Holgura_{}'.format(k_a)] = dfh.loc[((dfh[
                                                                                                  'Sede'] == s) & (
                                                                                                         dfh[
                                                                                                             'Fecha'] == f) &
                                                                                             (dfh[
                                                                                                  'Hora'] >= refrigerio) & (
                                                                                                         dfh[
                                                                                                             'Hora'] < (
                                                                                                                     refrigerio + dt.timedelta(
                                                                                                                 seconds=3600))) &
                                                                                             (dfh[
                                                                                                  'Hora'] >= entrada_nueva)),
                                                                                            'Holgura_{}'.format(
                                                                                                k_a)] + 1
                                                # 1ero corregimos curva de refrigerio
                                                r1 = franja_refrigerio[r:r + 4][0]
                                                r2 = franja_refrigerio[r:r + 4][-1] + dt.timedelta(
                                                    minutes=15)
                                                dfh.loc[((dfh['Fecha'] == f) &
                                                         (dfh['Sede'] == s) &
                                                         (dfh['Hora'] >= r1) &
                                                         (dfh['Hora'] < r2)), 'Holgura_{}'.format(
                                                    k_a)] = dfh.loc[((dfh['Fecha'] == f) &
                                                                     (dfh['Sede'] == s) &
                                                                     (dfh['Hora'] >= r1) &
                                                                     (dfh[
                                                                          'Hora'] < r2)), 'Holgura_{}'.format(
                                                    k_a)] - 1
                                                # 2do asignamos refrigerio
                                                dft.loc[(dft.ID == i) & (
                                                            dft.Fecha == f), 'BreakIn'] = r1
                                                dft.loc[(dft.ID == i) & (
                                                            dft.Fecha == f), 'BreakOut'] = r2
                                                # 3ero compensamos la entrada
                                                dft.loc[(dft.ID == i) & (dft.Fecha == f) &
                                                        (dft.Sede == s), 'Entrada'] = \
                                                dft.loc[(dft.ID == i) & (dft.Fecha == f) &
                                                        (dft.Sede == s), 'Entrada'].values[
                                                    0] + dt.timedelta(seconds=(c + 1) * 15 * 60)
                                                # 4to corregimos la holgura
                                                dfh.loc[(dfh['Fecha'] == f) &
                                                        (dfh['Sede'] == s) &
                                                        (dfh['Hora'] <= (entrada + dt.timedelta(
                                                            seconds=c * 15 * 60))) &
                                                        (dfh[
                                                             'Hora'] >= entrada), 'Holgura_{}'.format(
                                                    k_a)] = dfh.loc[(dfh['Fecha'] == f) &
                                                                    (dfh['Sede'] == s) &
                                                                    (dfh['Hora'] <= (
                                                                                entrada + dt.timedelta(
                                                                            seconds=c * 15 * 60))) &
                                                                    (dfh[
                                                                         'Hora'] >= entrada), 'Holgura_{}'.format(
                                                    k_a)] - 1
                                                # 5to agregamos contador
                                                horas_compensadas += (c + 1) * 15
                                                # 6to lo restamos de la bolsa de horas extra de la persona
                                                dft.loc[(dft['ID'] == i), 'Horas'] = \
                                                dft.loc[(dft['ID'] == i), 'Horas'].values[
                                                    0] - 0.25 * (c + 1)
                                                comp.loc[(comp['ID'] == i), 'Horas'] = \
                                                comp.loc[(comp['ID'] == i), 'Horas'].values[
                                                    0] - 0.25 * (c + 1)
                                                break
                                        break
                                        # Si no entra antes de las 14:00
                                # aplicamos los criterios de:
                                # 3 horas despues de entrada y 2 horas antes de salida
                                else:
                                    despues_entrada = 2
                                    antes_salida = 2
                                    holgura_refrigerio = dfh.loc[
                                        (dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                        (dfh['Hora'] >= (entrada_nueva + dt.timedelta(
                                            hours=despues_entrada))) &
                                        (dfh['Hora'] <= (salida - dt.timedelta(
                                            hours=antes_salida))), 'Holgura_Refrigerio'].values

                                    franja_refrigerio = dfh.loc[
                                        (dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                        (dfh['Hora'] >= (entrada_nueva + dt.timedelta(
                                            hours=despues_entrada))) &
                                        (dfh['Hora'] <= (salida - dt.timedelta(
                                            hours=antes_salida))), 'Hora'].values

                                    # Entonces revisamos si tiene holgura para asignar el refrigerio
                                    if len(holgura_refrigerio) >= 4:
                                        for r in range(0, len(holgura_refrigerio) - 4):
                                            if np.all(
                                                    holgura_refrigerio[r:r + 4] > holgura_critica):
                                                # Entonces asignamos refrigerio y compensamos
                                                # 0 sumamos la holgura de donde estaba el refrigerio antes
                                                dfh.loc[((dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                                         (dfh['Hora'] >= refrigerio) & (
                                                                     dfh['Hora'] < (
                                                                         refrigerio + dt.timedelta(
                                                                     seconds=3600))) &
                                                         (dfh['Hora'] >= entrada_nueva)),
                                                        'Holgura_{}'.format(k_a)] = dfh.loc[((dfh[
                                                                                                  'Sede'] == s) & (
                                                                                                         dfh[
                                                                                                             'Fecha'] == f) &
                                                                                             (dfh[
                                                                                                  'Hora'] >= refrigerio) & (
                                                                                                         dfh[
                                                                                                             'Hora'] < (
                                                                                                                     refrigerio + dt.timedelta(
                                                                                                                 seconds=3600))) &
                                                                                             (dfh[
                                                                                                  'Hora'] >= entrada_nueva)),
                                                                                            'Holgura_{}'.format(
                                                                                                k_a)] + 1
                                                # 1ero corregimos curva de refrigerio
                                                r1 = franja_refrigerio[r:r + 4][0]
                                                r2 = franja_refrigerio[r:r + 4][-1] + dt.timedelta(
                                                    minutes=15)
                                                dfh.loc[(dfh['Fecha'] == f) &
                                                        (dfh['Sede'] == s) &
                                                        (dfh['Hora'] >= r1) &
                                                        (dfh['Hora'] < r2), 'Holgura_{}'.format(
                                                    k_a)] = dfh.loc[(dfh['Fecha'] == f) &
                                                                    (dfh['Sede'] == s) &
                                                                    (dfh['Hora'] >= r1) &
                                                                    (dfh[
                                                                         'Hora'] < r2), 'Holgura_{}'.format(
                                                    k_a)] - 1
                                                # 2do asignamos refrigerio
                                                dft.loc[(dft.ID == i) & (
                                                            dft.Fecha == f), 'BreakIn'] = r1
                                                dft.loc[(dft.ID == i) & (
                                                            dft.Fecha == f), 'BreakOut'] = r2
                                                # 3ero compensamos la entrada
                                                dft.loc[(dft.ID == i) & (dft.Fecha == f) &
                                                        (dft.Sede == s), 'Entrada'] = \
                                                dft.loc[(dft.ID == i) & (dft.Fecha == f) &
                                                        (dft.Sede == s), 'Entrada'].values[
                                                    0] + dt.timedelta(seconds=(c + 1) * 15 * 60)
                                                # 4to corregimos la holgura
                                                dfh.loc[(dfh['Fecha'] == f) &
                                                        (dfh['Sede'] == s) &
                                                        (dfh['Hora'] <= (entrada + dt.timedelta(
                                                            seconds=c * 15 * 60))) &
                                                        (dfh[
                                                             'Hora'] >= entrada), 'Holgura_{}'.format(
                                                    k_a)] = dfh.loc[(dfh['Fecha'] == f) &
                                                                    (dfh['Sede'] == s) &
                                                                    (dfh['Hora'] <= (
                                                                                entrada + dt.timedelta(
                                                                            seconds=c * 15 * 60))) &
                                                                    (dfh[
                                                                         'Hora'] >= entrada), 'Holgura_{}'.format(
                                                    k_a)] - 1
                                                # 5to agregamos contador
                                                horas_compensadas += (c + 1) * 15
                                                # 6to lo restamos de la bolsa de horas extra de la persona
                                                dft.loc[(dft['ID'] == i), 'Horas'] = \
                                                dft.loc[(dft['ID'] == i), 'Horas'].values[
                                                    0] - 0.25 * (c + 1)
                                                comp.loc[(comp['ID'] == i), 'Horas'] = \
                                                comp.loc[(comp['ID'] == i), 'Horas'].values[
                                                    0] - 0.25 * (c + 1)
                                                break
                                        break


                            # %% sin refrigerio
                            else:
                                # nos alejamos y compensamos la entrada
                                dft.loc[(dft.ID == i) &
                                        (dft.Fecha == f) &
                                        (dft.Sede == s),
                                        'Entrada'] = dft.loc[(dft.ID == i) &
                                                             (dft.Fecha == f) &
                                                             (dft.Sede == s),
                                                             'Entrada'].values[0] + dt.timedelta(
                                    seconds=(c + 1) * 15 * 60)
                                # corregimos la holgura
                                dfh.loc[(dfh['Fecha'] == f) &
                                        (dfh['Sede'] == s) &
                                        (dfh['Hora'] <= (
                                                    entrada + dt.timedelta(seconds=c * 15 * 60))) &
                                        (dfh['Hora'] >= entrada), 'Holgura_{}'.format(k_a)] = \
                                dfh.loc[(dfh['Fecha'] == f) &
                                        (dfh['Sede'] == s) &
                                        (dfh['Hora'] <= (
                                                    entrada + dt.timedelta(seconds=c * 15 * 60))) &
                                        (dfh['Hora'] >= entrada), 'Holgura_{}'.format(k_a)] - 1
                                # agregamos contador
                                horas_compensadas += (c + 1) * 15
                                # lo restamos de la bolsa de horas extra de la persona
                                dft.loc[(dft['ID'] == i), 'Horas'] = \
                                dft.loc[(dft['ID'] == i), 'Horas'].values[0] - 0.25 * (c + 1)
                                comp.loc[(comp['ID'] == i), 'Horas'] = \
                                comp.loc[(comp['ID'] == i), 'Horas'].values[0] - 0.25 * (c + 1)
                                break
    horas_compensadas = horas_compensadas + horas_compensadas_salida
    return dfh, dft, horas_compensadas


# %% Hacemos funcion para compensar la salida
# input -> dfs,dft,dfh,holgura_critica,limite_corte,comp_max (% de maximo de hhee a compensar), turno_minimo
# horas_compensadas_entrada (para usarlo como sumador al contador con tal de no pasarse del limite de compensacion)
# k_a (indicar si se compensa según la Holgura_Kronos (Kronos) u Holgura_Actual (Actuar))
# output -> out_dfh,out_dft,horas_compensadas (copia de: dfh + dft + contador de horas compensadas)
def compensar_salida(semana, dft, dfh, holgura_critica,
                     limite_corte, comp_max, horas_compensadas_entrada, turno_minimo, k_a,
                     hh_ee_max, df_hhee,
                     maximo_compensacion_dia):
    dft = dft.copy()
    dfh = dfh.copy()
    horas_compensadas = 0
    for s in dfh['Sede'].unique():
        max_hh_ee = df_hhee.loc[df_hhee['Sede'] == s, 'HHEE Totales'].values[0] * hh_ee_max
        horas_planificacion_semana = dfh.loc[
            (dfh['Semana'] == semana) & (dfh['Sede'] == s), 'Horario_{}'.format(k_a)].sum()
        max_por_compensar = horas_planificacion_semana * comp_max
        maximo_compensacion_dia = maximo_compensacion_dia * \
                                  df_hhee.loc[df_hhee['Sede'] == s, 'HHEE Totales'].values[0]
        for f in dfh['Fecha'][dfh['Semana'] == semana].unique():
            # ordenamos por mayor a menor horas el df por compensar
            comp = dft.loc[(dft['Fecha'] == f) & (dft['Sede'] == s)].copy()
            comp.sort_values(by='Horas', ascending=False, inplace=True)
            ids = comp.ID.unique()
            for i in ids:
                if comp.Horas[comp.ID == i][comp.Fecha == f].values[0] >= 0.25:
                    # guardamos entrada y salida para ver si podemos compensar
                    entrada = comp.loc[
                        (comp.ID == i) & (comp.Fecha == f) & (comp.Sede == s), 'Entrada'].values[0]
                    salida = comp.loc[
                        (comp.ID == i) & (comp.Fecha == f) & (comp.Sede == s), 'Salida'].values[0]
                    entrada = redondear(entrada, 'entrada')
                    salida = redondear(salida, 'salida')
                    # anillamos condiciones para ver si podemos seguir compensando
                    for c in range(limite_corte - 1, -1, -1):
                        if (np.all((dfh['Holgura_{}'.format(k_a)][dfh['Fecha'] == f][
                                        dfh['Sede'] == s][dfh['Hora'] <= salida][dfh['Hora'] >= (
                                salida - dt.timedelta(
                            seconds=c * 15 * 60))].values > holgura_critica)) and
                                (comp.Horas[comp.ID == i][comp.Fecha == f].values[0] >= 0.25 * (
                                        c + 1)) and
                                ((((salida - dt.timedelta(seconds=(c + 1) * 15 * 60)) - entrada).total_seconds() / 3600 >= turno_minimo) or
                                 ((salida - (entrada + dt.timedelta(seconds=(c + 1) * 15 * 60))).total_seconds() / 3600 == 0)) and
                                (((horas_compensadas + (
                                        c + 1) * 15) + horas_compensadas_entrada) / 60 <= max_hh_ee) and
                                (((horas_compensadas + (
                                        c + 1) * 15) + horas_compensadas_entrada) / 60 <= max_por_compensar)):

                            # %% agregamos las restricciones de los refrigerios
                            salida_nueva = dft.loc[(dft.ID == i) &
                                                   (dft.Fecha == f) &
                                                   (dft.Sede == s),
                                                   'Salida'].values[0] - dt.timedelta(
                                seconds=(c + 1) * 15 * 60)
                            if ((salida_nueva - entrada).total_seconds() / 3600 >= 5.25):
                                # Capturamos el refrigerio
                                refrigerio = \
                                dft.loc[(dft.ID == i) & (dft.Fecha == f), 'BreakIn'].values[0]
                                # Primero vemos si tiene asignado el refrigerio
                                if refrigerio is not np.nan:
                                    refrigerio = refrigerio

                                else:
                                    # ponemos cualquier cosa
                                    refrigerio = dt.datetime(2020, 1, 1, 0, 0)

                                # Sumamos la hora de refrigerio a la holgura
                                dfh['Holgura_Refrigerio'] = dfh[
                                    'Holgura_{}'.format(k_a)]  # creamos col. auxiliar

                                dfh.loc[((dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                         (dfh['Hora'] >= refrigerio) & (dfh['Hora'] < (
                                                    refrigerio + dt.timedelta(seconds=3600))) &
                                         (dfh['Hora'] >= entrada) & (dfh['Hora'] < salida_nueva)),
                                        'Holgura_Refrigerio'] = dfh.loc[((dfh['Sede'] == s) & (
                                            dfh['Fecha'] == f) &
                                                                         (dfh[
                                                                              'Hora'] >= refrigerio) & (
                                                                                     dfh['Hora'] < (
                                                                                         refrigerio + dt.timedelta(
                                                                                     seconds=3600))) &
                                                                         (dfh[
                                                                              'Hora'] >= entrada) & (
                                                                                     dfh[
                                                                                         'Hora'] < salida_nueva)),
                                                                        'Holgura_Refrigerio'] + 1

                                # Verificamos si podemos asignar el refrigerio en otro lado
                                # Condiciones:
                                # 1) 3 horas despues de la entrada
                                # 2) 2 horas antes de la salida de la entrada
                                # 3) Si la entrada es antes de las 14:00
                                # 3.1) Entre las 11:30 y 16:30
                                # 3.2) Tiene que trabajar 1 hora despues de volver del refrigerio

                                # Vemos si entra antes de las 14:00
                                if entrada.time() <= dt.time(14, 0):
                                    l1 = dt.datetime.combine(pd.to_datetime(f), dt.time(11, 30))
                                    l2 = dt.datetime.combine(pd.to_datetime(f), dt.time(16, 30))
                                    holgura_refrigerio = dfh.loc[
                                        ((dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                         (dfh['Hora'] >= (
                                                     entrada + dt.timedelta(seconds=3600 * 1))) &
                                         (dfh['Hora'] <= (salida_nueva - dt.timedelta(
                                             seconds=3600 * 1))) &
                                         (dfh['Hora'] >= l1) &
                                         (dfh['Hora'] <= l2)),
                                        'Holgura_Refrigerio'].values
                                    franja_refrigerio = dfh.loc[
                                        ((dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                         (dfh['Hora'] >= (
                                                     entrada + dt.timedelta(seconds=3600 * 1))) &
                                         (dfh['Hora'] <= (salida_nueva - dt.timedelta(
                                             seconds=3600 * 1))) &
                                         (dfh['Hora'] >= l1) &
                                         (dfh['Hora'] <= l2)),
                                        'Hora'].values
                                    # Entonces revisamos si tiene holgura para asignar el refrigerio
                                    if len(holgura_refrigerio) >= 4:
                                        for r in range(0, len(holgura_refrigerio) - 4):
                                            if np.all(
                                                    holgura_refrigerio[r:r + 4] > holgura_critica):
                                                # Entonces asignamos refrigerio y compensamos
                                                # 0 sumamos la holgura de donde estaba el refrigerio antes
                                                dfh.loc[((dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                                         (dfh['Hora'] >= refrigerio) & (
                                                                     dfh['Hora'] < (
                                                                         refrigerio + dt.timedelta(
                                                                     seconds=3600))) &
                                                         (dfh['Hora'] >= entrada) & (
                                                                     dfh['Hora'] < salida_nueva)),
                                                        'Holgura_{}'.format(k_a)] = dfh.loc[((dfh[
                                                                                                  'Sede'] == s) & (
                                                                                                         dfh[
                                                                                                             'Fecha'] == f) &
                                                                                             (dfh[
                                                                                                  'Hora'] >= refrigerio) & (
                                                                                                         dfh[
                                                                                                             'Hora'] < (
                                                                                                                     refrigerio + dt.timedelta(
                                                                                                                 seconds=3600))) &
                                                                                             (dfh[
                                                                                                  'Hora'] >= entrada) & (
                                                                                                         dfh[
                                                                                                             'Hora'] < salida_nueva)),
                                                                                            'Holgura_{}'.format(
                                                                                                k_a)] + 1
                                                # 1ero corregimos curva de refrigerio
                                                r1 = franja_refrigerio[r:r + 4][0]
                                                r2 = franja_refrigerio[r:r + 4][-1] + dt.timedelta(
                                                    minutes=15)
                                                dfh.loc[((dfh['Fecha'] == f) &
                                                         (dfh['Sede'] == s) &
                                                         (dfh['Hora'] >= r1) &
                                                         (dfh['Hora'] < r2)), 'Holgura_{}'.format(
                                                    k_a)] = dfh.loc[((dfh['Fecha'] == f) &
                                                                     (dfh['Sede'] == s) &
                                                                     (dfh['Hora'] >= r1) &
                                                                     (dfh[
                                                                          'Hora'] < r2)), 'Holgura_{}'.format(
                                                    k_a)] - 1
                                                # 2do asignamos refrigerio
                                                dft.loc[(dft.ID == i) & (
                                                            dft.Fecha == f), 'BreakIn'] = r1
                                                dft.loc[(dft.ID == i) & (
                                                            dft.Fecha == f), 'BreakOut'] = r2
                                                # 3ero compensamos la salida
                                                dft.loc[(dft.ID == i) & (dft.Fecha == f) &
                                                        (dft.Sede == s), 'Salida'] = \
                                                dft.loc[(dft.ID == i) & (dft.Fecha == f) &
                                                        (dft.Sede == s), 'Salida'].values[
                                                    0] - dt.timedelta(seconds=(c + 1) * 15 * 60)
                                                # 4to corregimos la holgura
                                                dfh.loc[(dfh['Fecha'] == f) &
                                                        (dfh['Sede'] == s) &
                                                        (dfh['Hora'] >= (salida - dt.timedelta(
                                                            seconds=c * 15 * 60))) &
                                                        (dfh[
                                                             'Hora'] <= salida), 'Holgura_{}'.format(
                                                    k_a)] = dfh.loc[(dfh['Fecha'] == f) &
                                                                    (dfh['Sede'] == s) &
                                                                    (dfh['Hora'] >= (
                                                                                salida - dt.timedelta(
                                                                            seconds=c * 15 * 60))) &
                                                                    (dfh[
                                                                         'Hora'] <= salida), 'Holgura_{}'.format(
                                                    k_a)] - 1
                                                # 5to agregamos contador
                                                horas_compensadas += (c + 1) * 15
                                                # 6to lo restamos de la bolsa de horas extra de la persona
                                                dft.loc[(dft['ID'] == i), 'Horas'] = \
                                                dft.loc[(dft['ID'] == i), 'Horas'].values[
                                                    0] - 0.25 * (c + 1)
                                                comp.loc[(comp['ID'] == i), 'Horas'] = \
                                                comp.loc[(comp['ID'] == i), 'Horas'].values[
                                                    0] - 0.25 * (c + 1)
                                                break
                                        break
                                        # Si no entra antes de las 14:00
                                # aplicamos los criterios de:
                                # 3 horas despues de entrada y 2 horas antes de salida
                                else:
                                    despues_entrada = 2
                                    antes_salida = 2
                                    holgura_refrigerio = dfh.loc[
                                        (dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                        (dfh['Hora'] >= (entrada + dt.timedelta(
                                            hours=despues_entrada))) &
                                        (dfh['Hora'] <= (salida_nueva - dt.timedelta(
                                            hours=antes_salida))), 'Holgura_Refrigerio'].values

                                    franja_refrigerio = dfh.loc[
                                        (dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                        (dfh['Hora'] >= (entrada + dt.timedelta(
                                            hours=despues_entrada))) &
                                        (dfh['Hora'] <= (salida_nueva - dt.timedelta(
                                            hours=antes_salida))), 'Hora'].values

                                    # Entonces revisamos si tiene holgura para asignar el refrigerio
                                    if len(holgura_refrigerio) >= 4:
                                        for r in range(0, len(holgura_refrigerio) - 4):
                                            if np.all(
                                                    holgura_refrigerio[r:r + 4] > holgura_critica):
                                                # Entonces asignamos refrigerio y compensamos
                                                # 0 sumamos la holgura de donde estaba el refrigerio antes
                                                dfh.loc[((dfh['Sede'] == s) & (dfh['Fecha'] == f) &
                                                         (dfh['Hora'] >= refrigerio) & (
                                                                     dfh['Hora'] < (
                                                                         refrigerio + dt.timedelta(
                                                                     seconds=3600))) &
                                                         (dfh['Hora'] >= entrada) & (
                                                                     dfh['Hora'] < salida_nueva)),
                                                        'Holgura_{}'.format(k_a)] = dfh.loc[((dfh[
                                                                                                  'Sede'] == s) & (
                                                                                                         dfh[
                                                                                                             'Fecha'] == f) &
                                                                                             (dfh[
                                                                                                  'Hora'] >= refrigerio) & (
                                                                                                         dfh[
                                                                                                             'Hora'] < (
                                                                                                                     refrigerio + dt.timedelta(
                                                                                                                 seconds=3600))) &
                                                                                             (dfh[
                                                                                                  'Hora'] >= entrada) & (
                                                                                                         dfh[
                                                                                                             'Hora'] < salida_nueva)),
                                                                                            'Holgura_{}'.format(
                                                                                                k_a)] + 1
                                                # 1ero corregimos curva de refrigerio
                                                r1 = franja_refrigerio[r:r + 4][0]
                                                r2 = franja_refrigerio[r:r + 4][-1] + dt.timedelta(
                                                    minutes=15)
                                                dfh.loc[(dfh['Fecha'] == f) &
                                                        (dfh['Sede'] == s) &
                                                        (dfh['Hora'] >= r1) &
                                                        (dfh['Hora'] < r2), 'Holgura_{}'.format(
                                                    k_a)] = dfh.loc[(dfh['Fecha'] == f) &
                                                                    (dfh['Sede'] == s) &
                                                                    (dfh['Hora'] >= r1) &
                                                                    (dfh[
                                                                         'Hora'] < r2), 'Holgura_{}'.format(
                                                    k_a)] - 1
                                                # 2do asignamos refrigerio
                                                dft.loc[(dft.ID == i) & (
                                                            dft.Fecha == f), 'BreakIn'] = r1
                                                dft.loc[(dft.ID == i) & (
                                                            dft.Fecha == f), 'BreakOut'] = r2
                                                # 3ero compensamos la entrada
                                                dft.loc[(dft.ID == i) & (dft.Fecha == f) &
                                                        (dft.Sede == s), 'Salida'] = \
                                                dft.loc[(dft.ID == i) & (dft.Fecha == f) &
                                                        (dft.Sede == s), 'Salida'].values[
                                                    0] - dt.timedelta(seconds=(c + 1) * 15 * 60)
                                                # 4to corregimos la holgura
                                                dfh.loc[(dfh['Fecha'] == f) &
                                                        (dfh['Sede'] == s) &
                                                        (dfh['Hora'] >= (salida - dt.timedelta(
                                                            seconds=c * 15 * 60))) &
                                                        (dfh[
                                                             'Hora'] <= salida), 'Holgura_{}'.format(
                                                    k_a)] = dfh.loc[(dfh['Fecha'] == f) &
                                                                    (dfh['Sede'] == s) &
                                                                    (dfh['Hora'] >= (
                                                                                salida - dt.timedelta(
                                                                            seconds=c * 15 * 60))) &
                                                                    (dfh[
                                                                         'Hora'] <= salida), 'Holgura_{}'.format(
                                                    k_a)] - 1
                                                # 5to agregamos contador
                                                horas_compensadas += (c + 1) * 15
                                                # 6to lo restamos de la bolsa de horas extra de la persona
                                                dft.loc[(dft['ID'] == i), 'Horas'] = \
                                                dft.loc[(dft['ID'] == i), 'Horas'].values[
                                                    0] - 0.25 * (c + 1)
                                                comp.loc[(comp['ID'] == i), 'Horas'] = \
                                                comp.loc[(comp['ID'] == i), 'Horas'].values[
                                                    0] - 0.25 * (c + 1)
                                                break
                                        break

                            # %% sin refrigerio
                            else:
                                dft.loc[(dft.ID == i) &
                                        (dft.Fecha == f) &
                                        (dft.Sede == s),
                                        'Salida'] = dft.loc[(dft.ID == i) &
                                                            (dft.Fecha == f) &
                                                            (dft.Sede == s),
                                                            'Salida'].values[0] - dt.timedelta(
                                    seconds=(c + 1) * 15 * 60)
                                # corregimos la holgura
                                dfh.loc[(dfh['Fecha'] == f) &
                                        (dfh['Sede'] == s) &
                                        (dfh['Hora'] >= (
                                                    salida - dt.timedelta(seconds=c * 15 * 60))) &
                                        (dfh['Hora'] <= salida), 'Holgura_{}'.format(k_a)] = \
                                dfh.loc[(dfh['Fecha'] == f) &
                                        (dfh['Sede'] == s) &
                                        (dfh['Hora'] >= (
                                                    salida - dt.timedelta(seconds=c * 15 * 60))) &
                                        (dfh['Hora'] <= salida), 'Holgura_{}'.format(k_a)] - 1
                                # agregamos contador
                                horas_compensadas += (c + 1) * 15
                                # lo restamos de la bolsa de horas extra de la persona
                                dft.loc[(dft['ID'] == i), 'Horas'] = \
                                dft.loc[(dft['ID'] == i), 'Horas'].values[0] - 0.25 * (c + 1)
                                comp.loc[(comp['ID'] == i), 'Horas'] = \
                                comp.loc[(comp['ID'] == i), 'Horas'].values[0] - 0.25 * (c + 1)
                                break
    horas_compensadas_totales = (horas_compensadas + horas_compensadas_entrada)

    return dfh, dft, horas_compensadas_totales


# %% Funcion que compensa entradas y salidas, agrega las dos funciones anteriores
def compensador(semana_a_compensar, dfh_input, dft_input,
                holgura_critica,
                limite_corte,
                comp_max,
                turno_minimo,
                k_a,
                hh_ee_max,
                df_hhee, maximo_compensacion_dia):
    dft_input = dft_input.copy()
    dfh_input = dfh_input.copy()

    horas_compensadas_entrada = 0
    horas_compensadas_salida = 0

    # Se compensa la salida
    dfh_input, dft_input, horas_compensadas_salida = compensar_salida(semana_a_compensar, dft_input,
                                                                      dfh_input,
                                                                      holgura_critica=holgura_critica,
                                                                      limite_corte=limite_corte,
                                                                      comp_max=comp_max,
                                                                      horas_compensadas_entrada=horas_compensadas_entrada,
                                                                      turno_minimo=turno_minimo,
                                                                      k_a=k_a,
                                                                      hh_ee_max=hh_ee_max,
                                                                      df_hhee=df_hhee,
                                                                      maximo_compensacion_dia=maximo_compensacion_dia)

    # Se compensa la entrada
    dfh_input, dft_input, horas_compensadas_entrada = compensar_entrada(semana_a_compensar,
                                                                        dft_input, dfh_input,
                                                                        holgura_critica=holgura_critica,
                                                                        limite_corte=limite_corte,
                                                                        comp_max=comp_max,
                                                                        horas_compensadas_salida=horas_compensadas_salida,
                                                                        turno_minimo=turno_minimo,
                                                                        k_a=k_a,
                                                                        hh_ee_max=hh_ee_max,
                                                                        df_hhee=df_hhee,
                                                                        maximo_compensacion_dia=maximo_compensacion_dia)

    return dfh_input, dft_input


# %% Funcion para calcular la columna Horario_Real según el input de horarios
# input -> dft, dfh
# output -> procesa y crea una columna extra (Horario_Compensado)
def horario_compensado_final(dfh, dft):
    for s in dfh.Sede.unique():
        for h in dfh.Hora.unique():
            dfh.loc[(dfh['Hora'] == h) & (dfh['Sede'] == s), 'Horario_Compensado'] = len(
                dft.loc[(dft['Entrada'] <= h) &
                        (dft['Salida'] > h) &
                        ((dft['BreakIn'] < h) & (dft['BreakOut'] <= h) |
                         (dft['BreakIn'] > h) & (dft['BreakOut'] >= h) |
                         (dft['BreakIn'].isna()) | (dft['BreakOut'].isna())) &
                        (dft['Sede'] == s), 'ID'].unique())


# %% funciones para calcular compensación y horario actual
# Calculador de compensacion con respecto a antiguo
# input -> dft_antiguo, dft_nuevo
# output -> dft_nuevo['Compensado'] (devuelve la columna de compensacion)
def cuanto_compensa(dft_antiguo, dft_nuevo):
    dft_nuevo['Compensado'] = 0
    for i in dft_nuevo.ID.unique():
        for f in dft_nuevo.Fecha[dft_nuevo.ID == i].unique():
            Compensado = \
            dft_nuevo.loc[(dft_nuevo['ID'] == i) & (dft_nuevo['Fecha'] == f), 'Entrada'].values[0] - \
            dft_antiguo.loc[
                (dft_antiguo['ID'] == i) & (dft_antiguo['Fecha'] == f), 'Entrada'].values[0]
            dft_nuevo.loc[
                (dft_nuevo['ID'] == i) & (dft_nuevo['Fecha'] == f), 'Compensado'] = Compensado
    return dft_nuevo['Compensado']









