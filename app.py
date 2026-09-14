from flask import Flask

from config import Config
from extensions import db

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def seed_default_users(app: Flask) -> None:
    """Buat akun admin/superadmin/klien default kalau tabel users masih kosong (dev only)."""
    from models import User

    if User.query.count() > 0:
        return

    admin = User(username=app.config['SEED_ADMIN_USERNAME'], name='Administrator', role='admin')
    admin.set_password(app.config['SEED_ADMIN_PASSWORD'])

    superadmin = User(username=app.config['SEED_SUPERADMIN_USERNAME'], name='Super Administrator', role='superadmin')
    superadmin.set_password(app.config['SEED_SUPERADMIN_PASSWORD'])

    klien = User(username=app.config['SEED_KLIEN_USERNAME'], name='Klien Demo', role='klien')
    klien.set_password(app.config['SEED_KLIEN_PASSWORD'])

    db.session.add_all([admin, superadmin, klien])
    db.session.commit()

    print('=' * 56)
    print('  Akun default berhasil dibuat (GANTI PASSWORD INI!)')
    print(f"  admin      : {app.config['SEED_ADMIN_USERNAME']} / {app.config['SEED_ADMIN_PASSWORD']}")
    print(f"  superadmin : {app.config['SEED_SUPERADMIN_USERNAME']} / {app.config['SEED_SUPERADMIN_PASSWORD']}")
    print(f"  klien      : {app.config['SEED_KLIEN_USERNAME']} / {app.config['SEED_KLIEN_PASSWORD']}")
    print('=' * 56)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Import model supaya terdaftar ke SQLAlchemy metadata sebelum create_all()
    import models  # noqa: F401

    from routes.admin import admin_bp
    from routes.auth import auth_bp
    from routes.klien import klien_bp
    from routes.shared import shared_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(klien_bp)
    app.register_blueprint(shared_bp)

    with app.app_context():
        db.create_all()

        from db_maintenance import auto_migrate_columns
        auto_migrate_columns(app)

        seed_default_users(app)

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
