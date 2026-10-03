import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from app.database.connection import get_db_connection
from app.utils.auth import get_user_access

(EDIT_BIZ_NAME, EDIT_BIZ_ADDRESS, EDIT_BIZ_PHONE, EDIT_PAYMENT_METHODS, DEL_BIZ_NAME, DEL_BIZ_CONFIRM, RESET_DATA_STEP1, RESET_DATA_PIN, RESET_DATA_CONFIRM) = range(9)

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    access = get_user_access(user_id)
    if not access or access['role'] != 'owner':
        await query.message.edit_text("⚠️ Akses ditolak. Anda bukan pemilik.")
        return
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM businesses WHERE id = ?", (access['business_id'],))
        biz = cursor.fetchone()
        
    payment_methods = biz['payment_methods'] if biz['payment_methods'] else 'Tunai,QRIS'
        
    text = (
        f"⚙️ *Pengaturan Usaha*\n\n"
        f"🏢 Nama Usaha : *{biz['name']}*\n"
        f"📞 No. WhatsApp: {biz['phone'] or '-'}\n"
        f"📍 Alamat      : {biz['address'] or '-'}\n"
        f"💳 Pembayaran  : {payment_methods}\n\n"
        f"⚠️ Batas Peringatan Stok Menipis: {biz['low_stock_threshold']} pcs\n\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("✏️ Nama Usaha", callback_data="edit_biz_name"),
         InlineKeyboardButton("📍 Alamat", callback_data="edit_biz_address")],
        [InlineKeyboardButton("📞 No. WhatsApp", callback_data="edit_biz_phone"),
         InlineKeyboardButton("💳 Pembayaran", callback_data="edit_payment_methods")],
        [InlineKeyboardButton("🧹 Reset Data Toko", callback_data="reset_data_start")],
        [InlineKeyboardButton("🗑 Hapus Akun Usaha (Fatal)", callback_data="delete_biz_start")],
        [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data="menu_main")]
    ]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ================= UBAH PROFIL =================
async def start_edit_biz_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "🏢 Masukkan *Nama Usaha* yang baru:\n\n_(Ketik /cancel untuk membatalkan)_", 
        parse_mode='Markdown'
    )
    return EDIT_BIZ_NAME

async def save_biz_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text
    access = get_user_access(update.effective_user.id)
    with get_db_connection() as conn:
        conn.execute("UPDATE businesses SET name = ? WHERE id = ?", (new_name, access['business_id']))
        conn.commit()
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Pengaturan", callback_data="menu_pengaturan")]]
    await update.message.reply_text(f"✅ Nama usaha berhasil diubah menjadi *{new_name}*.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def start_edit_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("📍 Masukkan *Alamat Lengkap* usaha Anda:\n\n_(Ketik /cancel untuk membatalkan)_", parse_mode='Markdown')
    return EDIT_BIZ_ADDRESS

async def save_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_val = update.message.text
    access = get_user_access(update.effective_user.id)
    with get_db_connection() as conn:
        conn.execute("UPDATE businesses SET address = ? WHERE id = ?", (new_val, access['business_id']))
        conn.commit()
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Pengaturan", callback_data="menu_pengaturan")]]
    await update.message.reply_text(f"✅ Alamat berhasil diubah menjadi:\n*{new_val}*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def start_edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("📞 Masukkan *No. WhatsApp / Telepon* usaha Anda:\n\n_(Ketik /cancel untuk membatalkan)_", parse_mode='Markdown')
    return EDIT_BIZ_PHONE

async def save_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_val = update.message.text
    access = get_user_access(update.effective_user.id)
    with get_db_connection() as conn:
        conn.execute("UPDATE businesses SET phone = ? WHERE id = ?", (new_val, access['business_id']))
        conn.commit()
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Pengaturan", callback_data="menu_pengaturan")]]
    await update.message.reply_text(f"✅ No. WA berhasil diubah menjadi: *{new_val}*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

# ================= KELOLA PEMBAYARAN =================
async def start_edit_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "💳 Masukkan daftar Bank / Metode Pembayaran Anda.\n\n"
        "Pisahkan dengan **koma**. Contoh:\n"
        "`Tunai, BCA, Mandiri, QRIS, OVO`\n\n"
        "_(Ketik /cancel untuk membatalkan)_", 
        parse_mode='Markdown'
    )
    return EDIT_PAYMENT_METHODS

async def save_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text
    methods_list = [m.strip() for m in raw_text.split(",") if m.strip()]
    if not methods_list:
        methods_list = ["Tunai"]
    
    new_methods = ",".join(methods_list)
    user_id = update.effective_user.id
    
    access = get_user_access(user_id)
    if not access:
        return ConversationHandler.END
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE businesses SET payment_methods = ? WHERE id = ?", (new_methods, access['business_id']))
        conn.commit()
        
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Pengaturan", callback_data="menu_pengaturan")]]
    await update.message.reply_text(
        f"✅ Metode pembayaran berhasil disimpan:\n*{new_methods}*", 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='Markdown'
    )
    return ConversationHandler.END

# ================= RESET DATA (BONGKAR GUDANG) =================
async def start_reset_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🚨 Ya, Saya Paham Risikonya", callback_data="reset_data_step1")],
        [InlineKeyboardButton("⬅️ Batal", callback_data="menu_pengaturan")]
    ]
    
    await query.message.edit_text(
        "🧹 *RESET DATA TOKO*\n\n"
        "⚠️ **PERINGATAN**: Aksi ini akan membersihkan **SELURUH DATA** (Produk, Penjualan, Laporan, Kasbon, Pelanggan, Pegawai), "
        "kecuali Nama Toko & Pengaturan Anda.\n\n"
        "Toko akan dikosongkan seperti baru pertama kali diinstal.\n"
        "Apakah Anda sungguh ingin melakukan ini?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return RESET_DATA_STEP1

async def reset_data_generate_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    pin = str(random.randint(1000, 9999))
    context.user_data['reset_pin'] = pin
    
    await query.message.edit_text(
        f"Langkah Keamanan ke-2:\n\n"
        f"Untuk memastikan ini bukan ketidaksengajaan, silakan ketik angka keamanan berikut:\n\n"
        f"👉 **{pin}**\n\n"
        f"_(Ketik angkanya, atau ketik /cancel untuk membatalkan)_",
        parse_mode='Markdown'
    )
    return RESET_DATA_PIN

async def verify_reset_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    expected = context.user_data.get('reset_pin')
    
    if text != expected:
        await update.message.reply_text(f"❌ Angka salah. Harusnya: {expected}. Silakan ketik ulang atau /cancel.")
        return RESET_DATA_PIN
        
    await update.message.reply_text(
        "Langkah Terakhir!\n\n"
        "Data Anda akan musnah dalam hitungan detik. Jika yakin 100%, "
        "ketik kalimat sakti berikut persis seperti ini (huruf kapital semua):\n\n"
        "**RESET DATA TOKO**\n\n"
        "_(Ketik /cancel jika ragu)_",
        parse_mode='Markdown'
    )
    return RESET_DATA_CONFIRM

async def execute_reset_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text != "RESET DATA TOKO":
        await update.message.reply_text("❌ Kalimat salah. Ketik RESET DATA TOKO atau /cancel.")
        return RESET_DATA_CONFIRM
        
    access = get_user_access(update.effective_user.id)
    if not access or access['role'] != 'owner':
        return ConversationHandler.END
        
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # WIPE EVERYTHING EXCEPT businesses
        cursor.execute("DELETE FROM inventory_transactions WHERE product_id IN (SELECT id FROM products WHERE business_id = ?)", (b_id,))
        cursor.execute("DELETE FROM sale_items WHERE sale_id IN (SELECT id FROM sales WHERE business_id = ?)", (b_id,))
        cursor.execute("DELETE FROM debt_transactions WHERE debtor_id IN (SELECT id FROM debtors WHERE business_id = ?)", (b_id,))
        
        cursor.execute("DELETE FROM products WHERE business_id = ?", (b_id,))
        cursor.execute("DELETE FROM sales WHERE business_id = ?", (b_id,))
        cursor.execute("DELETE FROM debtors WHERE business_id = ?", (b_id,))
        cursor.execute("DELETE FROM customers WHERE business_id = ?", (b_id,))
        cursor.execute("DELETE FROM staff WHERE business_id = ?", (b_id,))
        cursor.execute("DELETE FROM expenses WHERE business_id = ?", (b_id,))
        
        conn.commit()
        
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data="menu_main")]]
    await update.message.reply_text(
        "💥 *BOOOM! RESET SELESAI!* 💥\n\n"
        "Seluruh data transaksi, produk, pelanggan, kasbon, dan pegawai "
        "telah disapu bersih. Toko Anda kini kembali kosong dan suci seperti kanvas baru.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return ConversationHandler.END


# ================= HAPUS USAHA (HAPUS AKUN FATAL) =================
async def start_delete_biz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    if not access or access['role'] != 'owner':
        return ConversationHandler.END
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM businesses WHERE id = ?", (access['business_id'],))
        biz = cursor.fetchone()
        
    context.user_data['delete_expected_name'] = biz['name']
    
    await query.message.edit_text(
        f"⚠️ *PERINGATAN KERAS!* ⚠️\n\n"
        f"Tindakan ini akan **MENUTUP DAN MENGHAPUS** akun toko Anda dari KawanUsaha:\n"
        f"Nama Usaha akan dihapus beserta seluruh isinya.\n\n"
        f"Jika Anda yakin, silakan ketik ulang nama usaha Anda secara persis: *{biz['name']}*\n\n"
        f"_(Ketik /cancel untuk membatalkan)_",
        parse_mode='Markdown'
    )
    return DEL_BIZ_NAME

async def verify_biz_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    typed_name = update.message.text
    expected_name = context.user_data.get('delete_expected_name', '')
    
    if typed_name != expected_name:
        await update.message.reply_text(
            f"❌ Nama yang diketik salah.\n\n"
            f"Harusnya: *{expected_name}*\n"
            f"Kamu mengetik: {typed_name}\n\n"
            f"Silakan ketik ulang dengan benar atau ketik /cancel.",
            parse_mode='Markdown'
        )
        return DEL_BIZ_NAME
        
    await update.message.reply_text(
        "Langkah Terakhir. Anda yakin 100%?\n\n"
        "Ketik kata **confirm** untuk menutup toko secara permanen.\n\n"
        "_(Ketik /cancel jika ragu)_",
        parse_mode='Markdown'
    )
    return DEL_BIZ_CONFIRM

async def execute_delete_biz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() != "confirm":
        await update.message.reply_text("❌ Kata kunci salah. Silakan ketik **confirm** atau /cancel.", parse_mode='Markdown')
        return DEL_BIZ_CONFIRM
        
    access = get_user_access(update.effective_user.id)
    if not access or access['role'] != 'owner':
        return ConversationHandler.END
        
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventory_transactions WHERE product_id IN (SELECT id FROM products WHERE business_id = ?)", (b_id,))
        cursor.execute("DELETE FROM sale_items WHERE sale_id IN (SELECT id FROM sales WHERE business_id = ?)", (b_id,))
        cursor.execute("DELETE FROM debt_transactions WHERE debtor_id IN (SELECT id FROM debtors WHERE business_id = ?)", (b_id,))
        cursor.execute("DELETE FROM products WHERE business_id = ?", (b_id,))
        cursor.execute("DELETE FROM sales WHERE business_id = ?", (b_id,))
        cursor.execute("DELETE FROM debtors WHERE business_id = ?", (b_id,))
        cursor.execute("DELETE FROM customers WHERE business_id = ?", (b_id,))
        cursor.execute("DELETE FROM staff WHERE business_id = ?", (b_id,))
        cursor.execute("DELETE FROM expenses WHERE business_id = ?", (b_id,))
        cursor.execute("DELETE FROM businesses WHERE id = ?", (b_id,))
        conn.commit()
        
    context.user_data.clear()
    
    await update.message.reply_text(
        "✅ *TOKO BERHASIL DITUTUP.*\n\n"
        "Akun dan seluruh data Anda telah dibersihkan dari sistem KawanUsaha. "
        "Sampai jumpa lagi! (Ketik /start jika ingin membuat toko baru).",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

# ================= CANCEL =================
async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Pengaturan", callback_data="menu_pengaturan")]]
    await update.message.reply_text("❌ Operasi dibatalkan.", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

def get_settings_conversation():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_edit_biz_name, pattern="^edit_biz_name$"),
            CallbackQueryHandler(start_edit_address, pattern="^edit_biz_address$"),
            CallbackQueryHandler(start_edit_phone, pattern="^edit_biz_phone$"),
            CallbackQueryHandler(start_edit_payments, pattern="^edit_payment_methods$"),
            CallbackQueryHandler(start_reset_data, pattern="^reset_data_start$"),
            CallbackQueryHandler(start_delete_biz, pattern="^delete_biz_start$")
        ],
        states={
            EDIT_BIZ_NAME: [CommandHandler("cancel", cancel_settings), MessageHandler(filters.TEXT & ~filters.COMMAND, save_biz_name)],
            EDIT_BIZ_ADDRESS: [CommandHandler("cancel", cancel_settings), MessageHandler(filters.TEXT & ~filters.COMMAND, save_address)],
            EDIT_BIZ_PHONE: [CommandHandler("cancel", cancel_settings), MessageHandler(filters.TEXT & ~filters.COMMAND, save_phone)],
            EDIT_PAYMENT_METHODS: [CommandHandler("cancel", cancel_settings), MessageHandler(filters.TEXT & ~filters.COMMAND, save_payments)],
            RESET_DATA_STEP1: [
                CallbackQueryHandler(reset_data_generate_pin, pattern="^reset_data_step1$"),
                CommandHandler("cancel", cancel_settings),
                CallbackQueryHandler(cancel_settings, pattern="^menu_pengaturan$")
            ],
            RESET_DATA_PIN: [CommandHandler("cancel", cancel_settings), MessageHandler(filters.TEXT & ~filters.COMMAND, verify_reset_pin)],
            RESET_DATA_CONFIRM: [CommandHandler("cancel", cancel_settings), MessageHandler(filters.TEXT & ~filters.COMMAND, execute_reset_data)],
            DEL_BIZ_NAME: [CommandHandler("cancel", cancel_settings), MessageHandler(filters.TEXT & ~filters.COMMAND, verify_biz_name)],
            DEL_BIZ_CONFIRM: [CommandHandler("cancel", cancel_settings), MessageHandler(filters.TEXT & ~filters.COMMAND, execute_delete_biz)]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_settings),
            CallbackQueryHandler(cancel_settings, pattern="^cancel$")
        ]
    )
