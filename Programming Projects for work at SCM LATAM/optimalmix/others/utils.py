import datetime, pandas as pd

shift_parameters = ['salario', 'largosem', 'largomen', 'cotainf', 'cotasup', 'diaslabmin',
                    'diaslabmax', 'zcero', 'productividad', 'ausentismo', 'rotacion', 'contrato',
                    'despido']
shift_boolean_parameters = ['Turnoshx', 'Turnoslegales']
scalar_parameters = ['ppto', 'sobrecargo', 'cu', 'co', 'slmin', 'opmin', 'opmax',
                     'SemCambioDotacion', 'horasmensual', 'mip_gap', 'days_cycle']
boolean_parameters = ['weekday_kind']
timerange_parameters = ['open_start_time', 'open_end_time', 'close_start_time', 'close_end_time']


def prepare_output(solution_dict, shifts, shifts_per_day, start_date, end_date, demanda, G4Semini,
                   shiftshx, salario, periodos, sobrecargo, horasmensual, contrato, despido, cu):
    # Months
    iter_date = start_date
    month_list = []
    count = {}
    for shift in shifts:
        count[shift] = 0
    count['Rango inicio'] = iter_date
    i = 0
    k = 0
    while iter_date <= end_date:
        if iter_date.day == 1 and start_date < iter_date:
            count['Rango fin'] = iter_date - datetime.timedelta(1)
            for shift in shifts:
                count[shift] = (count[shift ] /k ) /shifts_per_day
            month_list.append(count)
            count = {'Rango inicio': iter_date}
            k = 0
            for shift in shifts:
                count[shift] = 0
        for j in range(shifts_per_day):
            for shift in shifts:
                count[shift] += get_value(
                    solution_dict, 'z[{},{}]'.format(( i *shifts_per_day ) + j +1 ,shift))
        iter_date += datetime.timedelta(days=1)
        i += 1
        k += 1
    count['Rango fin'] = iter_date - datetime.timedelta(1)
    for shift in shifts:
        count[shift] = (count[shift]/k)/shifts_per_day
    month_list.append(count)
    month_df = pd.DataFrame(month_list)

    # Weeks
    iter_date = start_date
    week_list = []
    count = {}
    for shift in shifts:
        count[shift] = 0
    for attribute in ["hx", "hc", "oferta", "ymenos", "ymas", "demanda"]:
        count[attribute] = 0
    count['Rango inicio'] = iter_date
    i = 0
    k = 0
    while iter_date <= end_date:
        if iter_date.weekday() == 0 and start_date < iter_date:
            count['Rango fin'] = iter_date - datetime.timedelta(1)
            for shift in shifts:
                count[shift] = (count[shift ] /k ) /shifts_per_day
            week_list.append(count)
            count = {'Rango inicio': iter_date}
            k = 0
            for shift in shifts:
                count[shift] = 0
            for attribute in ["hx", "hc", "oferta", "ymenos", "ymas", "demanda"]:
                count[attribute] = 0
        for j in range(shifts_per_day):
            for shift in shifts:
                count[shift] += get_value(
                    solution_dict, 'z[{},{}]'.format((i * shifts_per_day) + j + 1, shift))
                for attribute in ["hx", "hc", "oferta"]:
                    count[attribute] += get_value(
                        solution_dict, '{}[{},{}]'.format(
                            attribute, ( i *shifts_per_day) + j + 1, shift))
            count["ymenos"] += get_value(solution_dict,
                                         'ymenos[{}]'.format(( i *shifts_per_day) + j + 1))
            count["ymas"] += get_value(solution_dict,
                                         'ymas[{}]'.format(( i *shifts_per_day) + j + 1))
            count["demanda"] += demanda[( i *shifts_per_day) + j]
        iter_date += datetime.timedelta(days=1)
        i += 1
        k += 1
    count['Rango fin'] = iter_date - datetime.timedelta(1)
    week_list.append(count)
    for shift in shifts:
        count[shift] = (count[shift ] /k ) /shifts_per_day
    week_df = pd.DataFrame(week_list)

    # Periods
    iter_date = start_date
    period_list = []
    i = 0
    while iter_date <= end_date:
        for j in range(shifts_per_day):
            count = {'Periodo': j + 1, 'Fecha': iter_date}
            for attribute in ["hx", "hc", "oferta"]:
                count[attribute] = 0
            for shift in shifts:
                count[shift] = get_value(
                    solution_dict, 'z[{},{}]'.format((i * shifts_per_day) + j + 1, shift))
                for attribute in ["hx", "hc", "oferta"]:
                    count[attribute] += get_value(
                        solution_dict, '{}[{},{}]'.format(
                            attribute, (i * shifts_per_day) + j + 1, shift))
            count['ymenos'] = get_value(solution_dict,
                                        'ymenos[{}]'.format(( i *shifts_per_day) + j + 1))
            count['ymas'] = get_value(solution_dict,
                                        'ymas[{}]'.format(( i *shifts_per_day) + j + 1))
            count["demanda"] = demanda[(i *shifts_per_day) + j]
            period_list.append(count)
        iter_date += datetime.timedelta(days=1)
        i += 1
    period_df = pd.DataFrame(period_list)

    # Costos
    hx_cost = 0
    for t in periodos:
        for i in shiftshx:
            # hx_cost += (hx[t,i] - hc[t,i]) * salario[i]
            hx_cost += (get_value(solution_dict, "hx[{},{}]".format(t, i)) - get_value(
                solution_dict, "hc[{},{}]".format(t, i))) * salario[i]
    hx_cost = hx_cost * (24 / shifts_per_day) * sobrecargo / horasmensual
    payroll_cost = 0
    for t in G4Semini:
        for i in shifts:
            payroll_cost += get_value(solution_dict, "z[{},{}]".format(t, i)) * salario[i]
    new_hire_cost = 0
    for t in periodos:
        for i in shifts:
            # new_hire_cost += nuevoscontratos[t,i] * contrato[i] + nuevosdespidos[t,i] * despido[i]
            new_hire_cost += (get_value(
                solution_dict, "nuevoscontratos[{},{}]".format(t, i)) * contrato[i]) + \
                             (get_value(
                                 solution_dict, "nuevosdespidos[{},{}]".format(t, i)) * despido[i])
    understaffing_cost = 0
    for t in periodos:
        understaffing_cost += get_value(solution_dict, "ymenos[{}]".format(t))
    understaffing_cost = understaffing_cost * (24 / shifts_per_day) * cu
    total_cost = hx_cost + payroll_cost + new_hire_cost + understaffing_cost
    cost = [
        ('Costo en horas extra', hx_cost),
        ('Costo de nomina', payroll_cost),
        ('Costo de contratacion', new_hire_cost),
        ('Costo al no cubrir la demanda', understaffing_cost),
        ('Costo total del plan', total_cost)
    ]
    return month_df, week_df, period_df, cost


def get_parameters_dict(df, store):
    parameters = {}
    df = df.loc[df['Tienda'] == store]
    shift_columns = list(df.columns)
    shift_columns.remove('Tienda')
    shift_columns.remove('Parametro')
    shifts = []
    timerange_parameters_extended = []
    for timerange_parameter in timerange_parameters:
        for i in range(1,11):
            timerange_parameters_extended.append(timerange_parameter + '_' + str(i))
    for index, row in df.iterrows():
        if row['Parametro'] == 'Turnos':
            i = 1
            while i <= len(shift_columns):
                if row[i]:
                    shifts.append(row[i])
                else:
                    break
                i += 1
            parameters['Turnos'] = shifts
        elif row['Parametro'] in shift_parameters:
            aux_dict = {}
            for i in range(1, len(shifts) + 1):
                aux_dict[shifts[i - 1]] = row[i]
            parameters[row['Parametro']] = aux_dict
        elif row['Parametro'] in shift_boolean_parameters:
            aux_list = []
            for i in range(1, len(shifts) + 1):
                if row[i].lower() == 'si':
                    aux_list.append(shifts[i - 1])
            parameters[row['Parametro']] = aux_list
        elif row['Parametro'] in scalar_parameters:
            parameters[row['Parametro']] = float(row[1])
        elif row['Parametro'] in boolean_parameters:
            parameters[row['Parametro']] = row[1].lower() == 'si'
        elif row['Parametro'] in timerange_parameters_extended:
            parameters[row['Parametro']] = str(row[1])[:5]
    return parameters


def adjust_mix_parameters(parameters):
    for timerange_parameter in timerange_parameters:
        parameters[timerange_parameter] = []
        for i in range(1,11):
            key = timerange_parameter + '_' + str(i)
            if key in parameters:
                parameters[timerange_parameter].append(parameters[key])


def get_value(object, key):
    value = object.get(key)
    return value if value is not None else 0
