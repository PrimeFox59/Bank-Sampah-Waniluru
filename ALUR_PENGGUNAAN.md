# Alur Penggunaan Aplikasi (User Flow)

Dokumen ini menjelaskan alur kerja utama dalam sistem Bank Sampah Waniluru.

## 1. Alur Pendaftaran & Login
1. **Pendaftaran:** Admin/Superuser mendaftarkan warga baru melalui menu "Manage User".
2. **Login:** User masuk menggunakan username dan password yang diberikan.
3. **Update Profil:** User melengkapi data profil dan mengganti password default (sangat disarankan).

## 2. Alur Transaksi Sampah
1. **Penimbangan:** Warga membawa sampah ke bank sampah.
2. **Input Data:** Admin atau Inputer memilih nama warga, kategori sampah, dan memasukkan berat (Kg).
3. **Pencatatan:** Sistem menghitung total harga (Harga/Kg x Berat).
4. **Bagi Hasil:** Sistem memotong 10% (default) untuk biaya operasional admin dan 90% masuk ke saldo warga.
5. **Konfirmasi:** Transaksi muncul di riwayat transaksi admin dan dashboard warga.

## 3. Alur Pengelolaan Keuangan (Tabungan)
1. **Cek Saldo:** Warga melihat saldo di dashboard.
2. **Penarikan (Withdrawal):**
   - Warga mendatangi Admin untuk tarik tunai.
   - Admin memasukkan jumlah penarikan di menu "Keuangan".
   - Saldo warga berkurang, status transaksi tercatat.
3. **Setoran Tunai (Deposit):**
   - Warga menyetor uang tunai (opsional, selain dari sampah).
   - Admin memasukkan jumlah deposit di menu "Keuangan".
   - Saldo warga bertambah.

## 4. Alur Kontrol Operasional (Admin)
1. **Update Harga:** Admin memperbarui harga sampah per kategori sesuai harga pasar terkini.
2. **Jadwal Input:** Admin mengatur jam aktif (misal: Senin-Kamis 08:00-12:00).
3. **Inputer Restriction:** Inputer tidak akan bisa membuka form transaksi di luar jam tersebut.

## 5. Alur Pelaporan
1. **Monitoring:** Admin memantau tren harian dan kategori terpopuler melalui grafik dashboard.
2. **Filter Data:** Admin memilih periode (tanggal mulai/selesai) dan filter warga.
3. **Cetak PDF:** Admin menekan tombol "Generate PDF" untuk arsip atau pembukuan fisik.
