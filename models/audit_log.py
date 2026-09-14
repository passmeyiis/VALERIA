from datetime import datetime

from extensions import db


class AuditLog(db.Model):
    """Catatan aktivitas penting di sistem.

    Dipakai buat dua hal:
    1. Riwayat aktivitas biasa (login/logout, tambah/ubah/hapus pengguna).
    2. Dasar "Berita Acara" resmi untuk perubahan yang butuh jejak formal
       (approve/reject scheduler, ubah Konfigurasi Global) — makanya ada
       kolom reason (tujuan/alasan) dan ref_no (nomor referensi dokumen).
    """

    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    ref_no = db.Column(db.String(40), unique=True, nullable=True)  # mis. BA-20260820-0007
    category = db.Column(db.String(40), default='Umum')  # Umum / Scheduler / Konfigurasi / Pengguna
    actor = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    detail = db.Column(db.String(500), nullable=True)
    reason = db.Column(db.String(500), nullable=True)  # tujuan/alasan perubahan
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Kategori yang butuh Berita Acara resmi (ditampilkan tombol "Lihat Berita Acara")
    FORMAL_CATEGORIES = ('Scheduler', 'Konfigurasi')

    @property
    def has_berita_acara(self) -> bool:
        return self.category in self.FORMAL_CATEGORIES

    @staticmethod
    def record(actor: str, action: str, detail: str = None, reason: str = None, category: str = 'Umum') -> 'AuditLog':
        entry = AuditLog(actor=actor, action=action, detail=detail, reason=reason, category=category)
        db.session.add(entry)
        db.session.commit()  # commit dulu supaya entry.id ke-generate

        if category in AuditLog.FORMAL_CATEGORIES:
            entry.ref_no = f"BA-{entry.created_at.strftime('%Y%m%d')}-{entry.id:04d}"
            db.session.commit()

        return entry

    def __repr__(self) -> str:
        return f'<AuditLog {self.actor}: {self.action}>'
