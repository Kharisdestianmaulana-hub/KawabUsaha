# KawanUsaha - Telegram Bot MVP

KawanUsaha adalah asisten digital berbasis Telegram Bot yang dirancang khusus untuk membantu pemilik usaha kecil/UMKM melakukan pekerjaan operasional harian secara cepat tanpa perlu membuka aplikasi kasir yang rumit.

## 🚀 Fitur Utama (MVP)
1. **Onboarding & Profil Bisnis**: Pendaftaran otomatis dengan command `/start`.
2. **Manajemen Produk (CRUD)**: Tambah, edit harga, hapus, dan lihat daftar produk.
3. **Manajemen Stok**: Stok masuk, stok keluar, beserta riwayat transaksi pergerakan stok.
4. **Peringatan Stok Menipis**: Notifikasi otomatis saat stok menipis (≤ 5 pcs) saat transaksi.
5. **Kasir / Penjualan**: Pencatatan omzet yang terintegrasi langsung dengan pengurangan stok.
6. **Laporan Usaha**: Rangkuman transaksi hari ini, 7 hari terakhir, dan bulan berjalan, lengkap dengan Total Omzet & Top 3 Produk Terlaris.
7. **Buku Pelanggan (CRM)**: Menyimpan nama dan nomor WhatsApp pelanggan beserta riwayat belanjanya.
8. **Cetak Invoice PDF**: Pembuatan struk format PDF secara instan dari Telegram.

## 🛠 Teknologi yang Digunakan
- **Python 3.14**
- **python-telegram-bot** (v21+)
- **SQLite3** (Database lokal tanpa setup server)
- **ReportLab** (Untuk merender file PDF)

## 📦 Cara Menjalankan secara Lokal
1. Pastikan Anda memiliki Token Bot Telegram (dapatkan dari [@BotFather](https://t.me/botfather)).
2. Buat file `.env` dan masukkan token Anda:
   ```env
   BOT_TOKEN=123456789:YOUR_BOT_TOKEN_HERE
   ```
3. Buat _virtual environment_ dan jalankan bot:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python main.py
   ```
4. Buka Telegram dan ketik `/start` pada bot Anda.

## 📁 Struktur Direktori
Sistem KawanUsaha ini sudah menerapkan arsitektur *modular* agar mudah di-*scale* saat nanti sistem dikembangkan menjadi *multi-tenant* untuk ribuan pengguna secara serentak.
- `/app/database/`: Berisi skema (migrations) dan koneksi SQLite.
- `/app/handlers/`: Logika routing Telegram (Menu, Produk, Stok, Penjualan, Pelanggan, Laporan, Invoice).
- `/app/utils/`: Script pendukung seperti `pdf_generator.py`.
