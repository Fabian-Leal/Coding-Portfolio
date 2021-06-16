import pandas as pd
from main import CoverageMatrix


dftest = pd.read_csv("/home/fernando/scm/suite/matrix/CoberturaLiberty.csv", sep=';')
df1 = pd.read_excel("/home/fernando/scm/suite/matrix/CoberturaLiberty1.xlsx")
dftest2 = pd.read_csv("/home/fernando/scm/suite/matrix/DriversLiberty.csv", sep=';')
df2 = pd.read_excel("/home/fernando/scm/suite/matrix/DriversLiberty1.xlsx")

parameters = {
    'coverage_units': ['Cobertura'],
    'transaction_units': ['Trafico'],
    'merge_coverage_units': False,
    'merge_transaction_units': False,
    'coverage_unit': 'Cobertura',
    'transaction_unit': 'Trafico',
    'start_date': '01/10/2020',
    'end_date': '31/12/2020'
}

matrix_instance = CoverageMatrix(parameters, [dftest, dftest2], 'AGUADILLA MALL STORE')
matrix_instance.run()
results = matrix_instance.results
print(results)
