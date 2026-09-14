from flask import Blueprint, redirect, render_template, request, session, url_for

from extensions import db
from models import AuditLog, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if 'role' in session:
        return redirect(url_for('auth.profil_akun'))
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

            # Mengarahkan langsung ke halaman profil akun yang aman dari error tabel lain
            return redirect(url_for('auth.profil_akun'))

    return render_template('auth/login.html', error=error)


@auth_bp.route('/profil-akun')
def profil_akun():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # Ambil data murni dari tabel users
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
        
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
        <h2 style="color: #2c3e50;">Selamat Datang, {user.name}! 🚀</h2>
        <p><b>Username:</b> {user.username}</p>
        <p><b>Role Akses:</b> {user.role}</p>
        <p><b>Akun Dibuat:</b> {user.created_at}</p>
        <hr style="margin: 20px 0;">
        <p style="color: #666; font-size: 14px;">Akun lu berhasil terautentikasi dari database tabel <code>users</code> tanpa gangguan tabel lain.</p>
        <a href="{url_for('auth.logout')}" style="display: inline-block; padding: 10px 15px; background: #e74c3c; color: white; text-decoration: none; border-radius: 5px;">Logout</a>
    </div>
    """


@auth_bp.route('/logout')
def logout():
    username = session.get('username')
    if username:
        AuditLog.record(actor=username, action='Logout')
    session.clear()
    return redirect(url_for('auth.login'))