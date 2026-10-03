import logging
import re
import uuid
from telegram import Update
from telegram.ext import ContextTypes
from app.database.connection import get_db_connection
from app.utils.auth import get_user_access
from app.utils.reports import get_report_text

logger = logging.getLogger(__name__)

def extract_number(text: str) -> int:
    """Mengambil angka pertama dari teks, mendukung format '50rb' atau '50000'."""
    text = text.lower().replace('.', '').replace(',', '')
    if 'rb' in text or 'ribu' in text:
        match = re.search(r'(\d+)\s*(rb|ribu)', text)
        if match:
            return int(match.group(1)) * 1000
    
    match = re.search(r'(\d+)', text)
    return int(match.group(1)) if match else 0

def extract_all_numbers(text: str) -> list:
    """Mengambil semua angka dari teks, mengkonversi rb/ribu jika relevan."""
    text = text.lower().replace('.', '').replace(',', '')
    
    # Pre-process 'rb'/'ribu' attached to numbers
    text = re.sub(r'(\d+)\s*(rb|ribu)', lambda m: str(int(m.group(1)) * 1000), text)
    
    matches = re.findall(r'\d+', text)
    return [int(m) for m in matches]

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
    if any(k in text for k in ["stok", "sisa barang", "daftar produk", "list produk", "lihat produk"]) and "tambah" not in text:
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
    # 3. FITUR TAMBAH PRODUK BARU
    # Contoh: "tambah produk sabun mandi harga 5000 stok 20"
    # ----------------------------------------------------
    if "tambah produk" in text or "produk baru" in text:
        if role != 'owner':
            await update.message.reply_text("⚠️ Hanya pemilik yang dapat menambah produk.")
            return
            
        numbers = extract_all_numbers(text)
        if len(numbers) >= 2:
            # Asumsi angka pertama harga, angka kedua stok
            price, stock = numbers[0], numbers[1]
            
            # Ekstrak nama produk (hapus kata kunci dan angka)
            words = text.split()
            ignore_words = ["tambah", "produk", "baru", "harga", "stok", "rp", "ribu", "rb"]
            name_words = [w for w in words if w not in ignore_words and not re.search(r'\d', w)]
            prod_name = " ".join(name_words).title()
            
            if prod_name:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO products (business_id, name, price, stock) VALUES (?, ?, ?, ?)",
                                   (b_id, prod_name, price, stock))
                    conn.commit()
                await update.message.reply_text(f"✅ *Produk Berhasil Ditambahkan*\n\nNama: {prod_name}\nHarga: Rp{price:,}\nStok: {stock}".replace(',', '.'), parse_mode='Markdown')
                return

    # ----------------------------------------------------
    # 4. FITUR PENJUALAN (SALES)
    # Contoh: "jual 2 es kopi", "laku nasi goreng 3 porsi"
    # ----------------------------------------------------
    if any(k in text for k in ["jual ", "laku ", "terjual ", "pesanan "]) and not "produk" in text:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, price, stock FROM products WHERE business_id = ?", (b_id,))
            products = cursor.fetchall()
            
        # Cari produk mana yang disebut
        matched_product = None
        for p in products:
            if p['name'].lower() in text:
                matched_product = p
                break
                
        if matched_product:
            qty = extract_number(text)
            if qty == 0: qty = 1 # Default 1 jika tidak sebut angka
            
            if qty > matched_product['stock']:
                await update.message.reply_text(f"❌ Stok {matched_product['name']} tidak cukup! Sisa stok: {matched_product['stock']}")
                return
                
            total_price = qty * matched_product['price']
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO sales (business_id, total_amount, payment_method, staff_name) VALUES (?, ?, ?, ?)", 
                               (b_id, total_price, 'Tunai', access.get('name', 'Staff')))
                sale_id = cursor.lastrowid
                
                cursor.execute("INSERT INTO sale_items (sale_id, product_id, quantity, price_at_sale) VALUES (?, ?, ?, ?)",
                               (sale_id, matched_product['id'], qty, matched_product['price']))
                
                cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (qty, matched_product['id']))
                conn.commit()
                
            msg = f"🛒 *Penjualan Sukses!*\n\n{qty}x {matched_product['name']}\nTotal: Rp{int(total_price):,}".replace(',', '.')
            await update.message.reply_text(msg, parse_mode='Markdown')
            return

    # ----------------------------------------------------
    # 5. FITUR KASBON (CATAT & BAYAR)
    # Contoh: "kasbon budi 50rb", "utang joko 100000"
    # Contoh bayar: "budi bayar kasbon 50rb"
    # ----------------------------------------------------
    if any(k in text for k in ["kasbon", "utang", "hutang", "bon"]):
        is_payment = any(k in text for k in ["bayar", "lunas", "cicil"])
        nominal = extract_number(text)
        
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
    # 6. FITUR PENGELUARAN
    # Contoh: "beli galon 20rb", "bayar listrik 150000"
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
    # 7. FITUR MANAJEMEN PEGAWAI (KODE UNDANGAN)
    # Contoh: "tambah pegawai", "kode undangan"
    # ----------------------------------------------------
    if any(k in text for k in ["pegawai", "kasir", "undangan", "invite"]):
        if role != 'owner':
            await update.message.reply_text("⚠️ Hanya pemilik yang dapat mengundang pegawai.")
            return
            
        invite_code = str(uuid.uuid4())[:8].upper()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE businesses SET invite_code = ? WHERE id = ?", (invite_code, b_id))
            conn.commit()
            
        await update.message.reply_text(f"👨‍💼 *Kode Undangan Kasir*\n\nBerikan kode ini kepada kasir Anda:\n`{invite_code}`\n\nMinta mereka mengetikkan `/join {invite_code}` di bot ini.", parse_mode='Markdown')
        return

    # ----------------------------------------------------
    # 8. FITUR DAFTAR PELANGGAN
    # Contoh: "lihat pelanggan", "daftar pelanggan"
    # ----------------------------------------------------
    if any(k in text for k in ["pelanggan", "customer", "pembeli"]):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, phone FROM customers WHERE business_id = ?", (b_id,))
            customers = cursor.fetchall()
            
        if not customers:
            await update.message.reply_text("👥 Belum ada data pelanggan yang terdaftar.")
            return
            
        msg = "👥 *Daftar Pelanggan*\n\n"
        for c in customers:
            phone = c['phone'] or "-"
            msg += f"👤 {c['name']} (☎️ {phone})\n"
        await update.message.reply_text(msg, parse_mode='Markdown')
        return

    # ----------------------------------------------------
    # 9. JIKA TIDAK MENGERTI
    # ----------------------------------------------------
    await update.message.reply_text(
        "Maaf, saya kurang mengerti maksud kalimatmu. 😅\n\n"
        "*Coba ketik dengan gaya seperti ini:*\n"
        "📊 _'Tolong cek laporan hari ini'_\n"
        "📦 _'Lihat daftar stok'_ atau _'Tambah produk Sabun harga 5000 stok 20'_\n"
        "🛒 _'Jual Es Teh 2 porsi'_\n"
        "📓 _'Kasbon si budi 50rb'_ atau _'Budi bayar utang 50rb'_\n"
        "💸 _'Beli token listrik 20000'_\n"
        "👨‍💼 _'Tambah pegawai'_",
        parse_mode='Markdown'
    )
