import pandas as pd
from sqlalchemy import create_engine
import traceback
import datetime as _dt

file_excel = 'report ITND fix(3).xlsx'

db_url = input('Paste External Database URL dari Render: ').strip()

INDO_MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mei': 5, 'jun': 6,
    'jul': 7, 'ags': 8, 'agu': 8, 'agt': 8, 'aug': 8, 'sep': 9,
    'okt': 10, 'oct': 10, 'nov': 11, 'des': 12, 'dec': 12,
}


def parse_date_id(val):
    """Parse tanggal yang formatnya bisa macem-macem: datetime asli dari Excel,
    string format umum, atau format Indonesia manual kayak '12-Des-2024'."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, pd.Timestamp):
        return val.date()
    if isinstance(val, _dt.datetime):
        return val.date()
    if isinstance(val, _dt.date):
        return val

    s = str(val).strip()
    if not s or s.lower() in ('nan', 'nat', '-'):
        return None

    try:
        return pd.to_datetime(s, dayfirst=True).date()
    except Exception:
        pass

    parts = s.replace('_', '-').replace('/', '-').replace(' ', '-').split('-')
    parts = [p for p in parts if p]
    if len(parts) == 3:
        try:
            day = int(parts[0])
            mon_str = parts[1].strip().lower()[:3]
            mon = INDO_MONTHS.get(mon_str)
            year = int(parts[2])
            if year < 100:
                year += 2000
            if mon:
                return _dt.date(year, mon, day)
        except Exception:
            pass

    print(f'  [!] Gak bisa parse tanggal: {s!r} -> diset kosong (NULL)')
    return None


# Kolom bertipe DATE di masing-masing tabel tujuan -- diparsing khusus
# biar gak crash kalau formatnya campur aduk (Excel date, text, dll)
DATE_COLUMNS_PER_TABLE = {
    'projects': {'tanggal_project_charter'},
    'orders': {'tanggal', 'akhir_kontrak', 'tgl_ba'},
    'dismantle_downgrade': {'tanggal', 'akhir_kontrak', 'tgl_ba'},
    'cases_connectivity': {'tanggal_charter', 'due_date_live'},
}

# Batas panjang kolom VARCHAR di database -- teks yang lebih panjang dari ini
# dipotong otomatis (daripada bikin insert gagal total).
VARCHAR_LIMITS = {
    'projects': {
        'project_id': 50, 'periode': 50, 'nama_project': 255, 'jenis_project': 100,
        'pmg': 100, 'pm': 100, 'segment_sales': 100, 'klasifikasi_project': 100,
        'nama_am': 100, 'target': 100, 'nama_pic': 100, 'status': 50,
        'order_type': 100, 'konfigurasi': 100, 'integrasi': 100, 'tshoot': 100,
    },
    'orders': {
        'periode': 50, 'order_type': 100, 'dasar_order': 255, 'no_surat_modin': 100,
        'jenis_order': 100, 'klasifikasi_order': 100, 'provider': 100,
        'sisa_kontrak': 50, 'no_order': 100, 'sid_1': 100, 'sid_2': 100,
        'ip_address': 100, 'status': 50, 'task': 100, 'no_ba': 100, 'file_ba': 255,
    },
    'dismantle_downgrade': {
        'periode': 50, 'project_or_non': 100, 'dasar_order': 255, 'no_surat_modin': 100,
        'jenis_order': 100, 'klasifikasi_order': 100, 'provider': 100,
        'sisa_kontrak': 50, 'no_order': 100, 'sid_1': 100, 'sid_2': 100,
        'ip_address': 100, 'status': 50, 'no_ba': 100, 'file_ba': 255,
    },
    'cases_connectivity': {
        'nama_project': 255, 'status': 50, 'status_nadine_itnd': 100, 'no_pr': 100,
        'connectivity': 100, 'opsi_connectivity_indibizz': 255,
    },
}


def truncate_value(table, col, val):
    limit = VARCHAR_LIMITS.get(table, {}).get(col)
    if limit and isinstance(val, str) and len(val) > limit:
        print(f'  [!] Kolom "{col}" kepanjangan ({len(val)} char), dipotong jadi {limit}: {val[:40]}...')
        return val[:limit]
    return val

# Rename kolom hasil normalisasi otomatis yang beda urutan/nama dari kolom
# yang sebenarnya ada di tabel database (biar gak mismatch pas insert).
COLUMN_RENAME = {
    'projects': {
        'id_project': 'project_id',
        'order': 'order_type',
    },
    'orders': {
        'order': 'dasar_order',
    },
    'dismantle_downgrade': {
        'project__non_project': 'project_or_non',
        'order': 'dasar_order',
    },
    'cases_connectivity': {},
}

print("Membaca dan merapikan seluruh data Excel ke database...")

try:
    engine = create_engine(db_url)
    xls = pd.ExcelFile(file_excel)

    def process_and_save(sheet_name, table_name):
        if sheet_name not in xls.sheet_names:
            print(f'-> Sheet "{sheet_name}" tidak ditemukan, dilewati.')
            return

        df = pd.read_excel(file_excel, sheet_name=sheet_name)
        df.columns = df.columns.str.strip()
        df = df.loc[:, ~df.columns.duplicated()]

        for col in list(df.columns):
            if col.strip().lower() == 'no':
                df = df.drop(columns=[col], errors='ignore')

        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(' ', '_', regex=False)
            .str.replace('-', '_', regex=False)
            .str.replace('/', '_', regex=False)
        )

        cols = pd.Series(df.columns)
        for dup in cols[cols.duplicated()].unique():
            cols[cols[cols == dup].index.values.tolist()] = [
                dup + '_' + str(i) if i != 0 else dup
                for i in range(sum(cols == dup))
            ]
        df.columns = cols

        # Rename kolom yang mismatch sama nama kolom di tabel database
        rename_map = COLUMN_RENAME.get(table_name, {})
        df = df.rename(columns=rename_map)

        # Buang kolom 'unnamed:...' (kolom kosong sisa formatting Excel)
        unnamed_cols = [c for c in df.columns if str(c).startswith('unnamed')]
        if unnamed_cols:
            print(f'  [i] Buang kolom kosong sisa Excel: {unnamed_cols}')
            df = df.drop(columns=unnamed_cols)

        # Kalau abis rename ada 2 kolom jadi namanya sama (bentrok), buang
        # yang belakangan -- biar gak bikin to_sql crash DuplicateColumnError
        dupe_cols = df.columns[df.columns.duplicated()].unique().tolist()
        if dupe_cols:
            print(f'  [!] Kolom bentrok setelah rename (dibuang yg belakangan): {dupe_cols}')
            df = df.loc[:, ~df.columns.duplicated()]

        # Parsing khusus buat kolom bertipe DATE (handle format campur aduk)
        for date_col in DATE_COLUMNS_PER_TABLE.get(table_name, set()):
            if date_col in df.columns:
                df[date_col] = df[date_col].apply(parse_date_id)

        # Potong teks yang kepanjangan biar gak error StringDataRightTruncation
        limits = VARCHAR_LIMITS.get(table_name, {})
        for col in df.columns:
            if col in limits:
                df[col] = df[col].apply(lambda v: truncate_value(table_name, col, v) if isinstance(v, str) else v)

        # Buang kolom yang gak dikenali tabel tujuan (biar gak error insert)
        # -- opsional: comment baris ini kalau mau lihat dulu kolom apa aja yang ada
        # df = df[[c for c in df.columns if c in KNOWN_COLUMNS.get(table_name, df.columns)]]

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

        # PENTING: 'append', BUKAN 'replace' -- biar tabel yang udah ada
        # (dengan kolom id SERIAL PRIMARY KEY dkk) gak ke-drop dan diganti.
        df.to_sql(table_name, engine, if_exists='append', index=False)
        print(
            f'-> Berhasil import sheet "{sheet_name}" ke tabel "{table_name}"'
            f' ({len(df)} baris).'
        )

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