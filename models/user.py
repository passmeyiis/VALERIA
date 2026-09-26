from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(db.Model):
    """Akun pengguna sistem Valeria.

    role ada tiga nilai: 'admin', 'superadmin' (dua-duanya punya akses & menu
    yang identik — sengaja dibikin dua akun/login terpisah supaya audit log
    bisa bedain siapa yang benar-benar melakukan tindakan), dan 'klien'
    (akses terbatas: monitoring, IP info, scheduler).
    """

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)  # <-- Kolom email ditambahkan di sini
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='klien')  # 'admin' | 'superadmin' | 'klien'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self) -> str:
        return f'<User {self.username} ({self.role})>'