import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from app.database.connection import get_db_connection
from app.utils.auth import get_user_access

(CHOOSING_PRODUCT, ENTERING_QTY, CHOOSING_CUSTOMER, ENTERING_DISCOUNT, CHOOSING_PAYMENT, CONFIRMING_SALE) = range(6)

async def render_sales_menu(message, context: ContextTypes.DEFAULT_TYPE, user_id: int, is_edit: bool = True):
    cart = context.user_data.get('cart', {})
    
    access = get_user_access(user_id)
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, price, stock FROM products WHERE business_id = ? ORDER BY category, name", (b_id,))
        products = cursor.fetchall()
        
    cart_text = ""
    total_amount = 0
    if cart:
        cart_text = "🛒 *KERANJANG BELANJA:*\n"
        for p_id, item in cart.items():
            subtotal = item['qty'] * item['price']
            total_amount += subtotal
            harga_str = f"Rp{int(item['price']):,}".replace(',', '.')
            sub_str = f"Rp{int(subtotal):,}".replace(',', '.')
            cart_text += f"🔹 {item['name']}\n     {item['qty']} x {harga_str} = *{sub_str}*\n"
        cart_text += f"\n💰 *Subtotal: Rp{int(total_amount):,}*\n\n".replace(',', '.')
    else:
        cart_text = "🛒 *Keranjang masih kosong.*\n\n"
        
    text = f"💰 *KASIR PENJUALAN*\n\n{cart_text}Pilih produk untuk ditambahkan ke keranjang:"
    
    keyboard = []
    
    current_cat = None
    for p in products:
        if p['category'] != current_cat:
            current_cat = p['category']
            keyboard.append([InlineKeyboardButton(f"📂 --- {current_cat.upper()} ---", callback_data="ignore")])
            
        in_cart = cart.get(str(p['id']), {}).get('qty', 0)
        avail_stock = p['stock'] - in_cart
        
        harga = f"Rp{int(p['price']):,}".replace(',', '.')
        if avail_stock > 0:
            btn_text = f"📦 {p['name']} ({harga}) - Sisa: {avail_stock}"
            callback = f"sale_prod_{p['id']}"
        else:
            btn_text = f"❌ {p['name']} (Habis)"
            callback = "sale_empty"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])
        
    if cart:
        keyboard.append([InlineKeyboardButton("🛍 Lanjut ke Pembayaran ➡️", callback_data="checkout")])
        keyboard.append([InlineKeyboardButton("🗑 Kosongkan Keranjang", callback_data="clear_cart")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Batal & Kembali ke Menu", callback_data="cancel_sale")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_edit:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def sales_menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    if not access:
        await query.message.edit_text("Akses ditolak.")
        return ConversationHandler.END
        
    context.user_data['cart'] = {}
    await render_sales_menu(query.message, context, update.effective_user.id, is_edit=True)
    return CHOOSING_PRODUCT

async def ignore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    return CHOOSING_PRODUCT

async def ask_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    prod_id = query.data.split("_")[2]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, price, stock FROM products WHERE id = ?", (prod_id,))
        p = cursor.fetchone()
        
    context.user_data['temp_prod_id'] = prod_id
    context.user_data['temp_prod_name'] = p['name']
    context.user_data['temp_prod_price'] = p['price']
    context.user_data['temp_prod_stock'] = p['stock']
    
    await query.message.edit_text(
        f"🛒 Tambah *{p['name']}*\n"
        f"Masukkan jumlah barang (hanya angka):\n\n"
        f"_(Ketik /cancel untuk kembali ke Kasir)_",
        parse_mode='Markdown'
    )
    return ENTERING_QTY

async def receive_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qty_text = update.message.text
    if not qty_text.isdigit():
        await update.message.reply_text("⚠️ Harus berupa angka. Masukkan jumlah:")
        return ENTERING_QTY
        
    qty = int(qty_text)
    if qty <= 0:
        await update.message.reply_text("⚠️ Jumlah minimal 1. Masukkan jumlah:")
        return ENTERING_QTY
        
    prod_id = str(context.user_data['temp_prod_id'])
    stock = context.user_data['temp_prod_stock']
    
    cart = context.user_data.get('cart', {})
    current_qty_in_cart = cart.get(prod_id, {}).get('qty', 0)
    
    if current_qty_in_cart + qty > stock:
        await update.message.reply_text(
            f"⚠️ Stok tidak cukup!\nSisa stok di database: {stock}\nSudah ada di keranjang: {current_qty_in_cart}\n"
            f"Silakan masukkan jumlah yang lebih kecil:"
        )
        return ENTERING_QTY
        
    if prod_id in cart:
        cart[prod_id]['qty'] += qty
    else:
        cart[prod_id] = {
            'name': context.user_data['temp_prod_name'],
            'price': context.user_data['temp_prod_price'],
            'qty': qty
        }
    context.user_data['cart'] = cart
    
    for k in ['temp_prod_id', 'temp_prod_name', 'temp_prod_price', 'temp_prod_stock']:
        context.user_data.pop(k, None)
        
    await update.message.reply_text("✅ Berhasil dimasukkan ke keranjang!")
    await render_sales_menu(update.message, context, update.effective_user.id, is_edit=False)
    return CHOOSING_PRODUCT

async def cancel_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Batal menambahkan barang.")
    await render_sales_menu(update.message, context, update.effective_user.id, is_edit=False)
    return CHOOSING_PRODUCT

async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Keranjang dibersihkan!")
    context.user_data['cart'] = {}
    await render_sales_menu(query.message, context, update.effective_user.id, is_edit=True)
    return CHOOSING_PRODUCT

async def checkout_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM customers WHERE business_id = ?", (b_id,))
        customers = cursor.fetchall()
        
    keyboard = [[InlineKeyboardButton("👤 Pelanggan Umum (Tanpa Nama)", callback_data="sel_cust_0")]]
    for c in customers:
        keyboard.append([InlineKeyboardButton(f"👤 {c['name']}", callback_data=f"sel_cust_{c['id']}")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Kembali ke Keranjang", callback_data="back_to_cart")])
    
    await query.message.edit_text(
        "👥 *Pilih Pelanggan*\n\nTransaksi ini atas nama siapa?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return CHOOSING_CUSTOMER

async def back_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await render_sales_menu(query.message, context, update.effective_user.id, is_edit=True)
    return CHOOSING_PRODUCT

async def select_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    cust_id = query.data.split("_")[2]
    context.user_data['sale_cust_id'] = int(cust_id)
    
    cust_name = "Pelanggan Umum"
    if cust_id != "0":
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM customers WHERE id = ?", (cust_id,))
            c = cursor.fetchone()
            if c: cust_name = c['name']
    context.user_data['sale_cust_name'] = cust_name
    
    await query.message.edit_text(
        "🏷 *Diskon Transaksi*\n\nApakah ada diskon untuk transaksi ini?\n"
        "Ketik nominal diskon (contoh: 5000).\n"
        "Ketik **0** jika tidak ada diskon.\n\n"
        "_(Ketik /cancel untuk membatalkan seluruh transaksi)_",
        parse_mode='Markdown'
    )
    return ENTERING_DISCOUNT

async def receive_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    discount_text = update.message.text
    if not discount_text.isdigit():
        await update.message.reply_text("⚠️ Harus berupa angka. Ketik nominal diskon atau 0:")
        return ENTERING_DISCOUNT
        
    discount = int(discount_text)
    context.user_data['sale_discount'] = discount
    
    # Hitung Subtotal
    cart = context.user_data['cart']
    subtotal = 0
    for p_id, item in cart.items():
        subtotal += item['qty'] * item['price']
        
    if discount > subtotal:
        await update.message.reply_text(f"⚠️ Diskon tidak boleh melebihi subtotal (Rp{subtotal}). Masukkan ulang:")
        return ENTERING_DISCOUNT
    
    # Ambil Payment Methods dari tabel businesses
    access = get_user_access(update.effective_user.id)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT payment_methods FROM businesses WHERE id = ?", (access['business_id'],))
        biz = cursor.fetchone()
        
    methods_str = biz['payment_methods'] if biz['payment_methods'] else 'Tunai,QRIS'
    methods_list = [m.strip() for m in methods_str.split(',')]
    
    keyboard = []
    for m in methods_list:
        keyboard.append([InlineKeyboardButton(f"💳 {m}", callback_data=f"sel_pay_{m}")])
        
    keyboard.append([InlineKeyboardButton("❌ Batal & Kosongkan Keranjang", callback_data="cancel_sale")])
    
    await update.message.reply_text(
        "💳 *Pilih Metode Pembayaran*\n\nPembayaran dilakukan menggunakan metode apa?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return CHOOSING_PAYMENT

async def select_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    payment_method = query.data.split("_", 2)[2]
    context.user_data['sale_payment'] = payment_method
    
    # Render Konfirmasi Final
    cart = context.user_data['cart']
    cust_name = context.user_data['sale_cust_name']
    discount = context.user_data['sale_discount']
    
    subtotal = 0
    text = f"🧾 *KONFIRMASI PESANAN*\n\nPelanggan: *{cust_name}*\n\n*Rincian Belanja:*\n"
    for p_id, item in cart.items():
        st = item['qty'] * item['price']
        subtotal += st
        harga_str = f"Rp{int(item['price']):,}".replace(',', '.')
        sub_str = f"Rp{int(st):,}".replace(',', '.')
        text += f"📦 {item['name']}\n   {item['qty']} x {harga_str} = {sub_str}\n"
        
    total = subtotal - discount
    context.user_data['sale_total'] = total
    
    sub_str = f"Rp{int(subtotal):,}".replace(',', '.')
    disc_str = f"Rp{int(discount):,}".replace(',', '.')
    tot_str = f"Rp{int(total):,}".replace(',', '.')
    
    text += f"\nSubtotal: {sub_str}\n"
    if discount > 0:
        text += f"Diskon: -{disc_str}\n"
    text += f"Metode Bayar: *{payment_method}*\n"
    text += f"\n💰 *TOTAL BAYAR: {tot_str}*\n\nApakah data ini sudah benar?"
    
    keyboard = [
        [InlineKeyboardButton("✅ Ya, Selesaikan Transaksi", callback_data="confirm_sale")],
        [InlineKeyboardButton("❌ Batal & Kosongkan Keranjang", callback_data="cancel_sale")]
    ]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return CONFIRMING_SALE

async def execute_sale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    cart = context.user_data['cart']
    cust_id = context.user_data['sale_cust_id']
    cust_name = context.user_data['sale_cust_name']
    total = context.user_data['sale_total']
    discount = context.user_data['sale_discount']
    payment_method = context.user_data['sale_payment']
    
    user_id = update.effective_user.id
    staff_name = update.effective_user.first_name
    
    access = get_user_access(user_id)
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        db_cust_id = cust_id if cust_id != 0 else None
        
        cursor.execute(
            "INSERT INTO sales (business_id, total_amount, discount, payment_method, customer_id, staff_name) VALUES (?, ?, ?, ?, ?, ?)", 
            (b_id, total, discount, payment_method, db_cust_id, staff_name)
        )
        sale_id = cursor.lastrowid
        
        for p_id, item in cart.items():
            qty = item['qty']
            price = item['price']
            
            cursor.execute("INSERT INTO sale_items (sale_id, product_id, quantity, price_at_sale) VALUES (?, ?, ?, ?)",
                           (sale_id, int(p_id), qty, price))
                           
            cursor.execute("SELECT stock FROM products WHERE id = ?", (int(p_id),))
            current_stock = cursor.fetchone()['stock']
            new_stock = current_stock - qty
            cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, int(p_id)))
            
            cursor.execute("INSERT INTO inventory_transactions (product_id, type, quantity, notes) VALUES (?, 'OUT', ?, ?)",
                           (int(p_id), qty, f"Penjualan #{sale_id}"))
                           
        conn.commit()
        
    context.user_data.clear()
    
    total_str = f"Rp{int(total):,}".replace(',', '.')
    success_text = (
        f"✅ *TRANSAKSI BERHASIL!*\n\n"
        f"ID Transaksi: #{sale_id}\n"
        f"Pelanggan: {cust_name}\n"
        f"Total: *{total_str}*\n"
        f"Via: {payment_method}\n\n"
        f"Stok produk otomatis terpotong."
    )
    
    keyboard = [
        [InlineKeyboardButton("🧾 Cetak Invoice PDF", callback_data=f"send_invoice_{sale_id}")],
        [InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data="menu_main")]
    ]
    
    await query.message.edit_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def cancel_sale_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        msg = update.callback_query.message
    else:
        msg = update.message
        
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_main")]]
    
    if update.callback_query:
        await msg.edit_text("❌ Transaksi dibatalkan dan keranjang dikosongkan.", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await msg.reply_text("❌ Transaksi dibatalkan dan keranjang dikosongkan.", reply_markup=InlineKeyboardMarkup(keyboard))
        
    return ConversationHandler.END

async def sale_empty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("⚠️ Stok produk ini habis atau tidak cukup!", show_alert=True)

def get_sales_conversation():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(sales_menu_start, pattern="^menu_penjualan$")],
        states={
            CHOOSING_PRODUCT: [
                CallbackQueryHandler(ask_qty, pattern="^sale_prod_"),
                CallbackQueryHandler(checkout_start, pattern="^checkout$"),
                CallbackQueryHandler(clear_cart, pattern="^clear_cart$"),
                CallbackQueryHandler(cancel_sale_all, pattern="^cancel_sale$"),
                CallbackQueryHandler(sale_empty_callback, pattern="^sale_empty$"),
                CallbackQueryHandler(ignore_callback, pattern="^ignore$")
            ],
            ENTERING_QTY: [
                CommandHandler("cancel", cancel_sale_all),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_qty)
            ],
            CHOOSING_CUSTOMER: [
                CallbackQueryHandler(select_customer, pattern="^sel_cust_"),
                CallbackQueryHandler(back_to_cart, pattern="^back_to_cart$")
            ],
            ENTERING_DISCOUNT: [
                CommandHandler("cancel", cancel_sale_all),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_discount)
            ],
            CHOOSING_PAYMENT: [
                CallbackQueryHandler(select_payment, pattern="^sel_pay_"),
                CallbackQueryHandler(cancel_sale_all, pattern="^cancel_sale$")
            ],
            CONFIRMING_SALE: [
                CallbackQueryHandler(execute_sale, pattern="^confirm_sale$"),
                CallbackQueryHandler(cancel_sale_all, pattern="^cancel_sale$")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_sale_all),
            CallbackQueryHandler(cancel_sale_all, pattern="^cancel_sale$")
        ]
    )
