from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from app.database.connection import get_db_connection
from app.utils.auth import get_user_access

(DEBT_NAME, DEBT_AMOUNT, DEBT_NOTES, PAY_AMOUNT) = range(4)

async def kasbon_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    if not access:
        await query.message.edit_text("⚠️ Akses ditolak.")
        return
        
    text = (
        "📓 *BUKU KASBON (Piutang)*\n\n"
        "Menu ini digunakan untuk mencatat pelanggan yang berhutang (kasbon). "
        "Uang pelunasan akan otomatis dihitung sebagai Omzet di hari pembayaran.\n\n"
        "Silakan pilih aksi:"
    )
    
    keyboard = [
        [InlineKeyboardButton("➕ Tambah Kasbon Baru", callback_data="add_kasbon")],
        [InlineKeyboardButton("👥 Kelola Orang (Tagih)", callback_data="manage_debtors")],
        [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data="menu_main")]
    ]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ================= TAMBAH KASBON =================
async def start_add_kasbon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "➕ *Tambah Kasbon Baru*\n\n"
        "Masukkan *Nama Orang* yang berhutang:\n\n"
        "_(Ketik /cancel untuk membatalkan)_",
        parse_mode='Markdown'
    )
    return DEBT_NAME

async def ask_debt_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['debt_name'] = update.message.text
    
    await update.message.reply_text(
        f"Nama: *{context.user_data['debt_name']}*\n\n"
        f"Masukkan *Nominal Kasbon* (hanya angka, misal: 25000):\n\n"
        f"_(Ketik /cancel untuk membatalkan)_",
        parse_mode='Markdown'
    )
    return DEBT_AMOUNT

async def ask_debt_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amt_text = update.message.text
    if not amt_text.isdigit():
        await update.message.reply_text("⚠️ Harus berupa angka. Masukkan nominal kasbon:")
        return DEBT_AMOUNT
        
    context.user_data['debt_amount'] = int(amt_text)
    
    await update.message.reply_text(
        f"Terakhir, ketik *Keterangan* (contoh: ngutang rokok, sembako, dsb):\n\n"
        f"_(Ketik /cancel untuk membatalkan)_",
        parse_mode='Markdown'
    )
    return DEBT_NOTES

async def save_kasbon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes = update.message.text
    name = context.user_data['debt_name']
    amount = context.user_data['debt_amount']
    
    access = get_user_access(update.effective_user.id)
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Cek apakah nama ini sudah ada di daftar debtor sebelumnya (case-insensitive)
        cursor.execute("SELECT id FROM debtors WHERE business_id = ? AND LOWER(name) = LOWER(?)", (b_id, name))
        debtor = cursor.fetchone()
        
        if debtor:
            debtor_id = debtor['id']
        else:
            cursor.execute("INSERT INTO debtors (business_id, name) VALUES (?, ?)", (b_id, name))
            debtor_id = cursor.lastrowid
            
        # Simpan transaksinya
        cursor.execute(
            "INSERT INTO debt_transactions (debtor_id, type, amount, notes) VALUES (?, 'DEBT', ?, ?)",
            (debtor_id, amount, notes)
        )
        conn.commit()
        
    context.user_data.clear()
    
    amt_str = f"Rp{int(amount):,}".replace(',', '.')
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Buku Kasbon", callback_data="menu_kasbon")]]
    await update.message.reply_text(
        f"✅ *Kasbon Berhasil Dicatat!*\n\n"
        f"👤 Nama: {name}\n"
        f"💰 Jumlah: {amt_str}\n"
        f"📝 Keterangan: {notes}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return ConversationHandler.END

# ================= KELOLA ORANG (TAGIH) =================
async def list_debtors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Ambil semua penghutang dan hitung sisa hutang mereka
        cursor.execute("""
            SELECT d.id, d.name, 
                   SUM(CASE WHEN dt.type='DEBT' THEN dt.amount ELSE -dt.amount END) as remaining_debt
            FROM debtors d
            JOIN debt_transactions dt ON d.id = dt.debtor_id
            WHERE d.business_id = ?
            GROUP BY d.id
            HAVING remaining_debt > 0
            ORDER BY d.name
        """, (b_id,))
        debtors = cursor.fetchall()
        
    if not debtors:
        keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu_kasbon")]]
        await query.message.edit_text(
            "🎉 Wah, bersih! Saat ini tidak ada pelanggan yang menunggak kasbon.", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
        
    text = "👥 *Daftar Penghutang*\n\nPilih nama untuk melihat detail atau mencatat pelunasan:\n"
    keyboard = []
    
    for d in debtors:
        rem_str = f"Rp{int(d['remaining_debt']):,}".replace(',', '.')
        btn_text = f"👤 {d['name']} ({rem_str})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"debtor_{d['id']}")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="menu_kasbon")])
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def debtor_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    debtor_id = query.data.split("_")[1]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM debtors WHERE id = ?", (debtor_id,))
        debtor = cursor.fetchone()
        
        cursor.execute("""
            SELECT type, amount, notes, created_at 
            FROM debt_transactions 
            WHERE debtor_id = ? 
            ORDER BY created_at DESC LIMIT 5
        """, (debtor_id,))
        history = cursor.fetchall()
        
        cursor.execute("""
            SELECT SUM(CASE WHEN type='DEBT' THEN amount ELSE -amount END) as remaining
            FROM debt_transactions WHERE debtor_id = ?
        """, (debtor_id,))
        rem = cursor.fetchone()['remaining']
        
    if not debtor:
        return
        
    rem_str = f"Rp{int(rem):,}".replace(',', '.')
    
    text = f"👤 *Detail Kasbon: {debtor['name']}*\n💰 *Sisa Tunggakan:* {rem_str}\n\n*5 Riwayat Terakhir:*\n"
    
    for h in history:
        amt = f"Rp{int(h['amount']):,}".replace(',', '.')
        date_str = h['created_at'][5:16]
        if h['type'] == 'DEBT':
            text += f"🔴 [{date_str}] Ngutang: {amt} ({h['notes']})\n"
        else:
            text += f"🟢 [{date_str}] Bayar: {amt}\n"
            
    keyboard = [
        [InlineKeyboardButton("💰 Terima Pelunasan", callback_data=f"pay_debt_{debtor_id}")],
        [InlineKeyboardButton("⬅️ Kembali ke Daftar", callback_data="manage_debtors")]
    ]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ================= TERIMA PELUNASAN =================
async def start_pay_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    debtor_id = query.data.split("_")[2]
    context.user_data['pay_debtor_id'] = debtor_id
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM debtors WHERE id = ?", (debtor_id,))
        name = cursor.fetchone()['name']
        
        cursor.execute("""
            SELECT SUM(CASE WHEN type='DEBT' THEN amount ELSE -amount END) as remaining
            FROM debt_transactions WHERE debtor_id = ?
        """, (debtor_id,))
        rem = cursor.fetchone()['remaining']
        
    rem_str = f"Rp{int(rem):,}".replace(',', '.')
    context.user_data['pay_debtor_rem'] = int(rem)
    
    await query.message.edit_text(
        f"💰 *Pelunasan: {name}*\n"
        f"Total Tunggakan: {rem_str}\n\n"
        f"Masukkan nominal uang yang dibayarkan sekarang (hanya angka):\n"
        f"_(Ketik /cancel untuk membatalkan)_",
        parse_mode='Markdown'
    )
    return PAY_AMOUNT

async def save_pay_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amt_text = update.message.text
    if not amt_text.isdigit():
        await update.message.reply_text("⚠️ Harus berupa angka. Masukkan nominal uang:")
        return PAY_AMOUNT
        
    paid = int(amt_text)
    rem = context.user_data['pay_debtor_rem']
    debtor_id = context.user_data['pay_debtor_id']
    
    if paid > rem:
        await update.message.reply_text(f"⚠️ Pembayaran lebih besar dari hutang (Sisa: Rp{rem}). Masukkan nominal yang benar:")
        return PAY_AMOUNT
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO debt_transactions (debtor_id, type, amount, notes) VALUES (?, 'PAYMENT', ?, 'Pelunasan Kasbon')",
            (debtor_id, paid)
        )
        conn.commit()
        
    context.user_data.clear()
    
    paid_str = f"Rp{int(paid):,}".replace(',', '.')
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Buku Kasbon", callback_data="menu_kasbon")]]
    
    await update.message.reply_text(
        f"✅ *Pelunasan Berhasil Diterima!*\n\n"
        f"Nominal {paid_str} telah dicatat dan **Otomatis Masuk ke Laporan Omzet Hari Ini**.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return ConversationHandler.END

# ================= CANCEL =================
async def cancel_kasbon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Buku Kasbon", callback_data="menu_kasbon")]]
    await update.message.reply_text("❌ Aksi dibatalkan.", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

def get_kasbon_conversation():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_kasbon, pattern="^add_kasbon$"),
            CallbackQueryHandler(start_pay_debt, pattern="^pay_debt_")
        ],
        states={
            DEBT_NAME: [CommandHandler("cancel", cancel_kasbon), MessageHandler(filters.TEXT & ~filters.COMMAND, ask_debt_amount)],
            DEBT_AMOUNT: [CommandHandler("cancel", cancel_kasbon), MessageHandler(filters.TEXT & ~filters.COMMAND, ask_debt_notes)],
            DEBT_NOTES: [CommandHandler("cancel", cancel_kasbon), MessageHandler(filters.TEXT & ~filters.COMMAND, save_kasbon)],
            PAY_AMOUNT: [CommandHandler("cancel", cancel_kasbon), MessageHandler(filters.TEXT & ~filters.COMMAND, save_pay_debt)]
        },
        fallbacks=[CommandHandler("cancel", cancel_kasbon)]
    )
