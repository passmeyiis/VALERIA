from functools import wraps

from flask import redirect, session, url_for


def login_required(view):
    """Pastikan user sudah login (ada session) sebelum akses route."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'role' not in session:
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    """Pastikan user sudah login DAN role-nya admin atau superadmin.

    Keduanya diperlakukan setara (akses & menu identik) — dipisah cuma di
    level akun/login supaya audit log bisa bedain siapa yang bertindak.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get('role') not in ('admin', 'superadmin'):
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)

    return wrapped
