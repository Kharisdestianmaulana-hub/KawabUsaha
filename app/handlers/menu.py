from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.utils.auth import get_user_access

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan Menu Utama KawanUsaha secara dinamis berdasarkan role."""
    
    user_id = update.effective_user.id
    access = get_user_access(user_id)
    
    if not access:
        text = "⚠️ Anda belum terdaftar di sistem. Silakan ketik /start untuk mendaftar atau gunakan kode undangan dari pemilik toko."
        if update.message:
            await update.message.reply_text(text)
        elif update.callback_query:
            await update.callback_query.message.edit_text(text)
        return

    role = access['role']
    
    keyboard = []
    
    if role == 'owner':
        keyboard = [
            [InlineKeyboardButton("💰 Kasir", callback_data="menu_penjualan"),
             InlineKeyboardButton("📦 Produk", callback_data="menu_produk")],
            [InlineKeyboardButton("📓 Buku Kasbon", callback_data="menu_kasbon"),
             InlineKeyboardButton("📊 Laporan", callback_data="menu_laporan")],
            [InlineKeyboardButton("💸 Pengeluaran", callback_data="menu_pengeluaran"),
             InlineKeyboardButton("👥 Pelanggan", callback_data="menu_pelanggan")],
            [InlineKeyboardButton("🧾 Invoice", callback_data="menu_invoice"),
             InlineKeyboardButton("⚙️ Pengaturan", callback_data="menu_pengaturan")],
            [InlineKeyboardButton("👨‍💼 Pegawai", callback_data="menu_pegawai"),
             InlineKeyboardButton("❓ Panduan", callback_data="menu_help")]
        ]
        text = "🏠 *Menu Utama Bos (Owner)*\n\nSilakan pilih menu di bawah ini:"
    else:
        # Role Kasir
        keyboard = [
            [InlineKeyboardButton("💰 Buka Kasir", callback_data="menu_penjualan")],
            [InlineKeyboardButton("📓 Buku Kasbon", callback_data="menu_kasbon")],
            [InlineKeyboardButton("👥 Daftar Pelanggan", callback_data="menu_pelanggan")],
            [InlineKeyboardButton("❓ Panduan & Bantuan", callback_data="menu_help")]
        ]
        text = "🏠 *Menu Utama Pegawai (Kasir)*\n\nSelamat bekerja! Silakan pilih menu:"
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan panduan pintar berdasarkan role user."""
    query = update.callback_query
    
    access = get_user_access(update.effective_user.id)
    role = access['role'] if access else 'kasir'
    
    if role == 'owner':
        text = (
            "❓ *PANDUAN PENGGUNAAN (OWNER)*\n\n"
            "KawanUsaha dilengkapi dengan fitur untuk mengelola toko secara menyeluruh:\n\n"
            "🛒 *Kasir:* Sistem keranjang belanja, penambahan diskon pesanan, pemilihan metode pembayaran (Tunai/BCA/dll), dan potong stok otomatis.\n"
            "📓 *Buku Kasbon:* Mencatat hutang pelanggan dengan cepat dan menerima pelunasannya (uang otomatis terhitung ke Omzet Laporan).\n"
            "📦 *Produk:* Mengelola daftar barang, kategori, harga, dan manajemen stok gudang.\n"
            "📊 *Laporan:* Kalkulasi Laba Bersih harian, rincian omzet per-bank, dan daftar produk terlaris.\n"
            "💸 *Pengeluaran:* Mencatat uang keluar untuk operasional toko (gaji, listrik, dll).\n"
            "🧾 *Invoice:* Mencetak ulang struk lama dalam bentuk PDF.\n"
            "👨‍💼 *Pegawai:* Membuat Kode Undangan agar kasir bisa login di HP mereka tanpa bisa melihat Laporan Keuangan.\n"
            "⚙️ *Pengaturan:* Mengubah Profil Toko (Nama, Alamat, WA), mengatur Daftar Bank Pembayaran, Mereset Data Transaksi, hingga Menutup Akun."
        )
    else:
        text = (
            "❓ *PANDUAN PENGGUNAAN (KASIR)*\n\n"
            "Sebagai garda depan toko, fitur Anda berfokus pada operasional kasir:\n\n"
            "🛒 *Buka Kasir:* Mencatat pembelian, menambahkan diskon nominal, dan mencetak struk. Pilih pelanggan terdaftar agar namanya muncul di nota.\n"
            "📓 *Buku Kasbon:* Gunakan menu ini saat ada pelanggan yang berhutang, atau saat mereka datang untuk membayar cicilan hutangnya.\n"
            "👥 *Daftar Pelanggan:* Daftarkan nama dan kontak pelanggan baru agar mudah dipilih saat transaksi."
        )
        
    keyboard = [[InlineKeyboardButton("⬅️ Mengerti & Kembali", callback_data="menu_main")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani ketika user mengklik tombol menu utama."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "menu_main":
        await show_main_menu(update, context)
        return
    elif query.data == "menu_help":
        await help_menu(update, context)
        return
        
    await query.message.edit_text(
        f"🛠 Menu ini sedang dalam perbaikan atau akses ditolak.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="menu_main")]]),
        parse_mode='Markdown'
    )
