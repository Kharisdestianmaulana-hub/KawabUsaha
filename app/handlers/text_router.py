import logging
import re
from telegram import Update
from telegram.ext import ContextTypes
from app.database.connection import get_db_connection
from app.utils.auth import get_user_access
from app.utils.reports import get_report_text

logger = logging.getLogger(__name__)

def extract_number(text: str) -> int:
    """Mengambil angka dari teks, mendukung format '50rb' atau '50000'."""
    text = text.lower().replace('.', '').replace(',', '')
    if 'rb' in text or 'ribu' in text:
        match = re.search(r'(\d+)\s*(rb|ribu)', text)
        if match:
            return int(match.group(1)) * 1000
    
    match = re.search(r'(\d+)', text)
    return int(match.group(1)) if match else 0

async def handle_global_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user_id = update.effective_user.id
    
    access = get_user_access(user_id)
    if not access:
        await update.message.reply_text("Silakan ketik /start untuk mendaftar terlebih dahulu.")
        return
        
    b_id = access['business_id']
    role = access['role']
    
    # ----------------------------------------------------
    # 1. FITUR LAPORAN & OMZET
    # ----------------------------------------------------
    if any(k in text for k in ["laporan", "omzet", "rekap", "penghasilan", "laba"]):
        if role != 'owner':
            await update.message.reply_text("⚠️ Hanya pemilik yang dapat melihat laporan.")
            return
            
        period = "today"
        if any(k in text for k in ["7 hari", "minggu", "pekan"]):
            period = "7d"
        elif any(k in text for k in ["bulan", "month"]):
            period = "month"
            
        report_text = get_report_text(b_id, period)
        await update.message.reply_text(report_text, parse_mode='Markdown')
        return

    # ----------------------------------------------------
    # 2. FITUR CEK STOK / DAFTAR PRODUK
    # ----------------------------------------------------
    if any(k in text for k in ["stok", "sisa barang", "daftar produk", "list produk", "lihat produk"]):
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

    # ----------------------------------------------------
    # 3. FITUR KASBON (CATAT & BAYAR)
    # Contoh: "kasbon budi 50rb", "utang joko 100000"
    # Contoh bayar: "budi bayar kasbon 50rb", "lunasin utang joko 20rb"
    # ----------------------------------------------------
    if any(k in text for k in ["kasbon", "utang", "hutang", "bon"]):
        is_payment = any(k in text for k in ["bayar", "lunas", "cicil"])
        nominal = extract_number(text)
        
        # Ekstrak nama (asumsi kata setelah kasbon/utang atau sebelum bayar)
        # Cara kasar tapi efektif: ambil kata-kata selain angka dan keyword
        words = text.split()
        keywords = ["kasbon", "utang", "hutang", "bon", "bayar", "lunas", "cicil", "rb", "ribu", "buat", "atas", "nama", "si"]
        name_words = [w for w in words if w not in keywords and not re.search(r'\d', w)]
        
        if nominal > 0 and name_words:
            debtor_name = name_words[0].capitalize()
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM debtors WHERE business_id = ? AND name LIKE ?", (b_id, f"%{debtor_name}%"))
                debtor = cursor.fetchone()
                
                if not debtor:
                    # Buat penghutang baru
                    cursor.execute("INSERT INTO debtors (business_id, name) VALUES (?, ?)", (b_id, debtor_name))
                    debtor_id = cursor.lastrowid
                else:
                    debtor_id = debtor['id']
                    
                type_trx = 'PAYMENT' if is_payment else 'DEBT'
                cursor.execute("INSERT INTO debt_transactions (debtor_id, type, amount, notes) VALUES (?, ?, ?, ?)",
                               (debtor_id, type_trx, nominal, text))
                conn.commit()
                
            aksi = "Pembayaran/Pelunasan" if is_payment else "Catatan"
            await update.message.reply_text(f"✅ *{aksi} Kasbon Berhasil!*\n\nAtas Nama: {debtor_name}\nNominal: Rp{nominal:,}".replace(',', '.'), parse_mode='Markdown')
            return

    # ----------------------------------------------------
    # 4. FITUR PENGELUARAN
    # Contoh: "beli galon 20rb", "bayar listrik 150000", "pengeluaran sapu 15 ribu"
    # ----------------------------------------------------
    if any(k in text for k in ["pengeluaran", "beli ", "bayar ", "biaya "]) and not any(k in text for k in ["kasbon", "utang", "hutang"]):
        nominal = extract_number(text)
        if nominal > 0:
            notes = text.capitalize()
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO expenses (business_id, amount, description) VALUES (?, ?, ?)",
                               (b_id, nominal, notes))
                conn.commit()
            await update.message.reply_text(f"💸 *Pengeluaran Dicatat*\n\nKeterangan: {notes}\nNominal: Rp{nominal:,}".replace(',', '.'), parse_mode='Markdown')
            return

    # ----------------------------------------------------
    # 5. JIKA TIDAK MENGERTI
    # ----------------------------------------------------
    await update.message.reply_text(
        "Maaf, saya kurang mengerti maksud kalimatmu. 😅\n\n"
        "*Coba ketik dengan gaya seperti ini:*\n"
        "📊 _'Tolong cek laporan hari ini'_\n"
        "📦 _'Lihat sisa stok dong'_\n"
        "📓 _'Kasbon si budi 50rb'_\n"
        "💸 _'Beli galon 20000'_\n"
        "💰 _'Budi bayar utang 50rb'_",
        parse_mode='Markdown'
    )
