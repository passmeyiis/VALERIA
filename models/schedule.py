from datetime import datetime

from extensions import db


class Schedule(db.Model):
    """Pengajuan penjadwalan perubahan bandwidth dari klien, menunggu approval admin."""

    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    pemohon = db.Column(db.String(100), nullable=False)
    schedule_time = db.Column(db.String(50), nullable=False)
    target_bandwidth = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(50), default='Pending Admin')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f'<Schedule {self.id} {self.pemohon} ({self.status})>'
