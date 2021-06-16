import pandas as pd
from main import CoverageMatrix


dftest = pd.read_csv("/home/fernando/scm/suite/matrix/CoberturaLiberty.csv", sep=';')
df1 = pd.read_excel("/home/fernando/scm/suite/matrix/Cobertura_Farmashop_1.xlsx", converters={'Sucursal':str})
dftest2 = pd.read_csv("/home/fernando/scm/suite/matrix/DriversLiberty.csv", sep=';')
df2 = pd.read_excel("/home/fernando/scm/suite/matrix/TransaccionesFarmashop1.xlsx", converters={'Sucursal':str})
df1.columns = df1.columns.astype(str)
df2.columns = df2.columns.astype(str)

parameters = {
    'coverage_units': ['Planificado'],
    'transaction_units': ['EFECTIVO', 'TARJETA', 'CHEQUE'],
    'merge_coverage_units': False,
    'merge_transaction_units': False,
    'iterations': 50,
    'coverage_unit': 'Planificado',
    'transaction_unit': 'Combinacion',
    'start_date': '01/01/2019',
    'end_date': '01/03/2019'
}

matrix_instance = CoverageMatrix(parameters, [df1, df2], '1')
matrix_instance.run()
results = matrix_instance.results
print(results)
