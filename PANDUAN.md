# Panduan Penggunaan Bank Sampah

## 🎯 Login

Akses aplikasi di: http://localhost:8503

### Default Users:

| Role | Username | Password | Akses |
|------|----------|----------|-------|
| Super User | superuser | admin123 | Semua fitur |
| Pengepul | pengepul1 | pengepul123 | Kelola harga & kategori |
| Panitia | panitia1 | panitia123 | Transaksi & keuangan |
| Warga | warga1 | warga123 | Lihat saldo & performa |

---

## 📦 Pengepul - Kelola Kategori & Harga

### Fitur:
1. **Tambah Kategori Baru**
   - Nama kategori
   - Harga per Kg

2. **Update Harga**
   - Pilih kategori
   - Masukkan harga baru
   - Update otomatis

3. **Lihat Riwayat Harga**
   - Riwayat perubahan dari transaksi

### Cara Kerja:
1. Login sebagai pengepul
2. Tab "Kelola Kategori"
3. Tambah atau update harga sesuai kebutuhan

---

## 📊 Panitia - Koordinasi & Keuangan

### 1. Input Transaksi Sampah

**Langkah:**
1. Pilih warga
2. Pilih kategori sampah
3. Input berat (Kg)
4. Tambah catatan (opsional)
5. Klik "Proses Transaksi"

**Sistem Otomatis:**
- Hitung total: berat × harga/Kg
- Potong fee panitia 10%
- Tambah saldo warga 90%
- Catat pendapatan panitia
- Update balance

**Contoh:**
- Plastik Botol: Rp 3,000/Kg
- Berat: 5 Kg
- Total: Rp 15,000
- Fee Panitia: Rp 1,500 (10%)
- Warga terima: Rp 13,500

### 2. Kelola Keuangan Warga

**Penarikan (Withdrawal):**
- Warga minta tarik saldo
- Input jumlah penarikan
- Sistem kurangi saldo otomatis

**Deposit:**
- Warga setor uang
- Input jumlah deposit
- Sistem tambah saldo otomatis

### 3. Laporan Keuangan

**Bulanan:**
- Pilih tahun & bulan
- Lihat total transaksi, berat, revenue, fee panitia

**Tahunan:**
- Pilih tahun
- Statistik lengkap setahun

**Riwayat Transaksi:**
- Filter berdasarkan tanggal
- Export data

### 4. Performa Warga

- Pilih warga
- Pilih periode
- Lihat:
  - Total transaksi
  - Total berat sampah
  - Total pendapatan
  - Saldo saat ini

### 5. Pendapatan Panitia

- Filter berdasarkan periode
- Lihat total fee 10%
- Detail per transaksi

---

## 💰 Warga - Cek Saldo & Performa

### Fitur:

1. **Saldo Saat Ini**
   - Tampil di dashboard utama
   - Real-time update

2. **Performa Saya**
   - Total transaksi
   - Total berat sampah dijual
   - Total pendapatan
   - Breakdown per kategori

3. **Riwayat Transaksi**
   - Semua penjualan sampah
   - Detail: kategori, berat, harga, total, tanggal
   - Siapa yang memproses

4. **Riwayat Keuangan**
   - Semua penarikan & deposit
   - Saldo sebelum & sesudah
   - Catatan transaksi

---

## ⚡ Super User - Kontrol Penuh

### Fitur:

1. **Kelola User**
   - Lihat semua user
   - Tambah user baru
   - Atur role
   - Non-aktifkan user

2. **Login Sebagai User Lain**
   - Pilih user mana saja
   - Login tanpa password
   - Lihat dari perspektif mereka
   - Tombol "Kembali ke Super User"

3. **Audit Log**
   - Semua aktivitas sistem
   - Filter per user
   - Timestamp lengkap
   - Detail action

4. **Statistik Global**
   - Total transaksi sistem
   - Total berat & revenue
   - Pendapatan panitia total
   - User per role
   - Top 5 warga teraktif

---

## 🔄 Flow Sistem

### Skenario Normal:

1. **Warga membawa sampah**
   ```
   Warga datang dengan plastik botol 5 Kg
   ```

2. **Panitia timbang & input**
   ```
   Panitia login → Input Transaksi
   Pilih warga → Plastik Botol → 5 Kg
   ```

3. **Sistem proses otomatis**
   ```
   Total: 5 × Rp 3,000 = Rp 15,000
   Fee Panitia 10%: Rp 1,500
   Warga terima: Rp 13,500
   Saldo warga bertambah Rp 13,500
   ```

4. **Warga cek saldo**
   ```
   Warga login → Lihat saldo bertambah
   ```

5. **Warga tarik uang** (opsional)
   ```
   Warga minta tarik Rp 10,000
   Panitia proses penarikan
   Warga terima uang tunai
   Saldo tersisa Rp 3,500
   ```

### Skenario Deposit:

1. **Warga pilih simpan uang**
   ```
   Warga: "Saya mau simpan dulu, nanti diambil"
   ```

2. **Panitia proses deposit**
   ```
   Tidak ada penarikan
   Saldo tetap di sistem
   Warga bisa tarik kapan saja
   ```

---

## 📈 Monitoring & Laporan

### Untuk Panitia:

**Harian:**
- Cek transaksi hari ini
- Total penjualan

**Bulanan:**
- Generate laporan bulanan
- Pendapatan panitia
- Performa warga

**Tahunan:**
- Statistik tahunan
- Trend penjualan
- Program evaluation

### Untuk Warga:

**Kapan Saja:**
- Cek saldo real-time
- Lihat performa
- Riwayat lengkap

---

## 🔒 Keamanan

1. **Password di-hash**
   - SHA256 encryption
   - Tidak ada plain text password

2. **Audit Log**
   - Semua aktivitas tercatat
   - Timestamp & user detail
   - Tracking lengkap

3. **Role-Based Access**
   - Setiap role punya akses berbeda
   - Tidak bisa akses fitur lain

4. **Super User Monitoring**
   - Bisa login sebagai user lain
   - Monitor semua aktivitas
   - Kontrol penuh

---

## ❓ FAQ

**Q: Bagaimana cara mengubah harga kategori?**
A: Login sebagai Pengepul → Tab "Kelola Kategori" → Pilih kategori → Update harga

**Q: Apakah warga harus langsung tarik uang?**
A: Tidak, bisa disimpan (deposit). Panitia koordinasi keuangan warga.

**Q: Berapa fee panitia?**
A: 10% dari setiap transaksi, otomatis terpotong.

**Q: Bagaimana cara lihat pendapatan panitia?**
A: Login Panitia → Tab "Pendapatan Panitia" → Filter periode

**Q: Bisa tambah kategori sampah baru?**
A: Ya, Pengepul bisa tambah kategori kapan saja.

**Q: Super User bisa apa saja?**
A: Semua fitur, kelola user, login sebagai user lain, lihat audit log, statistik global.

**Q: Bagaimana cara reset password?**
A: Minta Super User untuk update password melalui "Kelola User".

---

## 🛠️ Troubleshooting

**Aplikasi tidak jalan:**
```bash
cd bank_sampah
python database.py
streamlit run app.py
```

**Database corrupt:**
```bash
# Hapus file bank_sampah.db
# Jalankan ulang: python database.py
```

**Lupa password:**
- Gunakan Super User untuk reset
- Atau hapus database dan init ulang

---

## 📞 Support

Untuk bantuan lebih lanjut, hubungi administrator sistem.

© 2026 Bank Sampah Management System
