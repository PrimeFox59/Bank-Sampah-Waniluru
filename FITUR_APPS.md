# Fitur Aplikasi - Bank Sampah Waniluru

Daftar lengkap fitur berdasarkan role pengguna dalam aplikasi Bank Sampah Waniluru.

## 1. Fitur Umum (Semua User)
- **Login & Logout:** Keamanan akses menggunakan username dan password.
- **Profil Mandiri:** Setiap user dapat mengubah nama lengkap, panggilan, alamat, dan nomor WhatsApp sendiri.
- **Ubah Password:** Fitur keamanan untuk mengganti password secara mandiri.

## 2. Fitur Superuser (Pemilik/Pengembang)
- **Manajemen User:** Tambah, edit, dan hapus user dengan role apapun.
- **Login Sebagai User Lain:** Fitur simulasi untuk mengecek tampilan dari sisi warga atau panitia.
- **Data Dummy:** Generate data transaksi palsu untuk keperluan pengujian dan demo.
- **Audit Log:** Memantau seluruh aktivitas sensitif dalam sistem (login, transaksi, perubahan setting).
- **Statistik Global:** Ringkasan performa bank sampah secara keseluruhan.
- **Reset Data:** Membersihkan database (gunakan dengan hati-hati).
- **Pengaturan Jadwal Input:** Mengontrol jam operasional input transaksi bagi role Inputer.

## 3. Fitur Admin (Panitia Utama)
- **Dashboard Ringkasan:** Grafik tren harian, top warga, dan komposisi sampah.
- **Input Transaksi:** Mencatat setoran sampah warga (berat, kategori, harga).
- **Manajemen Kategori:** Tambah/edit kategori sampah dan update harga per kg.
- **Kelola Keuangan Warga:** Proses setoran tunai (Deposit) dan penarikan saldo (Withdrawal).
- **Manajemen Data Warga:** Registrasi warga baru dan update data warga.
- **Laporan Lengkap:** Generate laporan PDF bulanan/tahunan dan riwayat transaksi terperinci.
- **Pengaturan Jadwal Input:** Akses untuk mengatur waktu aktif penginputan bagi Inputer.

## 4. Fitur Inputer (Panitia Lapangan)
- **Input Transaksi:** Fitur utama untuk mencatat setoran sampah warga.
- **Riwayat Transaksi:** Melihat daftar transaksi yang baru saja diproses.
- **Update Harga:** Bisa mengubah harga kategori sampah jika diperlukan saat bertugas.
- **Pembatasan Akses:** Hanya bisa menginput pada jam/hari yang ditentukan oleh Admin/Superuser.

## 5. Fitur Warga (Nasabah)
- **Kartu Saldo Digital:** Melihat saldo saat ini secara real-time.
- **Statistik Penjualan:** Grafik performa penjualan sampah pribadi.
- **Riwayat Transaksi:** Daftar lengkap setoran sampah yang pernah dilakukan.
- **Laporan Keuangan:** Riwayat mutasi saldo (setor tunai/tarik tunai).
