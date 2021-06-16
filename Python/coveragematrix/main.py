import datetime, pandas as pd


class CoverageMatrix:
    def __init__(self, parameters, dataframes, site):
        self.coverage_units = parameters['coverage_units']
        self.transaction_units = parameters['transaction_units']
        self.merge_coverage_units = parameters['merge_coverage_units']
        self.merge_transaction_units = parameters['merge_transaction_units']
        self.iterations = parameters['iterations']
        self.driverhh = parameters['coverage_unit']
        self.driverpos = parameters['transaction_unit']
        self.start_date = datetime.datetime.strptime(parameters['start_date'], '%d/%m/%Y').strftime('%Y-%m-%d')
        self.end_date = datetime.datetime.strptime(parameters['end_date'], '%d/%m/%Y').strftime('%Y-%m-%d')

        self.dfmarcasplani = dataframes[0]
        self.df1 = dataframes[1]
        self.sucursal = site
        self.results = None

    def run(self):
        if self.merge_coverage_units:
            self.dfmarcasplani['Driver'] = self.dfmarcasplani['Driver'].isin(self.coverage_units)
            self.dfmarcasplani['Driver'] = self.dfmarcasplani['Driver'].replace(True, self.driverhh)

        if self.merge_transaction_units:
            self.df1['Driver'] = self.df1['Indicador'].isin(self.transaction_units)
            self.df1['Driver'] = self.df1['Driver'].replace(True, self.driverpos)
        else:
            self.df1['Driver'] = self.df1['Indicador']

        self.df1 = self.df1.groupby(['Fecha', 'Sucursal', 'Driver'], as_index=False).sum()

        df2 = pd.concat([self.df1, self.dfmarcasplani], ignore_index=True, sort=True)

        df2.groupby('Sucursal').mean()
        df2.groupby(['Sucursal', 'Fecha', 'Driver'])


        df = df2[df2['Driver'].isin([self.driverhh, self.driverpos])][df2['Sucursal'] == self.sucursal].drop(
            ['Sucursal'], axis=1)
        df['Fecha'] = df['Fecha'].astype('datetime64[ns]')
        df=df[(df['Fecha'] > self.start_date) & (df['Fecha'] < self.end_date)]
        df_aux = df.copy()
        df = df[df['Fecha'].duplicated(keep=False)]
        # df = pd.melt(df, id_vars=['Fecha', 'Driver'], value_vars=df.iloc[:,0:96].columns)

        l = []
        promedios = []
        intervalos = df.columns
        intervalos = intervalos[intervalos!='Driver']
        intervalos = intervalos[intervalos!='Fecha']
        for j in range(self.iterations):
            df[j] = 0
            for fecha in df['Fecha'].unique():
                for intervalo in intervalos:
                    if df.loc[(df['Fecha'] == fecha) & (df['Driver'] == self.driverpos), intervalo].iloc[0] == j:
                        l.append(str(intervalo))
                df.loc[(df['Fecha'] == fecha), j] = \
                df.loc[(df['Fecha'] == fecha) & (df['Driver'] == self.driverhh)].filter(l).mean(
                    axis=1).iloc[0]
                l = []
            promedios.append(df[j].mean())

        self.results = promedios
