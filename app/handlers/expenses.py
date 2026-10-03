from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from app.database.connection import get_db_connection
from app.utils.auth import get_user_access

(EXP_AMOUNT, EXP_DESC) = range(2)

async def expenses_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    if not access or access['role'] != 'owner':
        await query.message.edit_text("⚠️ Akses ditolak. Hanya pemilik yang dapat mencatat pengeluaran.")
        return
        
    keyboard = [
        [InlineKeyboardButton("💸 Catat Pengeluaran Baru", callback_data="add_expense")],
        [InlineKeyboardButton("📋 Riwayat Hari Ini", callback_data="list_expenses")],
        [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data="menu_main")]
    ]
    
    await query.message.edit_text(
        "💸 *Modul Pengeluaran*\n\nCatat pengeluaran operasional toko Anda (contoh: listrik, bahan baku, gaji).", 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='Markdown'
    )

async def list_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, amount, description, created_at 
            FROM expenses 
            WHERE business_id = ? AND DATE(created_at) = DATE('now', 'localtime')
            ORDER BY created_at DESC
        """, (b_id,))
        expenses = cursor.fetchall()
        
    if not expenses:
        keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu_pengeluaran")]]
        await query.message.edit_text("⚠️ Belum ada pengeluaran yang dicatat hari ini.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
        
    keyboard = []
    text = "📋 *Riwayat Pengeluaran Hari Ini*\n\nPilih pengeluaran yang ingin **dihapus/dibatalkan**:\n\n"
    
    for e in expenses:
        waktu = e['created_at'][11:16]
        amt_str = f"Rp{int(e['amount']):,}".replace(',', '.')
        desc = f"{waktu} | {e['description']} ({amt_str})"
        keyboard.append([InlineKeyboardButton(f"❌ Hapus: {desc}", callback_data=f"del_exp_{e['id']}")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="menu_pengeluaran")])
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def delete_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    exp_id = query.data.split("_")[2]
    access = get_user_access(update.effective_user.id)
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM expenses WHERE id = ? AND business_id = ?", (exp_id, b_id))
        conn.commit()
        
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Riwayat", callback_data="list_expenses")]]
    await query.message.edit_text("✅ Pengeluaran berhasil dihapus dan dibatalkan dari laporan.", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text("💸 Masukkan *Nominal Pengeluaran* (Hanya angka, contoh: 50000):\n\n_(Ketik /cancel untuk membatalkan)_", parse_mode='Markdown')
    return EXP_AMOUNT

async def ask_expense_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ Nominal harus angka. Masukkan nominal pengeluaran:")
        return EXP_AMOUNT
        
    context.user_data['exp_amount'] = int(update.message.text)
    await update.message.reply_text("Tulis *Keterangan/Deskripsi* pengeluaran ini:\n\n_(Ketik /cancel untuk membatalkan)_", parse_mode='Markdown')
    return EXP_DESC

async def save_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text
    amount = context.user_data['exp_amount']
    
    access = get_user_access(update.effective_user.id)
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO expenses (business_id, amount, description) VALUES (?, ?, ?)", (b_id, amount, desc))
        conn.commit()
        
    context.user_data.clear()
    
    amt_str = f"Rp{int(amount):,}".replace(',', '.')
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu_pengeluaran")]]
    await update.message.reply_text(f"✅ Pengeluaran *{desc}* sebesar *{amt_str}* berhasil dicatat!", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def cancel_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu_pengeluaran")]]
    await update.message.reply_text("❌ Pencatatan pengeluaran dibatalkan.", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

def get_expense_conversation():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_expense, pattern="^add_expense$")],
        states={
            EXP_AMOUNT: [CommandHandler("cancel", cancel_expense), MessageHandler(filters.TEXT & ~filters.COMMAND, ask_expense_desc)],
            EXP_DESC: [CommandHandler("cancel", cancel_expense), MessageHandler(filters.TEXT & ~filters.COMMAND, save_expense)]
        },
        fallbacks=[CommandHandler("cancel", cancel_expense)]
    )
