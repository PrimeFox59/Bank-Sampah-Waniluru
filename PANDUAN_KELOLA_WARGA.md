# 📖 Panduan Penggunaan - Kelola Warga (Panitia)

## 🔐 Login sebagai Panitia

1. Buka aplikasi: http://localhost:8503
2. Login dengan:
   - Username: `panitia1`
   - Password: `panitia123`

## 👥 Mengakses Kelola Warga

Setelah login, Anda akan melihat dashboard dengan 6 tabs:
1. ➕ Input Transaksi
2. 💰 Kelola Keuangan
3. **👥 Kelola Warga** ← KLIK DI SINI
4. 📑 Laporan
5. 📈 Performa Warga
6. 💵 Pendapatan Panitia

## ➕ Menambah Warga Baru

### Langkah-langkah:

1. Klik tab "👥 Kelola Warga"
2. Pastikan Anda di sub-tab "➕ Tambah Warga"
3. Isi formulir:

   **Kolom Kiri:**
   - 👤 Username: `[username untuk login]`
   - 🔒 Password: `[min 6 karakter]`
   - 📝 Nama Lengkap: `[sesuai KTP]`
   - 🆔 NIK: `[16 digit, contoh: 3201234567890099]`
   
   **Kolom Kanan:**
   - 🏠 Alamat Lengkap: `[alamat sesuai KTP]`
   - 📱 No. Telepon: `[HP/WA aktif]`
   - 👔 Role: `[pilih: warga atau panitia]`

4. Klik tombol "➕ Tambah Warga" (biru, full width)
5. ✅ Jika berhasil, akan muncul pesan sukses + balloons 🎈
6. ❌ Jika gagal, akan muncul pesan error (username sudah ada, NIK tidak 16 digit, dll)

### Validasi Otomatis:
- ✅ Password harus minimal 6 karakter
- ✅ NIK harus exactly 16 digit
- ✅ Username, Password, Nama Lengkap WAJIB diisi

## ✏️ Mengedit Data Warga

### Langkah-langkah:

1. Klik tab "👥 Kelola Warga"
2. Pilih sub-tab "✏️ Edit Warga"
3. Pilih warga dari dropdown: `[Nama (username)]`
4. Form akan otomatis terisi dengan data existing
5. Edit data yang ingin diubah:
   - 📝 Nama Lengkap
   - 🆔 NIK (harus 16 digit)
   - 🏠 Alamat Lengkap
   - 📱 No. Telepon
6. Klik "💾 Simpan Perubahan"
7. ✅ Jika berhasil, muncul pesan sukses
8. ❌ Jika NIK tidak 16 digit, muncul error

### Yang Tidak Bisa Diedit:
- ❌ Username (tetap tidak berubah)
- ❌ Password (harus reset manual oleh Super User)
- ❌ Role (tetap tidak berubah)
- ❌ Saldo (hanya bisa diubah via transaksi/deposit/withdrawal)

## 🗑️ Menghapus Warga

### Langkah-langkah:

1. Klik tab "👥 Kelola Warga"
2. Pilih sub-tab "🗑️ Hapus Warga"
3. **⚠️ PERHATIAN:** Akan ada warning tentang konsekuensi hapus
4. Pilih warga dari dropdown: `[Nama (username) - Saldo: Rp X]`
5. Klik tombol "🗑️ Hapus Warga"
6. Sistem akan cek saldo:
   - ✅ Jika saldo = Rp 0 → Warga berhasil dihapus
   - ❌ Jika saldo > 0 → Error: "Tidak bisa hapus! Warga masih punya saldo Rp X. Tarik dulu saldonya!"

### Sebelum Menghapus Warga dengan Saldo:
1. Pergi ke tab "💰 Kelola Keuangan"
2. Pilih sub-tab "💸 Penarikan"
3. Tarik semua saldo warga tersebut hingga Rp 0
4. Baru kemudian bisa dihapus

## 📋 Melihat Daftar Warga

Di bawah semua sub-tabs, ada tabel "📋 Daftar Warga Terdaftar" yang menampilkan:

| Kolom        | Keterangan                |
|--------------|---------------------------|
| ID           | ID unik warga             |
| Username     | Username untuk login      |
| Nama Lengkap | Nama sesuai KTP          |
| NIK          | 16 digit NIK             |
| Telepon      | No. HP/WA                |
| Saldo        | Saldo saat ini           |
| Status       | Aktif / Non-Aktif        |

**Empty State:**
Jika belum ada warga, akan muncul ilustrasi SVG dengan pesan:
"Belum Ada Warga Terdaftar - Tambahkan warga baru menggunakan form di atas"

## 💡 Tips & Best Practices

### Saat Menambah Warga:
1. ✅ Pastikan NIK benar dan 16 digit
2. ✅ Gunakan alamat lengkap (jalan, RT/RW, kelurahan, kecamatan, kota)
3. ✅ No. telepon aktif untuk komunikasi
4. ✅ Username unik dan mudah diingat (contoh: warga001, budi123)
5. ✅ Password minimal 6 karakter, informasikan ke warga

### Saat Mengedit Warga:
1. ✅ Pastikan data yang diubah sudah benar sebelum submit
2. ✅ NIK tidak boleh asal ubah, harus sesuai KTP
3. ✅ Update alamat jika warga pindah

### Saat Menghapus Warga:
1. ⚠️ Pastikan warga sudah tidak aktif
2. ⚠️ Pastikan saldo sudah Rp 0
3. ⚠️ Hapus warga akan menghapus SEMUA data terkait
4. ⚠️ Tindakan ini TIDAK BISA di-UNDO!

## 🔍 Audit Trail

Semua aktivitas user management tercatat di Audit Log:
- ✅ CREATE_USER: "Created user [username] with role [role]"
- ✅ UPDATE_USER: "Updated user [username]"
- ✅ DELETE_USER: "Deleted user ID [id]"

Super User bisa melihat semua audit log di dashboardnya.

## ❓ Troubleshooting

### Error: "Username sudah digunakan"
- **Solusi:** Gunakan username lain yang unik

### Error: "NIK harus 16 digit"
- **Solusi:** Pastikan NIK exactly 16 digit, tidak kurang tidak lebih

### Error: "Password minimal 6 karakter"
- **Solusi:** Gunakan password dengan minimal 6 karakter

### Error: "Tidak bisa hapus! Warga masih punya saldo"
- **Solusi:** Tarik dulu saldo warga di tab Kelola Keuangan → Penarikan

### Tidak melihat tab "Kelola Warga"
- **Solusi:** Pastikan Anda login sebagai **Panitia** atau **Super User**, bukan Warga atau Pengepul

## 📞 Support

Jika ada masalah atau pertanyaan, hubungi administrator sistem.

---

**Happy Managing! 🎉**
