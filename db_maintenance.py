"""
Auto-migrate ringan buat development.

Kalau model Python (models/*.py) sudah diubah (nambah kolom baru) tapi tabel
di database masih pakai struktur lama, error yang muncul biasanya:
    psycopg2.errors.UndefinedColumn: column xxx.yyy does not exist

db.create_all() dari SQLAlchemy TIDAK menangani ini — dia cuma bikin tabel
yang belum ada sama sekali, dan tidak pernah mengubah tabel yang sudah ada.

Fungsi di file ini menutup celah itu: setiap kali app.py start, untuk setiap
model yang terdaftar, dibandingkan kolom di model vs kolom yang benar-benar
ada di tabel database. Kolom yang belum ada otomatis ditambahkan lewat
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, tanpa menghapus data yang sudah ada.

Ini bukan pengganti tools migrasi seperti Alembic untuk production, tapi cukup
buat mencegah error 'column does not exist' berulang selama development.
"""

from sqlalchemy import inspect, text

from extensions import db


def auto_migrate_columns(app) -> None:
    from models import AuditLog, IPAddress, IPDeviceEntry, Schedule, User

    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())

        for model in (User, Schedule, AuditLog, IPAddress, IPDeviceEntry):
            table_name = model.__tablename__

            if table_name not in existing_tables:
                # Tabel belum ada sama sekali -> biar db.create_all() yang bikin,
                # tidak perlu ditangani di sini.
                continue

            existing_columns = {col['name'] for col in inspector.get_columns(table_name)}

            for column in model.__table__.columns:
                if column.name in existing_columns:
                    continue

                col_type = column.type.compile(dialect=db.engine.dialect)
                sql = f'ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column.name} {col_type}'

                try:
                    with db.engine.begin() as conn:
                        conn.execute(text(sql))
                    print(f'[auto-migrate] Kolom baru ditambahkan: {table_name}.{column.name}')
                except Exception as exc:  # noqa: BLE001
                    print(f'[auto-migrate] GAGAL menambahkan {table_name}.{column.name}: {exc}')
