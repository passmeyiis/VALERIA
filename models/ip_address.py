from datetime import datetime

from extensions import db


class IPAddress(db.Model):
    """Data IP address yang ditambahkan lewat form di aplikasi.

    Strukturnya sengaja disamakan dengan kolom di file Excel sumber
    (IP_address_INfomedia.xlsx): segmen_ip, subnet_mask, layanan, lokasi,
    desc, status, pic_req, tgl_req, tgl_aprv, tgl_release, vlan_id — supaya
    konsisten, TANPA meng-import ulang seluruh baris yang sudah ada di Excel.
    Data dari Excel tetap ditampilkan terpisah sebagai referensi (read-only).

    status: 0 = tersedia, 1 = digunakan/dibooking (mengikuti konvensi yang
    sama seperti catatan di file Excel aslinya).
    """

    __tablename__ = 'ip_addresses'

    id = db.Column(db.Integer, primary_key=True)
    kategori = db.Column(db.String(30), default='ip_10')  # ip_10 / ip_172 / ip_wan / ip_wan_karet
    segmen_ip = db.Column(db.String(50), nullable=False)
    subnet_mask = db.Column(db.String(10), nullable=True)
    layanan = db.Column(db.String(150), nullable=True)
    lokasi = db.Column(db.String(100), nullable=True)
    desc = db.Column(db.String(200), nullable=True)
    status = db.Column(db.Integer, default=0)
    pic_req = db.Column(db.String(100), nullable=True)
    tgl_req = db.Column(db.Date, nullable=True)
    tgl_aprv = db.Column(db.Date, nullable=True)
    tgl_release = db.Column(db.Date, nullable=True)
    vlan_id = db.Column(db.String(20), nullable=True)
    created_by = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f'<IPAddress {self.segmen_ip} ({self.lokasi})>'
