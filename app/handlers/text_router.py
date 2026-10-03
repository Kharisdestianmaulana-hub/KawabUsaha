import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.utils.auth import get_user_access
from app.utils.reports import get_report_text

logger = logging.getLogger(__name__)

async def handle_global_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Menangkap semua ketikan bebas dari pengguna dan mengarahkannya 
    ke fitur yang tepat menggunakan logika pencarian kata kunci (Keyword Matching).
    """
    text = update.message.text.lower()
    user_id = update.effective_user.id
    
    # Pastikan user punya akses
    access = get_user_access(user_id)
    if not access:
        await update.message.reply_text("Silakan ketik /start untuk mendaftar terlebih dahulu.")
        return
        
    b_id = access['business_id']
    role = access['role']
    
    # 1. FITUR LAPORAN
    if any(keyword in text for keyword in ["laporan", "omzet", "rekap"]):
        if role != 'owner':
            await update.message.reply_text("⚠️ Hanya pemilik yang dapat melihat laporan.")
            return
            
        period = "today"
        if "7 hari" in text or "minggu" in text:
            period = "7d"
        elif "bulan" in text:
            period = "month"
            
        report_text = get_report_text(b_id, period)
        await update.message.reply_text(report_text, parse_mode='Markdown')
        return

    # TODO: Tambahkan fitur lain seperti Penjualan, Kasbon, Produk, dll.
    
    # Jika tidak ada keyword yang cocok
    await update.message.reply_text(
        "Maaf, saya belum mengerti maksudmu. 😅\n\n"
        "Coba gunakan kata kunci seperti:\n"
        "- 'laporan hari ini'\n"
        "- 'laporan bulan ini'\n"
        "Atau gunakan menu tombol dengan mengetik /start."
    )

    # 2. FITUR CEK STOK
    if any(keyword in text for keyword in ["stok", "produk"]):
        from app.database.connection import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, stock, price FROM products WHERE business_id = ?", (b_id,))
            products = cursor.fetchall()
            
        if not products:
            await update.message.reply_text("📦 Belum ada produk yang terdaftar.")
            return
            
        msg = "📦 *Daftar Stok Produk*\n\n"
        for p in products:
            msg += f"- {p['name']}: {p['stock']} (Rp{int(p['price']):,})\n"
        await update.message.reply_text(msg, parse_mode='Markdown')
        return

