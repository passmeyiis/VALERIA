import pandas as pd
from sqlalchemy import create_engine
import traceback

db_user = 'postgres'
db_password = 'postgres'  # Sesuaikan dengan password postgres kamu (biasanya kosong atau postgres)
db_host = 'localhost'
db_port = '5432'
db_name = 'valeria_db'

file_excel = 'report ITND fix(3).xlsx'

print("Membaca dan merapikan seluruh data Excel ke database...")

try:
  engine = create_engine(
      f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
  )
  xls = pd.ExcelFile(file_excel)


  def process_and_save(sheet_name, table_name):
    if sheet_name not in xls.sheet_names:
      print(f'-> Sheet "{sheet_name}" tidak ditemukan, dilewati.')
      return

    df = pd.read_excel(file_excel, sheet_name=sheet_name)
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()]

    # Hapus kolom 'no' jika ada
    for col in list(df.columns):
      if col.strip().lower() == 'no':
        df = df.drop(columns=[col], errors='ignore')

    # Normalisasi nama kolom (snake_case)
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(' ', '_', regex=False)
        .str.replace('-', '_', regex=False)
        .str.replace('/', '_', regex=False)
    )

    # Buat nama kolom unik jika ada duplikat
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
      cols[cols[cols == dup].index.values.tolist()] = [
          dup + '_' + str(i) if i != 0 else dup
          for i in range(sum(cols == dup))
      ]
    df.columns = cols

    # Pembersihan otomatis untuk kolom angka/revenue/harga
    for col in df.columns:
      if any(
          keyword in col
          for keyword in ['revenue', 'harga', 'nilai', 'amount', 'total']
      ):
        df[col] = (
            pd.to_numeric(
                df[col]
                .astype(str)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False)
                .str.replace('Rp', '', regex=False)
                .str.strip(),
                errors='coerce',
            )
            .fillna(0)
            .astype(float)
        )

    # Simpan ke database
    df.to_sql(table_name, engine, if_exists='replace', index=False)
    print(
        f'-> Berhasil import sheet "{sheet_name}" ke tabel "{table_name}"'
        f' ({len(df)} baris).'
    )


  # Jalankan untuk semua tabel utama
  process_and_sheet_mappings = [
      ('List Project', 'projects'),
      ('List Order', 'orders'),
      ('Dis Dow Jan - Apr', 'dismantle_downgrade'),
      ('Case 1500 & Connectivity', 'cases_connectivity'),
  ]

  for sheet, table in process_and_sheet_mappings:
    process_and_save(sheet, table)

  print(
      '\nSelesai! Seluruh data finansial dan project kini sudah berformat angka'
      ' bersih.'
  )

except Exception as e:
  print('\n[!] Terjadi error saat import:')
  traceback.print_exc()