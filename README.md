# Bank Sampah - Waste Bank Management System 🏦♻️

Aplikasi manajemen Bank Sampah berbasis Streamlit dan SQLite dengan 4 role pengguna yang berbeda dan tema UI/UX biru-putih yang modern.

## ✨ Fitur Baru Update Terbaru

### 🆕 Manajemen Warga Lengkap (Panitia)
- ✅ **Tambah Warga Baru** dengan identitas lengkap (NIK, Nama, Alamat, Telepon)
- ✅ **Edit Data Warga** untuk update informasi
- ✅ **Hapus Warga** dengan validasi saldo (harus Rp 0)
- ✅ **Daftar Warga** dengan informasi lengkap dalam tabel

### 📝 Identitas Warga Lengkap
- **NIK**: Nomor Induk Kependudukan 16 digit (validasi otomatis)
- **Nama Lengkap**: Sesuai KTP
- **Alamat Lengkap**: Alamat domisili
- **No. Telepon**: HP/WA yang aktif
- **Username & Password**: Untuk login

### 🎨 UI/UX Modern
- **Tema Biru-Putih**: Warna utama #1E88E5, #0D47A1, #E3F2FD
- **11 SVG Illustrations**: Icon custom untuk setiap fitur
- **Responsive Cards**: Hover effects & gradients
- **Empty States**: Ilustrasi menarik saat belum ada data
- **Form Validation**: Real-time validation NIK, password, dll

## Fitur Utama

### 🔐 4 Role Pengguna

1. **Super User**
   - Akses penuh ke semua fitur
   - Kelola semua pengguna
   - Login sebagai user lain tanpa password
   - Lihat audit log lengkap
   - Statistik global

2. **Pengepul (Collector)**
   - Kelola kategori sampah
   - Set dan update harga per kategori (Rp/Kg)
   - Lihat riwayat perubahan harga

3. **Panitia (Committee)**
   - Input transaksi penjualan sampah warga
   - **➕ Tambah warga baru** dengan data lengkap (NIK, alamat, telepon)
   - **✏️ Edit data warga** yang sudah terdaftar
   - **🗑️ Hapus warga** dengan validasi saldo
   - Kelola keuangan warga (deposit & withdrawal)
   - Otomatis mendapat 10% dari setiap transaksi
   - Laporan keuangan bulanan & tahunan
   - Monitoring performa warga
   - Pembukuan otomatis

4. **Warga (Resident)**
   - Cek saldo
   - Lihat performa pribadi
   - Riwayat transaksi
   - Riwayat deposit & penarikan

## Fitur Sistem

- ✅ Login & Autentikasi
- ✅ Dashboard untuk setiap role
- ✅ Audit log lengkap
- ✅ Kategori barang fleksibel
- ✅ Update harga sewaktu-waktu
- ✅ Sistem deposit (uang tidak diambil langsung)
- ✅ Fee panitia otomatis 10%
- ✅ Pembukuan otomatis
- ✅ Laporan bulanan & tahunan
- ✅ Monitoring performa warga
- ✅ **CRUD User oleh Panitia** (Tambah, Edit, Hapus)
- ✅ **Identitas lengkap warga** (NIK, Alamat, Telepon)
- ✅ **Validasi input** (NIK 16 digit, password min 6 karakter)

## Instalasi

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Jalankan aplikasi:
```bash
streamlit run app.py
```

## Default Users

## Default Users (dengan identitas lengkap)

| Username    | Password     | Role      | NIK              | Alamat                           | Telepon      |
|-------------|--------------|-----------|------------------|----------------------------------|--------------|
| superuser   | admin123     | Super User| -                | -                                | -            |
| pengepul1   | pengepul123  | Pengepul  | 3201234567890001 | Jl. Raya Pengepul No. 123        | 081234567890 |
| panitia1    | panitia123   | Panitia   | 3201234567890002 | Jl. Panitia Indah No. 45         | 081234567891 |
| warga1      | warga123     | Warga     | 3201234567890003 | Jl. Warga Sejahtera No. 10       | 081234567892 |
| warga2      | warga123     | Warga     | 3201234567890004 | Jl. Mawar Melati No. 25          | 081234567893 |

## Default Kategori Sampah

- Plastik Botol: Rp 3,000/Kg
- Plastik Kemasan: Rp 2,000/Kg
- Kardus: Rp 1,500/Kg
- Kertas: Rp 1,000/Kg
- Kaleng Aluminium: Rp 5,000/Kg
- Besi: Rp 2,500/Kg
- Kaca: Rp 500/Kg

## Struktur Database

### Tables:
- **users** - Data pengguna (dengan NIK, alamat, telepon)
  - id, username, password, full_name, role
  - **nik** (16 digit), **address**, **phone** ← Baru!
  - balance, active, created_at
- **categories** - Kategori sampah & harga
- **transactions** - Transaksi penjualan sampah
- **financial_movements** - Deposit & withdrawal
- **committee_earnings** - Pendapatan panitia
- **audit_log** - Log aktivitas sistem (termasuk create/update/delete user)
- **active_sessions** - Session super user

## Cara Panitia Mengelola Warga

### ➕ Tambah Warga Baru
1. Login sebagai Panitia
2. Pilih tab "👥 Kelola Warga"
3. Klik sub-tab "➕ Tambah Warga"
4. Isi form:
   - Username (untuk login)
   - Password (min 6 karakter)
   - Nama Lengkap (sesuai KTP)
   - **NIK (exactly 16 digit)** ← Validasi otomatis
   - **Alamat Lengkap**
   - **No. Telepon**
   - Role (warga/panitia)
5. Klik "➕ Tambah Warga"
6. ✅ User baru berhasil dibuat!

### ✏️ Edit Data Warga
1. Tab "👥 Kelola Warga" → "✏️ Edit Warga"
2. Pilih warga dari dropdown
3. Update data yang perlu diubah
4. Klik "💾 Simpan Perubahan"
5. ✅ Data berhasil diupdate!

### 🗑️ Hapus Warga
1. Tab "👥 Kelola Warga" → "🗑️ Hapus Warga"
2. Pilih warga dari dropdown (dengan info saldo)
3. Klik "🗑️ Hapus Warga"
4. ⚠️ Validasi: Hanya bisa hapus jika saldo = Rp 0
5. ✅ Warga berhasil dihapus!

## Flow Transaksi

1. Warga membawa sampah ke bank sampah
2. Panitia menimbang dan input transaksi
3. Sistem otomatis:
   - Hitung total: berat × harga
   - Potong fee panitia 10%
   - Tambah saldo warga (90%)
   - Catat pendapatan panitia
   - Log ke audit
4. Warga bisa:
   - Tarik saldo (withdrawal)
   - Deposit/simpan uang
   - Cek performa

## Teknologi

- **Frontend**: Streamlit
- **Database**: SQLite
- **Authentication**: SHA256 hashing
- **Language**: Python 3.8+

## Keamanan

- Password di-hash menggunakan SHA256
- Session management
- Audit log untuk semua aktivitas
- Role-based access control

## Developer

Dibuat untuk sistem manajemen Bank Sampah yang efisien dan transparan.

---

© 2026 Bank Sampah Management System
