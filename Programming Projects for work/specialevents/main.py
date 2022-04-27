from pandas.tseries.offsets import DateOffset
import datetime
import numpy as np
import pandas as pd
import dateutil.relativedelta as re


class SpecialEvents:
    def __init__(self, parameters, dataframe, driver):
        # Parameters
        self.days_min = parameters['days_min']
        self.days_max = parameters['days_max']
        self.days_step = parameters['days_step']
        self.sensitivity_min = parameters['sensitivity_min']
        self.sensitivity_max = parameters['sensitivity_max']
        self.sensitivity_step = parameters['sensitivity_step']
        self.start_date = pd.Timestamp(datetime.datetime.strptime(parameters['start_date'], '%d/%m/%Y'))
        self.end_date = pd.Timestamp(datetime.datetime.strptime(parameters['end_date'], '%d/%m/%Y'))

        # Others
        self.dataframe = dataframe
        self.dataframe['FECHA'] = pd.to_datetime(self.dataframe['FECHA'], format='%d/%m/%Y')
        self.driver = driver
        self.events = pd.DataFrame(columns=('DAY', 'COUNT', 'WEEKS', 'Z'))
        self.results = {}

    def run(self):
        #writer = pd.ExcelWriter(self.path, engine='xlsxwriter')
        sensitivity_iter = self.sensitivity_min

        while sensitivity_iter <= self.sensitivity_max:
            days_iter = self.days_min
            while days_iter <= self.days_max:
                print("----------Sample Size " + str(days_iter) + " Anomaly Score value " + str(
                    sensitivity_iter) + "----------")
                aux_date = self.end_date
                anomaly = pd.DataFrame(columns=('DAY', 'SCORE'))
                while aux_date >= (self.start_date + re.relativedelta(weeks=days_iter)):
                    i = 0
                    list_amount = list()
                    list_date = list()
                    while i < days_iter:
                        series = self.dataframe[self.dataframe['FECHA'] == aux_date - re.relativedelta(weeks=i)]
                        if len(series) > 0:
                            list_amount.append(series.iloc[0]['VALOR'])
                            list_date.append(series.iloc[0]['FECHA'])
                        i += 1
                    #median_points = np.median(list_amount)
                    list_distance = (abs(list_amount - np.median(list_amount)))
                    median_distance = np.median(list_distance)
                    list_score = (list_distance / median_distance)

                    t = 0
                    while t < len(list_score):
                        if list_score[t] >= sensitivity_iter:
                            anomaly.loc[len(anomaly)] = [list_date[t], list_amount[t]]
                        t += 1
                    aux_date = aux_date - re.relativedelta(days=1)
                self.results[str(days_iter) + "-" + str(sensitivity_iter)] = anomaly['DAY'].value_counts()
                #anomaly['DAY'].value_counts().to_excel(writer, str(days_iter) + "-" + str(sensitivity_iter))
                aux = anomaly['DAY'].value_counts().rename_axis('DAY').reset_index(name='COUNT')
                for j in range(0, len(aux)):
                    if aux['COUNT'][j] == days_iter:
                        self.events.loc[len(self.events)] = [aux['DAY'][j], aux['COUNT'][j], days_iter, sensitivity_iter]
                days_iter += self.days_step
            sensitivity_iter += self.sensitivity_step
        #self.events.to_excel(writer, "SUMMARY", index=True, header=True)
        #self.events['DAY'].value_counts().to_excel(writer, "SUMMARY 2", index=True, header=True)
        #writer.save()
        #writer.close()
        combinations = len(self.results.keys())
        self.results['Detalle'] = self.events
        #self.results['SUMMARY 2'] = self.events['DAY'].value_counts()
        counts = self.events['DAY'].value_counts()
        iter_date = self.start_date
        summary = []
        while iter_date <= self.end_date:
            row = {
                'Dia': iter_date,
                'Cantidad': counts[iter_date] if iter_date in counts.index else 0,
            }
            row['Porcentaje'] = row['Cantidad']/combinations
            summary.append(row)
            iter_date = iter_date + DateOffset(days=1)
        self.results['Resumen'] = pd.DataFrame(summary).sort_values(['Cantidad', 'Dia'], ascending=[False, True])
