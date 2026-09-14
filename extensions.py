from flask_sqlalchemy import SQLAlchemy

# Instance tunggal SQLAlchemy dipakai bersama oleh app.py dan semua models/routes,
# supaya tidak ada circular import antara app.py <-> models <-> routes.
db = SQLAlchemy()
