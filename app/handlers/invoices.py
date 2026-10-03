import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database.connection import get_db_connection
from app.utils.pdf_generator import generate_invoice_pdf

async def invoices_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan 5 transaksi terakhir untuk dicetak invoice-nya."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    from app.utils.auth import get_user_access
    access = get_user_access(user_id)
    if not access or access['role'] != 'owner':
        await query.message.edit_text("⚠️ Akses ditolak. Hanya pemilik yang dapat mencetak invoice historis.")
        return
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, total_amount, created_at 
            FROM sales 
            WHERE business_id = ? 
            ORDER BY created_at DESC LIMIT 5
        """, (access['business_id'],))
        sales = cursor.fetchall()
        
    if not sales:
        keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data="menu_main")]]
        await query.message.edit_text(
            "⚠️ Belum ada transaksi penjualan tercatat.", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
        
    keyboard = []
    for s in sales:
        tanggal = s['created_at'][:16]
        total = f"Rp{int(s['total_amount']):,}".replace(',', '.')
        btn_text = f"🧾 {tanggal} | {total}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"send_invoice_{s['id']}")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data="menu_main")])
    
    await query.message.edit_text(
        "🧾 *Modul Invoice PDF*\n\nPilih transaksi (5 terakhir) yang ingin dicetak:", 
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def send_invoice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengenerate dan mengirim file PDF ke user."""
    query = update.callback_query
    await query.answer("Membuat PDF, mohon tunggu beberapa saat...")
    
    sale_id = int(query.data.split("_")[2])
    
    try:
        pdf_path = generate_invoice_pdf(sale_id)
        
        # Kirim dokumen
        with open(pdf_path, 'rb') as doc:
            await query.message.reply_document(
                document=doc,
                filename=f"Invoice_{sale_id}.pdf",
                caption=f"✅ Berikut adalah invoice PDF untuk transaksi #{sale_id}"
            )
            
        # Hapus file temporary agar server tidak penuh
        os.remove(pdf_path)
        
    except Exception as e:
        await query.message.reply_text(f"⚠️ Gagal membuat PDF: {str(e)}")
