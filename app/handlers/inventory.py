from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from app.database.connection import get_db_connection
from datetime import datetime

(STOCK_QTY,) = range(1)

async def manage_stock_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan daftar produk untuk dikelola stoknya."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    from app.utils.auth import get_user_access
    access = get_user_access(user_id)
    if not access or access['role'] != 'owner':
        await query.message.edit_text("⚠️ Akses ditolak.")
        return
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, stock FROM products WHERE business_id = ?", (access['business_id'],))
        products = cursor.fetchall()

    if not products:
        keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu_produk")]]
        await query.message.edit_text("⚠️ Anda belum memiliki produk terdaftar.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(f"📦 {p['name']} (Stok: {p['stock']})", callback_data=f"stock_detail_{p['id']}")])
    keyboard.append([InlineKeyboardButton("⬅️ Kembali ke Menu Produk", callback_data="menu_produk")])
    
    await query.message.edit_text(
        "📦 *Kelola Stok Produk*\n\nPilih produk yang ingin kamu atur stoknya:", 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='Markdown'
    )

async def stock_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan detail stok beserta riwayat transaksi."""
    query = update.callback_query
    await query.answer()
    prod_id = query.data.split("_")[2]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, stock FROM products WHERE id = ?", (prod_id,))
        p = cursor.fetchone()
        
        # Ambil 3 riwayat terakhir
        cursor.execute(
            "SELECT type, quantity, created_at FROM inventory_transactions WHERE product_id = ? ORDER BY created_at DESC LIMIT 3", 
            (prod_id,)
        )
        history = cursor.fetchall()
        
    text = f"📦 *{p['name']}*\n📊 Stok Saat Ini: *{p['stock']}*\n\n*🕒 Riwayat Terakhir:*\n"
    if not history:
        text += "_Belum ada riwayat transaksi_\n"
    else:
        for h in history:
            tipe = "Masuk" if h['type'] == 'IN' else "Keluar"
            simbol = "➕" if h['type'] == 'IN' else "➖"
            waktu = h['created_at'][:16]
            text += f"{simbol} {h['quantity']} ({tipe}) | {waktu}\n"
            
    text += "\nSilakan pilih tindakan:"
            
    keyboard = [
        [InlineKeyboardButton("➕ Stok Masuk", callback_data=f"stock_in_{p['id']}"),
         InlineKeyboardButton("➖ Stok Keluar", callback_data=f"stock_out_{p['id']}")],
        [InlineKeyboardButton("⬅️ Kembali ke Daftar", callback_data="manage_stock_list")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# --- Alur Penyesuaian Stok ---
async def start_stock_adj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data.split("_")[1] # 'in' atau 'out'
    prod_id = query.data.split("_")[2]
    
    context.user_data['stock_adj_id'] = prod_id
    context.user_data['stock_adj_action'] = 'IN' if action == 'in' else 'OUT'
    
    tipe_teks = "TAMBAH (Stok Masuk)" if action == 'in' else "KURANGI (Stok Keluar)"
    simbol = "➕" if action == 'in' else "➖"
    
    await query.message.edit_text(
        f"{simbol} Masukkan jumlah barang yang akan di *{tipe_teks}* (hanya angka):\n\n_(Ketik /cancel untuk membatalkan)_", 
        parse_mode='Markdown'
    )
    return STOCK_QTY

async def save_stock_adj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qty_text = update.message.text
    if not qty_text.isdigit():
        await update.message.reply_text("⚠️ Harus berupa angka tanpa simbol. Masukkan kembali:\n\n_(Ketik /cancel untuk membatalkan)_")
        return STOCK_QTY
        
    qty = int(qty_text)
    if qty <= 0:
        await update.message.reply_text("⚠️ Jumlah harus lebih dari 0. Masukkan kembali:")
        return STOCK_QTY
        
    prod_id = context.user_data['stock_adj_id']
    action = context.user_data['stock_adj_action']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, stock FROM products WHERE id = ?", (prod_id,))
        p = cursor.fetchone()
        
        # Validasi stok keluar
        if action == 'OUT' and qty > p['stock']:
            await update.message.reply_text(f"⚠️ Stok tidak mencukupi! Stok saat ini hanya {p['stock']} pcs.\nSilakan masukkan jumlah yang lebih kecil:")
            return STOCK_QTY
        
        new_stock = p['stock'] + qty if action == 'IN' else p['stock'] - qty
        
        # 1. Update tabel products
        cursor.execute("UPDATE products SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_stock, prod_id))
        
        # 2. Insert tabel inventory_transactions
        cursor.execute("INSERT INTO inventory_transactions (product_id, type, quantity, notes) VALUES (?, ?, ?, ?)",
                       (prod_id, action, qty, "Manual adjustment via bot"))
        conn.commit()
        
    context.user_data.clear()
    
    warning = ""
    if action == 'OUT' and new_stock <= 5:
        warning = f"\n\n⚠️ *PERINGATAN:* Stok menipis! Sisa stok hanya {new_stock} pcs."
    
    simbol = "➕" if action == 'IN' else "➖"
    success_text = f"✅ *Stok berhasil diperbarui!*\n\n📦 {p['name']}\n{simbol} Perubahan: {qty}\n📊 Sisa Stok: *{new_stock}*{warning}"
    
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Kelola Stok", callback_data="manage_stock_list")]]
    await update.message.reply_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def cancel_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Kelola Stok", callback_data="manage_stock_list")]]
    await update.message.reply_text("❌ Penyesuaian stok dibatalkan.", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

def get_stock_conversation():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_stock_adj, pattern="^stock_(in|out)_")],
        states={
            STOCK_QTY: [
                CommandHandler("cancel", cancel_stock),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_stock_adj)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_stock)]
    )
