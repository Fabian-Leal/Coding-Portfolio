from mix import OptimalMix
from tkinter import filedialog
import csv
import datetime
import pandas as pd
import tkinter
import tkinter.messagebox
#import tkinter.filedialog


parameters = {
    'Turnos': ['fulltime', 'parttime'],
    'salario': {"fulltime": 1488, "parttime": 652},
    'largosem': {"fulltime": 48, "parttime": 20},
    'largomen': {"fulltime": 192, "parttime": 80},
    'cotainf': {"fulltime": 6.4, "parttime": 4},
    'cotasup': {"fulltime": 8, "parttime": 4},
    'diaslabmin': {"fulltime": 6, "parttime": 4},
    'diaslabmax': {"fulltime": 6, "parttime": 4},
    'zcero': {"fulltime": 12, "parttime": 0},
    'productividad': {"fulltime": 0.85, "parttime": 0.85},
    'ausentismo': {"fulltime": 1, "parttime": 1},
    'rotacion': {"fulltime": 1, "parttime": 1},
    'contrato': {"fulltime": 432, "parttime": 432},
    'despido': {"fulltime": 232, "parttime": 232},
    'ppto': 99999999999999,
    'sobrecargo': 1.35,
    'cu': 117,
    'co': 0,
    'slmin': 0.95,
    'constraint_extra_hours': True,
    'constraint_min_operation': True,
    'constraint_max_operation': True,
    'constraint_proportional': True,
    'start_date': '01/01/2020',
    'end_date': '31/12/2020',
    'sheet_start_date': '01/01/2020',
    'sheet_end_date': '31/12/2020',
}

mix = OptimalMix(parameters)


def getCSV():
    csv_file_path = filedialog.askopenfilename()
    v.set(csv_file_path)
    df = pd.read_csv(csv_file_path, delimiter=';')
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    mix.load_demand(df)


def EjecutarMix():
    mix.load_constrains()
    mix.run_mix()


def verResultados():
    window = tkinter.Toplevel(root)
    window.geometry("300x150")
    tkinter.Label(window, text="Variable, Valor").grid(row=0,column=1)
    varInfo = mix.get_solution()
    for i in range(len(varInfo)):
        tkinter.Label(window, text=varInfo[i]).grid(row=i+1,column=1)


def exportCSV():
    varInfo = mix.get_solution()
    with open('Dotación Óptima', 'w') as myfile:
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        wr.writerows(varInfo)


root = tkinter.Tk()
root.geometry("320x200")
tkinter.Label(root, text='File Path').grid(row=0, column=0)
v = tkinter.StringVar()
entry = tkinter.Entry(root, textvariable=v).grid(row=0, column=1)
tkinter.Button(root, text='Importar Demanda',command=getCSV).grid(row=1, column=1)
tkinter.Button(root, text="Ejecutar Mix", command=EjecutarMix).grid(row=2,column=1)
tkinter.Button(root, text="Ver Resultados", command=verResultados).grid(row=3, column=1)
tkinter.Button(text='Exportar CSV', command=exportCSV).grid(row=4, column=1)
#tkinter.Checkbutton(root, text='Incluir límite mínimo de operación', command=LimOperacionMin).grid(row=5, column=1)
#tkinter.Checkbutton(root, text='Incluir límite máximo de operación', command=LimOperacionMax).grid(row=6, column=1)
#tkinter.Checkbutton(root, text='Incluir proporción entre FT y PT', command=ProporcionFtPt).grid(row=7, column=1)

root.mainloop()
