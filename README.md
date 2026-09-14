# Valeria — Network Monitoring & Service Scheduling (by Infomedia)

Aplikasi Flask untuk monitoring jaringan (via PRTG) dan pengajuan penjadwalan
layanan, dengan tiga role: **Admin**, **Super Admin** (dua-duanya akses penuh
dan identik — sengaja dipisah jadi 2 login berbeda supaya audit log bisa
bedain siapa yang benar-benar bertindak), dan **Klien** (akses terbatas).

## Struktur folder

```
valeria/
  app.py                   # entry point — bikin app, daftarin blueprint, seed akun default
  config.py                 # semua konfigurasi (baca dari environment variable)
  extensions.py              # instance SQLAlchemy
  requirements.txt
  .env.example               # contoh isi file .env — salin & sesuaikan
  IP_address_INfomedia.xlsx

  models/                    # satu file per tabel database
    user.py                    # akun (admin / superadmin / klien)
    schedule.py                 # pengajuan bandwidth
    audit_log.py                 # riwayat aktivitas + berita acara
    global_config.py              # pengaturan operasional (refresh interval, dll)

  routes/                    # satu file per kelompok fitur (blueprint)
    auth.py                    # login, logout
    admin.py                    # dashboard admin, kelola pengguna, konfigurasi, audit log
    klien.py                     # dashboard klien
    shared.py                     # ip management, scheduler, proxy PRTG (admin & klien)
    decorators.py                  # @login_required, @admin_required

  templates/                  # satu folder per kategori halaman
    auth/login.html
    admin/dashboard_admin.html      # dashboard operasional (device table + grafik)
    admin/dashboard_sup_admin.html   # dashboard overview sistem
    admin/kelola_pengguna.html
    admin/konfigurasi_global.html
    admin/audit_logs.html
    admin/berita_acara.html          # dokumen resmi per-aktivitas, bisa di-print/PDF
    klien/dashboard_klien.html
    shared/base.html                  # layout+sidebar dipakai semua halaman
    shared/ip_management.html
    shared/scheduler.html

  static/
    css/style.css              # satu design system dipakai semua halaman
```

## 1. Setup database PostgreSQL

```bash
psql -U postgres -c "CREATE DATABASE valeria_db;"
```

Atau pakai Docker kalau belum ada PostgreSQL ter-install:

```bash
docker run --name valeria-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres
docker exec -it valeria-postgres psql -U postgres -c "CREATE DATABASE valeria_db;"
```

## 2. Setup environment

```bash
cp .env.example .env
```

Buka `.env`, isi minimal:
- `DATABASE_URL` — **pastikan formatnya `postgresql://username:password@host:port/nama_db`**
  (jangan sampai username-nya kosong seperti `postgresql://:postgres@...`)
- `SECRET_KEY` — ganti dengan string acak
- `PRTG_BASE_URL`, `PRTG_USERNAME`, `PRTG_PASSHASH` — lihat bagian 4 di bawah

## 3. Install dependencies & jalankan

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
python app.py
```

Buka `http://localhost:5000`. Saat pertama kali dijalankan (tabel `users` masih
kosong), aplikasi otomatis bikin 3 akun default dan nge-print ke terminal:

```
admin      : admin / admin123        (role: admin)
superadmin : superadmin / super123   (role: superadmin)
klien      : klien / klien123        (role: klien)
```

**Ganti password ini lewat halaman Kelola Pengguna setelah login**, atau ganti
`SEED_*_PASSWORD` di `.env` sebelum run pertama kali.

## 4. Supaya grafik PRTG beneran muncul

Isi 3 variabel ini di `.env` dengan data server PRTG kamu yang sebenarnya:

```
PRTG_BASE_URL=http://alamat-server-prtg-kamu
PRTG_USERNAME=username_prtg_kamu
PRTG_PASSHASH=passhash_prtg_kamu
```

`PRTG_BASE_URL=http://127.0.0.1` (nilai default) cuma benar kalau PRTG core
server-nya jalan di komputer yang SAMA dengan Flask ini. Kalau PRTG-nya di
server/komputer lain, wajib diganti ke IP/hostname server PRTG yang sebenarnya.

Cara dapat `passhash`: login ke PRTG web interface → Setup → Account Settings
→ My Account → bagian "Passhash".

Passhash **tidak pernah** dikirim ke browser — semua request ke PRTG lewat
proxy backend (`/api/prtg-chart`, `/api/prtg-devices`).

## 5. Data Excel IP Address

File `IP_address_INfomedia.xlsx` sudah ada di root project, header kolom asli
ada di baris index 6 (`IP_EXCEL_HEADER_ROW=6` di `.env`). Kalau halaman IP
Management masih menunjukkan "Data Excel belum terbaca", pesan errornya akan
tampil di halaman itu (kalau login sebagai admin/superadmin) — cek juga log di
terminal tempat `python app.py` jalan untuk detail lengkapnya.

## 6. Audit Log & Berita Acara

Setiap approve/reject scheduler dan perubahan Konfigurasi Global **wajib**
diisi kolom "Tujuan / Alasan" — ini yang dicatat di Audit Log supaya atasan
bisa lihat siapa yang request, siapa yang ubah, dan untuk apa.

- Halaman **Audit Logs** menampilkan semua aktivitas + tombol "Unduh Berita
  Acara (.xlsx)" untuk export semuanya jadi satu file Excel.
- Untuk aktivitas kategori Scheduler/Konfigurasi, ada juga tombol per-baris ke
  halaman **Berita Acara** resmi (format dokumen dengan kop, nomor referensi,
  kolom tanda tangan) yang bisa dibuka dan di-print/save-as-PDF langsung dari
  browser (tombol "Unduh / Print sebagai PDF").

## Ringkasan perubahan dari versi sebelumnya

- **Login**: cek username + password sungguhan lewat tabel `users` (password
  di-hash).
- **Role**: `admin` dan `superadmin` — dua login terpisah, isi/akses identik.
  `klien` tetap terbatas.
- **Database**: PostgreSQL, bukan SQLite.
- **PRTG passhash**: tidak lagi ter-expose ke browser, lewat proxy backend.
- **Excel IP data**: bug baca header sudah diperbaiki + error message lebih jelas.
- **Kelola Pengguna**: fungsional penuh (tambah/edit/hapus, tersimpan ke DB).
- **Konfigurasi Global**: sekarang punya bagian yang benar-benar bisa diedit
  (refresh interval, ambang warning, email notifikasi, catatan) — setiap
  perubahan wajib disertai alasan dan otomatis tercatat di Audit Log.
- **Audit Logs**: fungsional, mencatat login/logout, CRUD user, approve/reject
  scheduler, dan perubahan konfigurasi — lengkap dengan siapa & tujuannya.
- **Berita Acara**: dokumen resmi per-aktivitas (untuk kategori Scheduler &
  Konfigurasi) yang bisa dilihat dan diunduh sebagai PDF, plus export semua
  audit log jadi Excel.
- **Desain**: dark theme aksen merah, font Sora + Inter + JetBrains Mono,
  konsisten di semua halaman lewat satu `base.html` + `style.css`.
