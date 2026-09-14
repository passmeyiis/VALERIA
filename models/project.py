from extensions import db

class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_no = db.Column(db.Integer)
    project_id = db.Column(db.String(50))
    tahun = db.Column(db.Integer)
    periode = db.Column(db.String(50))
    nama_project = db.Column(db.String(255), nullable=False)
    jenis_project = db.Column(db.String(100))
    pmg = db.Column(db.String(100))
    pm = db.Column(db.String(100))
    revenue_akhir = db.Column(db.Numeric(18, 2))
    segment_sales = db.Column(db.String(100))
    klasifikasi_project = db.Column(db.String(100))
    nama_am = db.Column(db.String(100))
    tanggal_project_charter = db.Column(db.Date)
    target = db.Column(db.String(100))
    nama_pic = db.Column(db.String(100))
    status = db.Column(db.String(50))
    order_type = db.Column(db.String(100))
    konfigurasi = db.Column(db.String(100))
    integrasi = db.Column(db.String(100))
    tshoot = db.Column(db.String(100))
    keterangan = db.Column(db.Text)