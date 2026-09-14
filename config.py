import os


class Config:
    """Konfigurasi utama aplikasi Valeria.

    Semua nilai sensitif (secret key, kredensial PRTG, koneksi database)
    diambil dari environment variable. Jangan hardcode credential di sini.
    Contoh isi file .env ada di .env.example.
    """

    # --- Flask ---
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-change-this-in-production')

    # --- Database (PostgreSQL) ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/valeria_db',
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Integrasi PRTG ---
    PRTG_BASE_URL = os.environ.get('PRTG_BASE_URL', 'http://127.0.0.1')
    PRTG_USERNAME = os.environ.get('PRTG_USERNAME', 'prtgadmin')
    PRTG_PASSHASH = os.environ.get('PRTG_PASSHASH', '4235005056')
    PRTG_DEFAULT_GRAPH_ID = os.environ.get('PRTG_DEFAULT_GRAPH_ID', '2082')

    # --- Sumber data IP Address ---
    IP_EXCEL_PATH = os.environ.get('IP_EXCEL_PATH', 'IP_address_INfomedia.xlsx')
    # Baris ke berapa (index dari 0) yang berisi header kolom asli di file Excel.
    IP_EXCEL_HEADER_ROW = int(os.environ.get('IP_EXCEL_HEADER_ROW', 6))

    # --- Akun default yang di-seed saat pertama kali dijalankan (dev only) ---
    SEED_ADMIN_USERNAME = os.environ.get('SEED_ADMIN_USERNAME', 'admin')
    SEED_ADMIN_PASSWORD = os.environ.get('SEED_ADMIN_PASSWORD', 'admin123')
    SEED_SUPERADMIN_USERNAME = os.environ.get('SEED_SUPERADMIN_USERNAME', 'superadmin')
    SEED_SUPERADMIN_PASSWORD = os.environ.get('SEED_SUPERADMIN_PASSWORD', 'super123')
    SEED_KLIEN_USERNAME = os.environ.get('SEED_KLIEN_USERNAME', 'klien')
    SEED_KLIEN_PASSWORD = os.environ.get('SEED_KLIEN_PASSWORD', 'klien123')
