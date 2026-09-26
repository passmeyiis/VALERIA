import random
import string
from flask import Blueprint, redirect, render_template, request, session, url_for, flash

from extensions import db
from models import AuditLog, User

auth_bp = Blueprint('auth', __name__)

# Temporary storage untuk kode verifikasi lupa password
reset_tokens = {}


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


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        # Cari user berdasarkan email di database
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('Email tersebut tidak terdaftar di sistem.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        # Generate kode referal / verifikasi unik (contoh: VAL-XXXXXX)
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Simpan ke session sementara
        session['reset_email'] = email
        session['reset_code'] = code
        
        # Simulasi pengiriman kode (bisa dicek di terminal Flask)
        print(f"\n[KODE REFERRAL RESET] Untuk email '{email}' adalah: VAL-{code}\n")
        
        return redirect(url_for('auth.reset_password'))
        
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    # Pastikan user sudah melewati tahap input email
    if 'reset_email' not in session or 'reset_code' not in session:
        flash('Silakan masukkan email terlebih dahulu.', 'danger')
        return redirect(url_for('auth.forgot_password'))
        
    target_email = session['reset_email']
    actual_code = session['reset_code']
    
    if request.method == 'POST':
        token = request.form.get('token', '').strip().upper()
        new_password = request.form.get('new_password', '')
        
        # Validasi kode verifikasi
        if token == f"VAL-{actual_code}" or token == actual_code:
            user = User.query.filter_by(email=target_email).first()
            
            if user:
                # Update password baru pakai method model User
                user.set_password(new_password)
                db.session.commit()
                
                # Bersihkan session reset
                session.pop('reset_email', None)
                session.pop('reset_code', None)
                
                flash('Password berhasil diubah! Silakan login dengan password baru.', 'success')
                return redirect(url_for('auth.login'))
        
        flash('Kode verifikasi salah atau sudah kedaluwarsa.', 'danger')
        
    # Kirim kode display ke template agar user bisa melihat langsung kodenya (sebagai simulasi referral/email)
    return render_template('auth/reset_password.html', display_code=f"VAL-{actual_code}", email=target_email)


@auth_bp.route('/logout')
def logout():
    username = session.get('username')
    if username:
        AuditLog.record(actor=username, action='Logout')
    session.clear()
    return redirect(url_for('auth.login'))