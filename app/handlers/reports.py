from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database.connection import get_db_connection
from app.utils.auth import get_user_access

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
    
    await query.message.edit_text("📊 *Laporan Penjualan & Keuangan*\n\nPilih rentang waktu laporan yang ingin dilihat:", reply_markup=reply_markup, parse_mode='Markdown')

async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    period = query.data.split("_")[1]
    
    access = get_user_access(update.effective_user.id)
    b_id = access['business_id']
    
    time_modifier = ""
    title = ""
    if period == "today":
        time_modifier = "DATE(created_at) = DATE('now', 'localtime')"
        title = "HARI INI"
    elif period == "7d":
        time_modifier = "DATE(created_at) >= DATE('now', '-7 days', 'localtime')"
        title = "7 HARI TERAKHIR"
    elif period == "month":
        time_modifier = "strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now', 'localtime')"
        title = "BULAN INI"
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Omzet dari Penjualan Normal
        cursor.execute(f"SELECT COUNT(id) as trx_count, SUM(total_amount) as revenue FROM sales WHERE business_id = ? AND {time_modifier}", (b_id,))
        sales_data = cursor.fetchone()
        
        # 1.1 Omzet dari Pelunasan Kasbon
        kasbon_mod = time_modifier.replace('created_at', 'dt.created_at')
        cursor.execute(f'''
            SELECT SUM(dt.amount) as paid
            FROM debt_transactions dt
            JOIN debtors d ON dt.debtor_id = d.id
            WHERE d.business_id = ? AND dt.type = 'PAYMENT' AND {kasbon_mod}
        ''', (b_id,))
        kasbon_data = cursor.fetchone()
        
        trx_count = sales_data['trx_count'] or 0
        sales_rev = sales_data['revenue'] or 0
        kasbon_rev = kasbon_data['paid'] or 0
        revenue = sales_rev + kasbon_rev
        
        # 1.5. Breakdown per Pembayaran
        cursor.execute(f"SELECT payment_method, SUM(total_amount) as pm_total FROM sales WHERE business_id = ? AND {time_modifier} GROUP BY payment_method", (b_id,))
        payment_breakdowns = cursor.fetchall()
        
        # 2. Item Terjual & Top Produk
        cursor.execute(f'''
            SELECT p.name, SUM(si.quantity) as qty_sold 
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON si.product_id = p.id
            WHERE s.business_id = ? AND {time_modifier.replace('created_at', 's.created_at')}
            GROUP BY p.id
            ORDER BY qty_sold DESC
        ''', (b_id,))
        top_items = cursor.fetchall()
        
        total_items = sum([item['qty_sold'] for item in top_items])
        
        # 3. Pengeluaran
        cursor.execute(f"SELECT SUM(amount) as expenses FROM expenses WHERE business_id = ? AND {time_modifier}", (b_id,))
        exp_data = cursor.fetchone()
        total_expenses = exp_data['expenses'] or 0
        
        # 4. Laba Bersih
        net_profit = revenue - total_expenses
        
    revenue_str = f"Rp{int(revenue):,}".replace(',', '.')
    expenses_str = f"Rp{int(total_expenses):,}".replace(',', '.')
    net_str = f"Rp{int(net_profit):,}".replace(',', '.')
    
    text = f"📊 *LAPORAN {title}*\n\n"
    text += f"Total Transaksi: {trx_count}\n"
    text += f"Item Terjual: {total_items} pcs\n"
    text += f"📈 Total Omzet: *{revenue_str}*\n"
    
    if payment_breakdowns or kasbon_rev > 0:
        text += "   *Rincian Masuk:*\n"
        for pb in payment_breakdowns:
            pm_name = pb['payment_method'] or "Tunai"
            pm_val = f"Rp{int(pb['pm_total']):,}".replace(',', '.')
            text += f"   💳 {pm_name}: {pm_val}\n"
        if kasbon_rev > 0:
            kb_val = f"Rp{int(kasbon_rev):,}".replace(',', '.')
            text += f"   💰 Pelunasan Kasbon: {kb_val}\n"
            
    text += f"\n📉 Pengeluaran: *{expenses_str}*\n"
    text += f"------------------------\n"
    text += f"💵 LABA BERSIH: *{net_str}*\n\n"
    
    if top_items:
        text += "*Top 3 Produk Terlaris:*\n"
        for i, item in enumerate(top_items[:3], 1):
            text += f"{i}. {item['name']} ({item['qty_sold']} pcs)\n"
            
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu Laporan", callback_data="menu_laporan")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
