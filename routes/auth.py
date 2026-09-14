from flask import Blueprint, redirect, render_template, request, session, url_for

from extensions import db
from models import AuditLog, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if 'role' in session:
        if session['role'] == 'admin':
            return redirect(url_for('admin.dashboard_admin'))
        if session['role'] == 'superadmin':
            return redirect(url_for('admin.sup_admin'))
        return redirect(url_for('klien.dashboard_klien'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            error = 'Username atau password yang kamu masukkan salah.'
        else:
            session['user_id'] = user.id
            session['username'] = user.username
            session['name'] = user.name
            session['role'] = user.role

            AuditLog.record(actor=user.username, action='Login', detail=f'role: {user.role}')

            if user.role == 'admin':
                return redirect(url_for('admin.dashboard_admin'))
            if user.role == 'superadmin':
                return redirect(url_for('admin.sup_admin'))
            return redirect(url_for('klien.dashboard_klien'))

    return render_template('auth/login.html', error=error)


@auth_bp.route('/logout')
def logout():
    username = session.get('username')
    if username:
        AuditLog.record(actor=username, action='Logout')
    session.clear()
    return redirect(url_for('auth.login'))