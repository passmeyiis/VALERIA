from flask import Blueprint, render_template

from routes.decorators import login_required

klien_bp = Blueprint('klien', __name__)


@klien_bp.route('/dashboard/klien')
@login_required
def dashboard_klien():
    return render_template('klien/dashboard_klien.html', active_page='dashboard_klien')
