import pandas as pd

file_excel = 'report ITND fix(3).xlsx'
xls = pd.ExcelFile(file_excel)
print("Daftar Sheet di Excel:", xls.sheet_names)