"""
Script SEKALI JALAN buat mindahin data agregat lama dari Excel
(sheet 'Sum {tahun}') ke tabel monthly_revenue_history &
yearly_summary_history di database Postgres.

Cara pakai:
  1. Pastiin file Excel 'report ITND fix(3).xlsx' ada di folder yang sama
     dengan script ini (atau ubah EXCEL_PATH di bawah).
  2. pip install pandas openpyxl psycopg2-binary --break-system-packages
     (kalau belum ada)
  3. Jalanin: python import_history.py
  4. Pas diminta, paste "External Database URL" dari dashboard Render
     (database -> tab Connect -> External -> External Database URL)
"""

import pandas as pd
import psycopg2

EXCEL_PATH = 'report ITND fix(3).xlsx'


def find_revenue_row(df):
    """Cari baris & posisi kolom label 'Revenue Project' di sheet."""
    for idx, row in df.iterrows():
        for col_idx, cell in enumerate(row):
            if isinstance(cell, str) and 'Revenue Project' in cell:
                return row, col_idx
    return None, None


def main():
    db_url = input('Paste External Database URL dari Render: ').strip()

    print(f'\nMembaca daftar sheet dari "{EXCEL_PATH}"...')
    xl = pd.ExcelFile(EXCEL_PATH)
    year_sheets = [s for s in xl.sheet_names if s.strip().startswith('Sum ')]

    if not year_sheets:
        print('Gak ketemu sheet yang namanya diawali "Sum " (contoh: "Sum 2024"). Berhenti.')
        return

    print(f'Sheet yang ketemu: {year_sheets}\n')

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    print('Bikin tabel kalau belum ada...')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS yearly_summary_history (
            tahun INT PRIMARY KEY,
            total_project INT DEFAULT 0,
            total_revenue NUMERIC(18, 2) DEFAULT 0
        );
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS monthly_revenue_history (
            id SERIAL PRIMARY KEY,
            tahun INT NOT NULL,
            bulan INT NOT NULL,
            revenue NUMERIC(18, 2) NOT NULL DEFAULT 0,
            UNIQUE(tahun, bulan)
        );
    ''')
    conn.commit()

    for sheet_name in year_sheets:
        try:
            tahun = int(''.join(ch for ch in sheet_name if ch.isdigit()))
        except ValueError:
            print(f'Gak bisa nebak tahun dari nama sheet "{sheet_name}", skip.')
            continue

        print(f'--- Memproses sheet "{sheet_name}" (tahun {tahun}) ---')
        df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name, header=None)

        target_row, label_col_idx = find_revenue_row(df)
        if target_row is None:
            print(f'  "Revenue Project" gak ketemu di sheet ini, skip.')
            continue

        monthly_revenues = []
        for i in range(12):
            col = label_col_idx + 1 + i
            val = target_row.iloc[col] if col < len(target_row) else None
            try:
                revenue = float(val) if pd.notna(val) else 0
            except (TypeError, ValueError):
                revenue = 0
            monthly_revenues.append(revenue)

        for i, revenue in enumerate(monthly_revenues):
            bulan = i + 1
            cur.execute('''
                INSERT INTO monthly_revenue_history (tahun, bulan, revenue)
                VALUES (%s, %s, %s)
                ON CONFLICT (tahun, bulan) DO UPDATE SET revenue = EXCLUDED.revenue
            ''', (tahun, bulan, revenue))

        total_project_val = 0
        total_revenue_val = sum(monthly_revenues)
        if len(df) > 1 and pd.notna(df.iloc[1, 3]):
            try:
                total_project_val = int(df.iloc[1, 3])
            except (TypeError, ValueError):
                pass
        if len(df) > 3 and pd.notna(df.iloc[3, 3]):
            try:
                total_revenue_val = float(df.iloc[3, 3])
            except (TypeError, ValueError):
                pass

        cur.execute('''
            INSERT INTO yearly_summary_history (tahun, total_project, total_revenue)
            VALUES (%s, %s, %s)
            ON CONFLICT (tahun) DO UPDATE SET
                total_project = EXCLUDED.total_project,
                total_revenue = EXCLUDED.total_revenue
        ''', (tahun, total_project_val, total_revenue_val))

        conn.commit()
        print(f'  Berhasil: revenue bulanan {monthly_revenues}')
        print(f'  Total project: {total_project_val}, Total revenue: {total_revenue_val}\n')

    cur.close()
    conn.close()
    print('Selesai! Semua sheet udah diimport ke database.')


if __name__ == '__main__':
    main()
