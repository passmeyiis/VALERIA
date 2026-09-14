from datetime import datetime

from extensions import db


class IPDeviceEntry(db.Model):
    """Data IP per-device di Data Center, ditambahkan lewat form di aplikasi.

    Strukturnya disamakan dengan sheet 'IP JTN' / 'IP KBL' di file Excel
    sumber, yang formatnya beda dari sheet segmen (IP 10/172/WAN): di sini
    satu baris = satu IP address device, bukan satu segmen/subnet.
    """

    __tablename__ = 'ip_device_entries'

    id = db.Column(db.Integer, primary_key=True)
    kategori = db.Column(db.String(20), default='ip_jtn')  # ip_jtn / ip_kbl
    ip_addr = db.Column(db.String(50), nullable=False)
    vlan_id = db.Column(db.String(20), nullable=True)
    netmask = db.Column(db.String(10), nullable=True)
    ip_gtw = db.Column(db.String(50), nullable=True)
    status_text = db.Column(db.String(30), nullable=True)  # Used / Not In Used / Hardening
    service = db.Column(db.String(200), nullable=True)
    pic_req = db.Column(db.String(100), nullable=True)
    tgl_req = db.Column(db.Date, nullable=True)
    tgl_aprv = db.Column(db.Date, nullable=True)
    tgl_release = db.Column(db.Date, nullable=True)
    created_by = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f'<IPDeviceEntry {self.ip_addr} ({self.kategori})>'
