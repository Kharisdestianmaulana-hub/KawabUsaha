import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from app.database.connection import get_db_connection

(CUST_NAME, CUST_PHONE) = range(2)

async def customers_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📋 Daftar Pelanggan", callback_data="list_customers"),
         InlineKeyboardButton("➕ Tambah Pelanggan", callback_data="add_customer")],
        [InlineKeyboardButton("⚙️ Kelola Pelanggan", callback_data="manage_customers")],
        [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data="menu_main")]
    ]
    
    await query.message.edit_text(
        "👥 *Manajemen Pelanggan*\n\nSilakan pilih aksi yang ingin dilakukan:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# --- ALUR TAMBAH PELANGGAN ---
async def start_add_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "👤 Masukkan *Nama Pelanggan*:\n\n_(Ketik /cancel untuk membatalkan)_", 
        parse_mode='Markdown'
    )
    return CUST_NAME

async def ask_cust_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cust_name'] = update.message.text
    await update.message.reply_text(
        "Sip! Masukkan *Nomor WhatsApp / HP* pelanggan (misal: 081234...):\n"
        "Atau ketik '-' jika tidak ada.\n\n_(Ketik /cancel untuk membatalkan)_"
    )
    return CUST_PHONE

async def ask_cust_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    name = context.user_data['cust_name']
    user_id = update.effective_user.id
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        from app.utils.auth import get_user_access
        access = get_user_access(user_id)
        if not access:
            return
        b_id = access["business_id"]
        
        
        cursor.execute(
            "INSERT INTO customers (business_id, name, phone) VALUES (?, ?, ?)",
            (b_id, name, phone)
        )
        conn.commit()
        
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu Pelanggan", callback_data="menu_pelanggan")]]
    await update.message.reply_text(
        f"✅ Pelanggan *{name}* berhasil ditambahkan!", 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='Markdown'
    )
    return ConversationHandler.END
    
async def cancel_cust(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu Pelanggan", callback_data="menu_pelanggan")]]
    await update.message.reply_text("❌ Proses dibatalkan.", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

def get_customer_conversation():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_customer, pattern="^add_customer$")],
        states={
            CUST_NAME: [CommandHandler("cancel", cancel_cust), MessageHandler(filters.TEXT & ~filters.COMMAND, ask_cust_name)],
            CUST_PHONE: [CommandHandler("cancel", cancel_cust), MessageHandler(filters.TEXT & ~filters.COMMAND, ask_cust_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel_cust)]
    )

# --- DAFTAR & KELOLA PELANGGAN ---
async def list_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        from app.utils.auth import get_user_access
        access = get_user_access(user_id)
        if not access:
            return
        b_id = access["business_id"]
        
        cursor.execute("SELECT name, phone FROM customers WHERE business_id = ?", (b_id,))
        customers = cursor.fetchall()
        
    if not customers:
        text = "👥 *Daftar Pelanggan*\n\nBelum ada pelanggan terdaftar."
    else:
        text = "👥 *Daftar Pelanggan*\n\n"
        for idx, c in enumerate(customers, 1):
            phone = c['phone'] if c['phone'] != '-' else "Tidak ada No. HP"
            text += f"{idx}. *{c['name']}* ({phone})\n"
            
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu_pelanggan")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def manage_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        from app.utils.auth import get_user_access
        access = get_user_access(user_id)
        if not access:
            return
        b_id = access["business_id"]
        
        cursor.execute("SELECT id, name FROM customers WHERE business_id = ?", (b_id,))
        customers = cursor.fetchall()
        
    if not customers:
        keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu_pelanggan")]]
        await query.message.edit_text("⚠️ Anda belum memiliki pelanggan terdaftar.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
        
    keyboard = []
    for c in customers:
        keyboard.append([InlineKeyboardButton(f"👤 {c['name']}", callback_data=f"cust_detail_{c['id']}")])
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="menu_pelanggan")])
    
    await query.message.edit_text(
        "⚙️ *Kelola Pelanggan*\n\nPilih pelanggan untuk melihat profil/menghapus:", 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='Markdown'
    )

async def customer_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cust_id = query.data.split("_")[2]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, phone FROM customers WHERE id = ?", (cust_id,))
        c = cursor.fetchone()
        
        # Histori transaksi pelanggan
        try:
            cursor.execute("SELECT total_amount, created_at FROM sales WHERE customer_id = ? ORDER BY created_at DESC LIMIT 3", (cust_id,))
            history = cursor.fetchall()
        except sqlite3.OperationalError:
            history = []
            
    text = f"👤 *Profil Pelanggan*\n\nNama: *{c['name']}*\nNo. HP: {c['phone']}\n\n*🕒 Riwayat Belanja Terakhir:*\n"
    if not history:
        text += "_Belum ada transaksi tercatat untuk pelanggan ini._"
    else:
        for h in history:
            omzet = f"Rp{int(h['total_amount']):,}".replace(',', '.')
            waktu = h['created_at'][:16]
            text += f"🛍 {omzet} | {waktu}\n"
            
    keyboard = [
        [InlineKeyboardButton("❌ Hapus Pelanggan", callback_data=f"delete_cust_{c['id']}")],
        [InlineKeyboardButton("⬅️ Kembali", callback_data="manage_customers")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def delete_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cust_id = query.data.split("_")[2]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM customers WHERE id = ?", (cust_id,))
        conn.commit()
        
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Kelola Pelanggan", callback_data="manage_customers")]]
    await query.message.edit_text("✅ Pelanggan berhasil dihapus.", reply_markup=InlineKeyboardMarkup(keyboard))
