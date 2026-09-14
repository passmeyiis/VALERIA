"""
Script sekali-pakai buat reset tabel audit_logs kalau strukturnya ketinggalan
zaman dibanding model (error 'column audit_logs.xxx does not exist').

Script ini pakai koneksi database YANG SAMA PERSIS dengan yang dipakai
app.py (baca dari .env yang sama), jadi dijamin nggak salah drop di
database yang salah.

Cara pakai:
    python reset_audit_logs.py
"""

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from app import app
from extensions import db
from models import AuditLog

with app.app_context():
    print(f"Terhubung ke: {app.config['SQLALCHEMY_DATABASE_URI']}")

    inspector = db.inspect(db.engine)
    if 'audit_logs' in inspector.get_table_names():
        print("Menghapus tabel audit_logs yang lama...")
        AuditLog.__table__.drop(db.engine)
    else:
        print("Tabel audit_logs belum ada, lanjut bikin baru.")

    print("Membuat ulang tabel audit_logs sesuai model terbaru...")
    db.create_all()

    print("Selesai! Tabel audit_logs sekarang sudah sesuai model (ref_no, category, reason, dst).")
