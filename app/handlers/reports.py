from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.utils.auth import get_user_access
from app.utils.reports import get_report_text

async def reports_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    if not access or access['role'] != 'owner':
        await query.message.edit_text("⚠️ Akses ditolak. Hanya pemilik yang dapat melihat laporan.")
        return
        
    keyboard = [
        [InlineKeyboardButton("📅 Laporan Hari Ini", callback_data="report_today")],
        [InlineKeyboardButton("🗓 Laporan 7 Hari Terakhir", callback_data="report_7d")],
        [InlineKeyboardButton("📆 Laporan Bulan Ini", callback_data="report_month")],
        [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data="menu_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text("📊 *Laporan Penjualan & Keuangan*\n\nPilih rentang waktu laporan yang ingin dilihat:\n\n_(Catatan: Hari berjalan dihitung mulai jam 06:00 pagi)_", reply_markup=reply_markup, parse_mode='Markdown')

async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    period = query.data.split("_")[1]
    
    access = get_user_access(update.effective_user.id)
    b_id = access['business_id']
    
    text = get_report_text(b_id, period)
            
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu Laporan", callback_data="menu_laporan")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
