# 🏪 KawanUsaha - Asisten Digital & Kasir UMKM via Telegram

KawanUsaha adalah aplikasi kasir pintar (Point of Sale) dan sistem pembukuan yang beroperasi **100% di dalam Telegram Bot**. Dirancang khusus untuk warung, toko kelontong, dan UMKM di Indonesia agar bisa mengelola bisnis tanpa perlu menginstal aplikasi berat yang menguras memori HP.

🌐 **Website Resmi / Landing Page**: [Akses di sini](https://Kharisdestianmaulana-hub.github.io/KawabUsaha) (Jika GitHub Pages sudah diaktifkan)

---

## ✨ Fitur Unggulan

KawanUsaha versi terbaru telah dilengkapi dengan modul skala *Enterprise* yang disederhanakan untuk kelas warung:

*   🛒 **Kasir Pintar Terintegrasi**
    *   Sistem keranjang belanja multi-item.
    *   Fitur **Diskon Transaksi** (Nominal Rupiah).
    *   Pemilihan **Metode Pembayaran** (Tunai, BCA, QRIS, dsb).
    *   Stok otomatis terpotong saat transaksi selesai.
*   📓 **Buku Kasbon (Piutang)**
    *   Catat pelanggan yang berhutang dengan cepat tanpa memotong stok.
    *   Terima uang pelunasan yang otomatis masuk ke hitungan **Omzet Hari Ini**.
    *   Pantau riwayat cicilan kasbon per pelanggan.
*   🧾 **Struk PDF Otomatis**
    *   Nota cetak digital (PDF) lengkap dengan rincian diskon, metode bayar, dan nama kasir yang bertugas.
*   📊 **Laporan & Laba Bersih**
    *   Sistem akuntansi otomatis: **Total Omzet – Total Pengeluaran = Laba Bersih**.
    *   Rincian uang masuk berdasarkan bank (Berapa tunai di laci, berapa saldo di rekening).
    *   Daftar produk terlaris harian/bulanan.
*   👥 **Multi-Kasir (Role-Based Access)**
    *   **Bos (Owner)** memiliki kendali penuh (Laporan, Pengeluaran, Reset Data).
    *   Bos dapat men-generate **Kode Undangan** rahasia untuk pegawai.
    *   **Pegawai (Kasir)** hanya bisa mengakses menu Kasir dan Pelanggan.
*   📦 **Manajemen Inventaris**
    *   Kelola produk, edit harga/kategori, dan tambah/kurangi stok.
*   ⚙️ **Pengaturan Tingkat Lanjut**
    *   Ubah profil toko (Nama, Alamat, No WA).
    *   Kustomisasi daftar Rekening Bank/E-Wallet.
    *   **Sapu Bersih (Reset Data)** dengan gembok keamanan 3 lapis.

---

## 🛠 Teknologi (Tech Stack)

*   **Bahasa**: Python 3.10+
*   **Framework Bot**: `python-telegram-bot` v20+ (Asynchronous)
*   **Database**: SQLite3 (Ringan, *built-in*, menggunakan relasi *Foreign Key* dan *Cascade*)
*   **PDF Generator**: ReportLab
*   **Landing Page**: HTML5, Tailwind CSS (CDN), FontAwesome Icons

---

## 📂 Struktur Direktori

```text
KawanUsaha/
├── app/
│   ├── bot.py                # Entry point handler Telegram
│   ├── config.py             # Konfigurasi Token
│   ├── database/             # Logika koneksi & Migrasi SQLite (Pembuatan Tabel)
│   ├── handlers/             # Modul Fitur (Kasbon, Penjualan, Produk, Laporan, dll)
│   └── utils/                # Helper (Generator PDF & Autentikasi Role)
├── docs/                     # Kode Website Statis (Landing Page) untuk GitHub Pages
├── .env                      # File rahasia berisi BOT_TOKEN
├── main.py                   # Script utama untuk menjalankan bot
└── requirements.txt          # Daftar library Python
```

---

## 🚀 Cara Menjalankan Bot di Komputer/Server

1. **Clone Repositori**
   ```bash
   git clone https://github.com/Kharisdestianmaulana-hub/KawabUsaha.git
   cd KawabUsaha
