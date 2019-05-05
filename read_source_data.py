# https://openpyxl.readthedocs.io

import __init__
from __init__ import here
from pathlib import Path
from openpyxl import load_workbook

datafile = Path(here) / 'raw_data' / 'Blueprint Course Management 1 (14).xlsx'

wb = load_workbook(filename=datafile)

for row in wb['Form1']:
    values = list(map(lambda x: x.value, row))
    print(values)
