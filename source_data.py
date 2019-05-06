# https://openpyxl.readthedocs.io

from openpyxl import load_workbook
from collections import namedtuple


def get_data(filename):
    wb = load_workbook(filename=filename)
    raw_data = []

    for row in wb['Form1']:
        r = [str(x.value) for x in row]
        raw_data.append(r)

    headers = list(map(lambda x: x.replace(" ", ""), raw_data[0]))
    row = namedtuple('row', headers)

    return [row(*x) for x in raw_data[1:]]


def write_data():
    pass
    filename = 'x'


if __name__ == '__main__':
    data_file_name = 'Blueprint Course Management 1 (14).xlsx'
    print(get_data(data_file_name))
