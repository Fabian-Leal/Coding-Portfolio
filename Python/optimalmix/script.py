from mix import OptimalMix
#from tkinter import filedialog
import csv
import datetime
import pandas as pd
#import tkinter
#import tkinter.messagebox
#import tkinter.filedialog

from utils import get_parameters_dict, adjust_mix_parameters

df1 = pd.read_excel('/home/fernando/scm/suite/mix/test1/Parámetros_nuevos_JP_EN2LPRB.xlsx')
parameters = get_parameters_dict(df1, 'General')
adjust_mix_parameters(parameters)
parameters['start_date'] = '08/07/2019'
parameters['end_date'] = '30/06/2020'
parameters['sheet_start_date'] = '08/07/2019'
parameters['sheet_end_date'] = '30/06/2020'
parameters['time_shifts'] = 12


mix = OptimalMix(parameters)
df = pd.read_excel('/home/fernando/scm/suite/mix/test1/DEMANDA_JAVIER_PRADO_gB4vrkr.xlsx')
mix.load_demand(df)
mix.load_constrains()
mix.run_mix()

