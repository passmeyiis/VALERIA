import os
from datetime import datetime

import pandas as pd
import requests
from flask import Blueprint, Response, current_app, flash, jsonify, redirect, render_template, request, session, url_for

from extensions import db
from models import AuditLog, IPAddress, Schedule
from routes.decorators import admin_required, login_required

# Deklarasi blueprint ditaruh di sini sebelum digunakan oleh decorator route
shared_bp = Blueprint('shared', __name__)


# --- IP Management ---

def _resolve_excel_path():
    excel_path = current_app.config['IP_EXCEL_PATH']
    # Selalu resolve ke path absolut relatif terhadap root project (app.py),
    # supaya file tetap ketemu walau app dijalankan dari working directory lain.
    if not os.path.isabs(excel_path):
        excel_path = os.path.join(current_app.root_path, excel_path)
    return excel_path


@shared_bp.route('/ip-management')
@login_required
def ip_management():
    excel_path = _resolve_excel_path()
    header_row = current_app.config['IP_EXCEL_HEADER_ROW']
    ip_error = None

    # Cek apakah database IPAddress masih kosong, kalau kosong kita coba import dari Excel
    if IPAddress.query.count() == 0:
        try:
            raw_df = pd.read_excel(excel_path, sheet_name=0, header=header_row)
            raw_df = raw_df.dropna(axis=1, how='all').dropna(axis=0, how='all')
            for _, row in raw_df.iterrows():
                segmen = str(row.get('segmen_ip', row.iloc[0])).strip()
                if segmen and segmen != '-' and segmen.lower() != 'nan':
                    
                    # --- PARSING STATUS LEBIH FLEKSIBEL ---
                    raw_status = str(row.get('status', 0)).strip().lower()
                    status_val = 0  # Default 0 (Tersedia)
                    
                    if raw_status in ['1', '1.0', 'digunakan', 'used', 'terpakai', 'aktif', 'true', 'ya']:
                        status_val = 1
                    elif raw_status in ['0', '0.0', 'tersedia', 'available', 'kosong', 'free', 'false', 'nan', '']:
                        status_val = 0
                    elif raw_status.isdigit():
                        status_val = int(float(raw_status))
                    else:
                        status_val = 1 if any(k in raw_status for k in ['pakai', 'guna', 'isi', 'aktif', 'live']) else 0

                    # Bersihkan lokasi dari 'nan'
                    raw_lokasi = str(row.get('lokasi', '')).strip()
                    lokasi_val = raw_lokasi if raw_lokasi and raw_lokasi.lower() != 'nan' and raw_lokasi != '-' else None

                    new_entry = IPAddress(
                        segmen_ip=segmen,
                        subnet_mask=str(row.get('subnet_mask', '')).strip() or None,
                        layanan=str(row.get('layanan', '')).strip() or None,
                        lokasi=lokasi_val,
                        status=status_val,
                        created_by='System (Auto-Import)'
                    )
                    db.session.add(new_entry)
            db.session.commit()
        except Exception as exc:
            ip_error = f"Gagal auto-import Excel ke DB: {type(exc).__name__}: {exc}"
            current_app.logger.exception('Gagal auto-import Excel IP')

    # Ambil seluruh data murni dari Database
    ip_entries = IPAddress.query.order_by(IPAddress.created_at.desc()).all()
    
    # Buat ringkasan langsung dari data database
    tersedia = sum(1 for e in ip_entries if e.status == 0)
    digunakan = sum(1 for e in ip_entries if e.status == 1)
    belum_diisi = sum(1 for e in ip_entries if e.status is None)
    total = len(ip_entries)

    lokasi_counter = {}
    for e in ip_entries:
        if e.lokasi:
            lok = e.lokasi.strip()
            if lok and lok.lower() != 'nan' and lok != '-':
                lokasi_counter[lok] = lokasi_counter.get(lok, 0) + 1

    def pct(n):
        return round(n / total * 100, 1) if total > 0 else 0

    top_lokasi = sorted(lokasi_counter.items(), key=lambda kv: kv[1], reverse=True)[:6]
    max_lokasi_count = top_lokasi[0][1] if top_lokasi else 1

    ip_summary = {
        'total': total,
        'tersedia': tersedia,
        'digunakan': digunakan,
        'belum_diisi': belum_diisi,
        'tersedia_pct': pct(tersedia),
        'digunakan_pct': pct(digunakan),
        'belum_diisi_pct': pct(belum_diisi),
        'seg1_end': pct(tersedia),
        'seg2_end': pct(tersedia) + pct(digunakan),
        'top_lokasi': [
            {'lokasi': lok, 'count': cnt, 'bar_pct': round(cnt / max_lokasi_count * 100, 1)}
            for lok, cnt in top_lokasi
        ],
    } if total > 0 else None

    return render_template(
        'shared/ip_management.html',
        active_page='ip_management',
        ip_error=ip_error,
        excel_path=excel_path,
        total_ip=total,
        used_ip=digunakan,
        ip_summary=ip_summary,
        ip_entries=ip_entries,
    )


@shared_bp.route('/ip-management/tambah', methods=['POST'])
@admin_required
def tambah_ip_address():
    def parse_date(field_name):
        raw = request.form.get(field_name, '').strip()
        if not raw:
            return None
        try:
            return datetime.strptime(raw, '%Y-%m-%d').date()
        except ValueError:
            return None

    segmen_ip = request.form.get('segmen_ip', '').strip()
    if not segmen_ip:
        flash('Segmen IP wajib diisi.', 'danger')
        return redirect(url_for('shared.ip_management'))

    entry = IPAddress(
        segmen_ip=segmen_ip,
        subnet_mask=request.form.get('subnet_mask', '').strip() or None,
        layanan=request.form.get('layanan', '').strip() or None,
        lokasi=request.form.get('lokasi', '').strip() or None,
        desc=request.form.get('desc', '').strip() or None,
        status=int(request.form.get('status', 0)),
        pic_req=request.form.get('pic_req', '').strip() or None,
        tgl_req=parse_date('tgl_req'),
        tgl_aprv=parse_date('tgl_aprv'),
        tgl_release=parse_date('tgl_release'),
        vlan_id=request.form.get('vlan_id', '').strip() or None,
        created_by=session.get('username'),
    )
    db.session.add(entry)
    db.session.commit()

    AuditLog.record(
        actor=session.get('username'),
        action='Tambah Data IP',
        detail=f'{entry.segmen_ip}{entry.subnet_mask or ""} — {entry.layanan or "(tanpa nama layanan)"} @ {entry.lokasi or "-"}',
        category='Umum',
    )
    flash(f'Data IP {entry.segmen_ip} berhasil ditambahkan.', 'success')
    return redirect(url_for('shared.ip_management'))


@shared_bp.route('/ip-management/edit/<int:id>', methods=['POST'])
@admin_required
def edit_ip_address(id):
    entry = IPAddress.query.get_or_404(id)

    def parse_date(field_name):
        raw = request.form.get(field_name, '').strip()
        if not raw:
            return None
        try:
            return datetime.strptime(raw, '%Y-%m-%d').date()
        except ValueError:
            return None

    segmen_ip = request.form.get('segmen_ip', '').strip()
    if not segmen_ip:
        flash('Segmen IP wajib diisi.', 'danger')
        return redirect(url_for('shared.ip_management'))

    entry.segmen_ip = segmen_ip
    entry.subnet_mask = request.form.get('subnet_mask', '').strip() or None
    entry.layanan = request.form.get('layanan', '').strip() or None
    entry.lokasi = request.form.get('lokasi', '').strip() or None
    entry.desc = request.form.get('desc', '').strip() or None
    entry.status = int(request.form.get('status', 0))
    entry.pic_req = request.form.get('pic_req', '').strip() or None
    entry.tgl_req = parse_date('tgl_req')
    entry.tgl_aprv = parse_date('tgl_aprv')
    entry.tgl_release = parse_date('tgl_release')
    entry.vlan_id = request.form.get('vlan_id', '').strip() or None

    db.session.commit()

    AuditLog.record(
        actor=session.get('username'),
        action='Edit Data IP',
        detail=f'{entry.segmen_ip}{entry.subnet_mask or ""} — {entry.layanan or "(tanpa nama layanan)"} @ {entry.lokasi or "-"}',
        category='Umum',
    )
    flash(f'Data IP {entry.segmen_ip} berhasil diperbarui.', 'success')
    return redirect(url_for('shared.ip_management'))


# --- Scheduler ---

@shared_bp.route('/scheduler')
@login_required
def scheduler_page():
    schedules = Schedule.query.order_by(Schedule.created_at.desc()).all()
    return render_template('shared/scheduler.html', active_page='scheduler', schedules=schedules)


@shared_bp.route('/scheduler/add', methods=['POST'])
@login_required
def add_scheduler():
    new_schedule = Schedule(
        pemohon=session.get('name', 'User'),
        schedule_time=request.form.get('schedule_time'),
        target_bandwidth=request.form.get('target_bandwidth'),
        notes=request.form.get('notes'),
        status='Pending Admin',
    )
    db.session.add(new_schedule)
    db.session.commit()

    AuditLog.record(
        actor=session.get('username'),
        action='Ajukan Scheduler',
        detail=f"Request #{new_schedule.id}: {new_schedule.target_bandwidth} Mbps pada {new_schedule.schedule_time}",
        reason=new_schedule.notes or 'Tidak ada catatan.',
        category='Scheduler',
    )
    flash('Pengajuan jadwal berhasil dikirim, menunggu approval admin.', 'success')
    return redirect(url_for('shared.scheduler_page'))


@shared_bp.route('/scheduler/approve/<int:schedule_id>', methods=['POST'])
@admin_required
def approve_scheduler(schedule_id):
    item = Schedule.query.get_or_404(schedule_id)
    item.status = 'Approved (Live)'
    db.session.commit()

    reason = request.form.get('reason', '').strip() or 'Tidak ada catatan tambahan.'
    AuditLog.record(
        actor=session.get('username'),
        action='Approve Scheduler',
        detail=f"Jadwal #{schedule_id} ({item.pemohon}, {item.target_bandwidth} Mbps) disetujui.",
        reason=reason,
        category='Scheduler',
    )
    flash('Jadwal disetujui.', 'success')
    return redirect(url_for('shared.scheduler_page'))


@shared_bp.route('/scheduler/reject/<int:schedule_id>', methods=['POST'])
@admin_required
def reject_scheduler(schedule_id):
    item = Schedule.query.get_or_404(schedule_id)
    item.status = 'Rejected'
    db.session.commit()

    reason = request.form.get('reason', '').strip() or 'Tidak ada catatan tambahan.'
    AuditLog.record(
        actor=session.get('username'),
        action='Reject Scheduler',
        detail=f"Jadwal #{schedule_id} ({item.pemohon}, {item.target_bandwidth} Mbps) ditolak.",
        reason=reason,
        category='Scheduler',
    )
    flash('Jadwal ditolak.', 'success')
    return redirect(url_for('shared.scheduler_page'))


# --- Proxy PRTG ---

@shared_bp.route('/api/prtg-chart')
@login_required
def api_prtg_chart():
    graph_id = request.args.get('id', current_app.config['PRTG_DEFAULT_GRAPH_ID'])
    url = (
        f"{current_app.config['PRTG_BASE_URL']}/chart.svg"
        f"?type=graph&graphid=0&id={graph_id}"
        f"&username={current_app.config['PRTG_USERNAME']}"
        f"&passhash={current_app.config['PRTG_PASSHASH']}"
    )
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return Response(resp.content, mimetype='image/svg+xml')
    except Exception:  # noqa: BLE001
        pass
    placeholder = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="220">'
        '<rect width="100%" height="100%" fill="#12161F"/>'
        '<text x="50%" y="50%" fill="#5A617A" font-size="13" text-anchor="middle">'
        'Server PRTG tidak terjangkau</text></svg>'
    )
    return Response(placeholder, mimetype='image/svg+xml')


@shared_bp.route('/api/prtg-devices')
@login_required
def api_prtg_devices():
    url = (
        f"{current_app.config['PRTG_BASE_URL']}/api/table.json"
        f"?content=devices&output=json"
        f"&username={current_app.config['PRTG_USERNAME']}"
        f"&passhash={current_app.config['PRTG_PASSHASH']}"
    )
    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            return jsonify(resp.json())
        return jsonify({'error': True, 'message': 'Gagal terhubung ke server PRTG'})
    except Exception:  # noqa: BLE001
        return jsonify({
            'devices': [
                {'device': 'Gateway Utama', 'host': '192.168.1.1', 'status': 'Up (Normal)', 'uptime': '29d 4h'},
                {'device': 'Switch Server', 'host': '192.168.1.2', 'status': 'Up (Normal)', 'uptime': '12d 9h'},
            ]
        })