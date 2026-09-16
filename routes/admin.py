from datetime import datetime
import io
import os
import pandas as pd
from flask import Blueprint, flash, redirect, render_template, request, session, url_for, send_file, send_from_directory
from fpdf import FPDF
import openpyxl

from extensions import db
from models import AuditLog, User
from routes.decorators import admin_required

admin_bp = Blueprint('admin', __name__)


# --- Dashboard ---

@admin_bp.route('/dashboard/admin')
@admin_required
def dashboard_admin():
    total_users = User.query.count()
    return render_template('admin/dashboard_admin.html', active_page='dashboard_admin', total_users=total_users)


@admin_bp.route('/dashboard/sup_admin')
@admin_required
def sup_admin():
    return redirect(url_for('admin.dashboard_admin'))


# --- Kelola Pengguna ---

@admin_bp.route('/kelola-pengguna')
@admin_required
def kelola_pengguna():
    users = User.query.order_by(User.created_at.asc()).all()
    return render_template('admin/kelola_pengguna.html', active_page='kelola_pengguna', users=users)


@admin_bp.route('/kelola-pengguna/tambah', methods=['POST'])
@admin_required
def tambah_pengguna():
    username = request.form.get('username', '').strip()
    name = request.form.get('name', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'klien')
    reason = request.form.get('reason', '').strip() or None

    if not username or not name or not password:
        flash('Semua field wajib diisi.', 'danger')
        return redirect(url_for('admin.kelola_pengguna'))

    if User.query.filter_by(username=username).first():
        flash('Username sudah dipakai, pilih username lain.', 'danger')
        return redirect(url_for('admin.kelola_pengguna'))

    user = User(username=username, name=name, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    AuditLog.record(
        actor=session.get('username'),
        action='Tambah pengguna',
        detail=f'{username} ({role})',
        reason=reason,
        category='Pengguna',
    )
    flash(f'Akun {username} berhasil dibuat.', 'success')
    return redirect(url_for('admin.kelola_pengguna'))


@admin_bp.route('/kelola-pengguna/ubah/<int:user_id>', methods=['POST'])
@admin_required
def ubah_pengguna(user_id):
    user = User.query.get_or_404(user_id)
    user.name = request.form.get('name', user.name).strip()
    user.role = request.form.get('role', user.role)
    reason = request.form.get('reason', '').strip() or None

    new_password = request.form.get('password', '')
    if new_password:
        user.set_password(new_password)

    db.session.commit()
    AuditLog.record(actor=session.get('username'), action='Ubah pengguna', detail=user.username, reason=reason, category='Pengguna')
    flash(f'Akun {user.username} berhasil diperbarui.', 'success')
    return redirect(url_for('admin.kelola_pengguna'))


@admin_bp.route('/kelola-pengguna/hapus/<int:user_id>', methods=['POST'])
@admin_required
def hapus_pengguna(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == session.get('user_id'):
        flash('Kamu tidak bisa menghapus akunmu sendiri.', 'danger')
        return redirect(url_for('admin.kelola_pengguna'))

    reason = request.form.get('reason', '').strip() or None
    username = user.username
    db.session.delete(user)
    db.session.commit()

    AuditLog.record(actor=session.get('username'), action='Hapus pengguna', detail=username, reason=reason, category='Pengguna')
    flash(f'Akun {username} berhasil dihapus.', 'success')
    return redirect(url_for('admin.kelola_pengguna'))


# --- Audit Logs ---

@admin_bp.route('/audit-logs')
@admin_required
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template('admin/audit_logs.html', active_page='audit_logs', logs=logs)


@admin_bp.route('/audit-logs/<int:log_id>/berita-acara')
@admin_required
def berita_acara(log_id):
    log = AuditLog.query.get_or_404(log_id)
    if not log.has_berita_acara:
        flash('Entry ini tidak memiliki Berita Acara formal.', 'danger')
        return redirect(url_for('admin.audit_logs'))
    return render_template('admin/berita_acara.html', log=log)


@admin_bp.route('/audit-logs/export')
@admin_required
def export_audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).all()
    rows = [
        {
            'Waktu': log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else '-',
            'Actor (yang login)': log.actor,
            'Aksi': log.action,
            'Detail Perubahan': log.detail or '-',
            'Tujuan / Alasan': log.reason or '-',
        }
        for log in logs
    ]
    df = pd.DataFrame(rows, columns=['Waktu', 'Actor (yang login)', 'Aksi', 'Detail Perubahan', 'Tujuan / Alasan'])
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Audit Log')
    buffer.seek(0)
    AuditLog.record(actor=session.get('username'), action='Unduh berita acara audit log')
    filename = f"berita-acara-valeria-{datetime.now().strftime('%Y%m%d-%H%M')}.xlsx"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@admin_bp.route('/audit-logs/export-pdf')
@admin_required
def export_audit_logs_pdf():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).all()
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 15)
    pdf.cell(0, 9, 'Laporan Audit Log - Sistem Valeria')
    pdf.ln(9)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(90, 97, 122)
    generated_at = datetime.now().strftime('%d %B %Y, %H:%M')
    pdf.cell(0, 6, f'Diunduh oleh: {session.get("name", session.get("username", "-"))}   |   Dibuat: {generated_at}   |   Total entri: {len(logs)}')
    pdf.ln(6)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    col_widths = [30, 28, 22, 40, 60, 60, 37]
    headers = ['Waktu', 'Ref. No', 'Kategori', 'Actor', 'Aksi', 'Detail', 'Tujuan / Alasan']

    def draw_header():
        pdf.set_font('Helvetica', 'B', 8.5)
        pdf.set_fill_color(217, 217, 217)
        for w, h in zip(col_widths, headers):
            pdf.cell(w, 7, h, border=1, fill=True)
        pdf.ln()
        pdf.set_font('Helvetica', '', 8)

    draw_header()

    def clip(text, limit):
        text = (text or '-').replace('\n', ' ')
        return text if len(text) <= limit else text[:limit - 1] + '…'

    for log in logs:
        if pdf.get_y() > 190:
            pdf.add_page()
            draw_header()

        row = [
            log.created_at.strftime('%d/%m/%y %H:%M') if log.created_at else '-',
            clip(getattr(log, 'ref_no', None), 16),
            clip(getattr(log, 'category', None), 14),
            clip(log.actor, 22),
            clip(log.action, 34),
            clip(log.detail, 46),
            clip(log.reason, 32),
        ]
        for w, val in zip(col_widths, row):
            pdf.cell(w, 6.5, val, border=1)
        pdf.ln()

    pdf_bytes = bytes(pdf.output())
    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)
    AuditLog.record(actor=session.get('username'), action='Unduh audit log (PDF)')
    filename = f"audit-log-valeria-{datetime.now().strftime('%Y%m%d-%H%M')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


# --- Analytics Dashboard ---

@admin_bp.route('/admin/analytics')
@admin_required
def admin_analytics():
    engine = db.engine
    query_segment = """
        SELECT segment_sales, SUM(revenue_akhir) AS total_revenue, COUNT(*) AS total_project
        FROM projects WHERE segment_sales IS NOT NULL GROUP BY segment_sales ORDER BY total_revenue DESC;
    """
    df_segment = pd.read_sql(query_segment, engine)

    query_order = """
        SELECT jenis_order, COUNT(*) AS jumlah_order
        FROM orders WHERE jenis_order IS NOT NULL GROUP BY jenis_order ORDER BY jumlah_order DESC;
    """
    df_order = pd.read_sql(query_order, engine)

    query_yearly = """
        SELECT tahun, SUM(harga) AS total_revenue
        FROM orders WHERE tahun IS NOT NULL GROUP BY tahun ORDER BY tahun ASC;
    """
    df_yearly = pd.read_sql(query_yearly, engine)

    segment_labels = df_segment['segment_sales'].tolist() if 'segment_sales' in df_segment.columns else []
    segment_revenues = df_segment['total_revenue'].tolist() if 'segment_sales' in df_segment.columns else []

    order_labels = df_order['jenis_order'].tolist() if 'jenis_order' in df_order.columns else []
    order_counts = df_order['jumlah_order'].tolist() if 'jenis_order' in df_order.columns else []

    yearly_labels = [str(int(t)) for t in df_yearly['tahun'].tolist()] if 'tahun' in df_yearly.columns and not df_yearly.empty else ['2024', '2025', '2026']
    yearly_revenues = df_yearly['total_revenue'].tolist() if 'tahun' in df_yearly.columns and not df_yearly.empty else [0, 0, 0]

    return render_template(
        'admin/analytics.html',
        active_page='analytics',
        segment_labels=segment_labels,
        segment_revenues=segment_revenues,
        order_labels=order_labels,
        order_counts=order_counts,
        yearly_labels=yearly_labels,
        yearly_revenues=yearly_revenues,
    )


# --- Summary Report (Sesuai Struktur Grafik & Data Asli Excel) ---

@admin_bp.route('/admin/summary/<int:tahun>')
@admin_required
def summary_page(tahun):
    from extensions import db
    from sqlalchemy import text

    monthly_labels = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    monthly_revenues = [0] * 12
    total_project_val = 0
    total_revenue_val = 0

    # Ambil trend revenue bulanan dari tabel histori
    rows = db.session.execute(
        text('SELECT bulan, revenue FROM monthly_revenue_history WHERE tahun = :tahun ORDER BY bulan'),
        {'tahun': tahun}
    ).fetchall()
    for bulan, revenue in rows:
        if 1 <= bulan <= 12:
            monthly_revenues[bulan - 1] = float(revenue)

    # Ambil total tahunan dari tabel histori (kalau ada)
    yearly = db.session.execute(
        text('SELECT total_project, total_revenue FROM yearly_summary_history WHERE tahun = :tahun'),
        {'tahun': tahun}
    ).fetchone()
    if yearly:
        total_project_val = yearly[0] or 0
        total_revenue_val = float(yearly[1] or 0)
    else:
        total_revenue_val = sum(monthly_revenues)

    # Matriks detail: data project asli dari tabel projects (data yang diinput lewat web)
    project_rows = db.session.execute(
        text('SELECT * FROM projects WHERE tahun = :tahun ORDER BY id DESC'),
        {'tahun': tahun}
    ).mappings().fetchall()

    # Kalau tabel projects untuk tahun ini kosong (histori lama belum ada data
    # per-project), pakai jumlah dari yearly_summary_history sebagai fallback
    if not project_rows and yearly:
        total_project_val = yearly[0] or 0

    table_columns = list(project_rows[0].keys()) if project_rows else []
    table_rows = [list(r.values()) for r in project_rows]

    return render_template(
        'admin/summary_report.html',
        active_page=f'summary_{tahun}',
        tahun=tahun,
        table_columns=table_columns,
        table_rows=table_rows,
        monthly_labels=monthly_labels,
        monthly_revenues=monthly_revenues,
        total_project=total_project_val,
        total_revenue=total_revenue_val,
    )


# --- Additional Reports (Dis Dow & Case 1500) ---

@admin_bp.route('/admin/reports/dis-dow')
@admin_required
def report_dis_dow():
    excel_path = 'report ITND fix(3).xlsx'
    dis_dow_headers = []
    dis_dow_data = []
    
    if os.path.exists(excel_path):
        try:
            if 'Dis Dow Jan - Apr' in pd.ExcelFile(excel_path).sheet_names:
                df_dis = pd.read_excel(excel_path, sheet_name='Dis Dow Jan - Apr')
                dis_dow_headers = df_dis.columns.tolist()
                dis_dow_data = df_dis.fillna('').astype(str).values.tolist()
        except Exception as e:
            flash(f'Gagal memuat data Dis Dow: {str(e)}', 'danger')

    return render_template(
        'admin/report_dis_dow.html',
        active_page='report_dis_dow',
        headers=dis_dow_headers,
        rows=dis_dow_data
    )


@admin_bp.route('/admin/reports/case-1500')
@admin_required
def report_case_1500():
    excel_path = 'report ITND fix(3).xlsx'
    case_headers = []
    case_data = []
    
    if os.path.exists(excel_path):
        try:
            if 'Case 1500 & Connectivity' in pd.ExcelFile(excel_path).sheet_names:
                df_case = pd.read_excel(excel_path, sheet_name='Case 1500 & Connectivity')
                case_headers = df_case.columns.tolist()
                case_data = df_case.fillna('').astype(str).values.tolist()
        except Exception as e:
            flash(f'Gagal memuat data Case 1500: {str(e)}', 'danger')

    return render_template(
        'admin/report_case_1500.html',
        active_page='report_case_1500',
        headers=case_headers,
        rows=case_data
    )


# --- List & Add/Edit Orders ---

@admin_bp.route('/admin/orders')
@admin_required
def list_orders():
    excel_path = 'report ITND fix(3).xlsx'
    
    if os.path.exists(excel_path):
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        sheet = wb['List Order']
        
        headers = [cell.value for cell in sheet[1]]
        orders_data = []
        
        for row_idx in range(2, sheet.max_row + 1):
            row_dict = {'id': row_idx - 2} 
            has_data = False
            for col_idx, header in enumerate(headers, 1):
                if not header:
                    continue
                cell = sheet.cell(row=row_idx, column=col_idx)
                val = cell.value
                
                if str(header).strip().lower() == 'file ba':
                    if cell.hyperlink and cell.hyperlink.target:
                        val = cell.hyperlink.target
                    elif not val:
                        val = '-'
                
                if val is not None:
                    has_data = True
                    if isinstance(val, datetime):
                        val = val.strftime('%Y-%m-%d')
                    elif isinstance(val, float) and val.is_integer():
                        val = str(int(val))
                    else:
                        val = str(val)
                else:
                    val = '-'
                
                row_dict[str(header).strip()] = val
            
            if has_data:
                orders_data.append(row_dict)
    else:
        orders_data = []

    return render_template('admin/list_orders.html', active_page='orders', orders=orders_data)


@admin_bp.route('/admin/orders/add', methods=['GET', 'POST'])
@admin_required
def add_order():
    excel_path = 'report ITND fix(3).xlsx'
    if request.method == 'POST':
        try:
            id_order = request.form.get('id_order')
            client = request.form.get('client')
            keterangan = request.form.get('keterangan') or '-'
            nilai = request.form.get('nilai') or 0
            file_ba = request.form.get('file_ba') or '-'

            if os.path.exists(excel_path):
                df = pd.read_excel(excel_path, sheet_name='List Order')
                cols = list(df.columns)
                new_row = {col: '-' for col in cols}
                for col in cols:
                    cl = col.lower()
                    if 'order' in cl or 'no order' in cl:
                        new_row[col] = id_order
                    elif 'client' in cl or 'provider' in cl:
                        new_row[col] = client
                    elif 'keterangan' in cl:
                        new_row[col] = keterangan
                    elif 'harga' in cl or 'nilai' in cl:
                        new_row[col] = nilai
                    elif 'file' in cl or 'ba' in cl:
                        new_row[col] = file_ba

                df_new = pd.DataFrame([new_row])
                df_combined = pd.concat([df, df_new], ignore_index=True)
                with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    df_combined.to_excel(writer, sheet_name='List Order', index=False)

            flash('Order baru berhasil ditambahkan!', 'success')
            return redirect(url_for('admin.list_orders'))
        except Exception as e:
            flash(f'Gagal menambah order: {str(e)}', 'danger')

    return render_template('admin/add_orders.html', active_page='orders')


@admin_bp.route('/admin/orders/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_order(id):
    excel_path = 'report ITND fix(3).xlsx'
    if not os.path.exists(excel_path):
        flash('File data Excel tidak ditemukan.', 'danger')
        return redirect(url_for('admin.list_orders'))

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb['List Order']
    headers = [cell.value for cell in sheet[1]]
    
    excel_row_idx = id + 2 

    if request.method == 'POST':
        try:
            for col_idx, header in enumerate(headers, 1):
                if not header:
                    continue
                header_key = str(header).strip()
                for field_name, form_val in request.form.items():
                    if field_name.lower() == header_key.lower():
                        sheet.cell(row=excel_row_idx, column=col_idx, value=form_val)
            
            wb.save(excel_path)
            flash('Data order berhasil diperbarui!', 'success')
            return redirect(url_for('admin.list_orders'))
        except Exception as e:
            flash(f'Gagal memperbarui order: {str(e)}', 'danger')

    order_dict = {'id': id}
    for col_idx, header in enumerate(headers, 1):
        if not header:
            continue
        val = sheet.cell(row=excel_row_idx, column=col_idx).value
        if isinstance(val, datetime):
            val = val.strftime('%Y-%m-%d')
        order_dict[str(header).strip()] = val if val is not None else ''

    return render_template('admin/edit_order.html', active_page='orders', order=order_dict)


# --- List & Add/Edit Projects ---

@admin_bp.route('/admin/projects')
@admin_required
def list_projects():
    excel_path = 'report ITND fix(3).xlsx'
    if os.path.exists(excel_path):
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        sheet = wb['List Project']
        
        headers = [cell.value for cell in sheet[1]]
        projects_data = []
        
        for row_idx in range(2, sheet.max_row + 1):
            row_dict = {'id': row_idx - 2} 
            has_data = False
            for col_idx, header in enumerate(headers, 1):
                if not header:
                    continue
                val = sheet.cell(row=row_idx, column=col_idx).value
                if val is not None:
                    has_data = True
                    if isinstance(val, datetime):
                        val = val.strftime('%Y-%m-%d')
                    elif isinstance(val, float) and val.is_integer():
                        val = str(int(val))
                    else:
                        val = str(val)
                else:
                    val = '-'
                row_dict[str(header).strip()] = val
            
            if has_data:
                projects_data.append(row_dict)
    else:
        projects_data = []

    return render_template('admin/list_projects.html', active_page='projects', projects=projects_data)


@admin_bp.route('/admin/projects/add', methods=['GET', 'POST'])
@admin_required
def add_project():
    excel_path = 'report ITND fix(3).xlsx'
    if request.method == 'POST':
        try:
            id_project = request.form.get('id_project')
            tahun = request.form.get('tahun')
            periode = request.form.get('periode')
            nama_project = request.form.get('nama_project')
            jenis_project = request.form.get('jenis_project')
            pmg = request.form.get('pmg') or '-'
            pm = request.form.get('pm') or '-'
            revenue_akhir = float(request.form.get('revenue_akhir') or 0)
            segment_sales = request.form.get('segment_sales') or '-'
            klasifikasi_project = request.form.get('klasifikasi_project') or '-'

            if os.path.exists(excel_path):
                df = pd.read_excel(excel_path, sheet_name='List Project')
                next_no = len(df) + 1
                
                new_row = {
                    ' No ': next_no,
                    ' ID Project ': id_project,
                    'Tahun': int(tahun) if tahun and tahun.isdigit() else tahun,
                    'Periode': periode,
                    ' Nama Project ': nama_project,
                    'Jenis Project': jenis_project,
                    ' PMG ': pmg,
                    ' PM ': pm,
                    ' Revenue Akhir ': revenue_akhir,
                    ' Segment Sales ': segment_sales,
                    ' Klasifikasi Project ': klasifikasi_project,
                    ' Nama AM ': '-',
                    ' Tanggal Project Charter ': '-',
                    ' Target ': '-',
                    'Nama PIC': '-',
                    'Status': 'Pending',
                    'Order': '-',
                    'Konfigurasi': '-',
                    'Integrasi': '-',
                    'Tshoot': '-',
                    'Keterangan': '-'
                }

                df_new = pd.DataFrame([new_row])
                df_combined = pd.concat([df, df_new], ignore_index=True)

                with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    df_combined.to_excel(writer, sheet_name='List Project', index=False)

            flash('Project baru berhasil ditambahkan!', 'success')
            return redirect(url_for('admin.list_projects'))
        except Exception as e:
            flash(f'Gagal menambah project: {str(e)}', 'danger')

    return render_template('admin/add_projects.html', active_page='projects')


@admin_bp.route('/admin/projects/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_project(id):
    excel_path = 'report ITND fix(3).xlsx'
    if not os.path.exists(excel_path):
        flash('File data Excel tidak ditemukan.', 'danger')
        return redirect(url_for('admin.list_projects'))

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb['List Project']
    headers = [cell.value for cell in sheet[1]]
    
    excel_row_idx = id + 2

    if request.method == 'POST':
        try:
            for col_idx, header in enumerate(headers, 1):
                if not header:
                    continue
                header_key = str(header).strip()
                for field_name, form_val in request.form.items():
                    if field_name.lower() == header_key.lower():
                        sheet.cell(row=excel_row_idx, column=col_idx, value=form_val)
            
            wb.save(excel_path)
            flash('Data project berhasil diperbarui!', 'success')
            return redirect(url_for('admin.list_projects'))
        except Exception as e:
            flash(f'Gagal memperbarui project: {str(e)}', 'danger')

    project_dict = {'id': id}
    for col_idx, header in enumerate(headers, 1):
        if not header:
            continue
        val = sheet.cell(row=excel_row_idx, column=col_idx).value
        if isinstance(val, datetime):
            val = val.strftime('%Y-%m-%d')
        project_dict[str(header).strip()] = val if val is not None else ''

    return render_template('admin/edit_project.html', active_page='projects', project=project_dict)