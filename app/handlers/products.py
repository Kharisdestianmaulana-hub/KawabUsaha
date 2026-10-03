from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from app.database.connection import get_db_connection
from app.utils.auth import get_user_access

(PROD_CATEGORY, PROD_NAME, PROD_PRICE, PROD_STOCK) = range(4)
(EDIT_PRICE_STATE, EDIT_NAME_STATE, EDIT_CAT_STATE) = range(3)

async def product_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📋 Daftar Produk", callback_data="list_products"),
         InlineKeyboardButton("📝 Tambah Produk", callback_data="add_product")],
        [InlineKeyboardButton("⚙️ Kelola Produk", callback_data="manage_products"),
         InlineKeyboardButton("📦 Kelola Stok", callback_data="manage_stock_list")],
        [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data="menu_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("📦 *Manajemen Produk*\n\nPilih aksi yang ingin dilakukan:", reply_markup=reply_markup, parse_mode='Markdown')

# --- ALUR TAMBAH PRODUK ---
async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    if not access or access['role'] != 'owner':
        await query.message.edit_text("⚠️ Akses ditolak. Hanya pemilik yang dapat menambah produk.")
        return ConversationHandler.END
        
    await query.message.edit_text(
        "📝 *Kategori Produk*\n\nMasukkan nama kategori (contoh: Makanan, Minuman, Pakaian).\nAtau ketik *Umum* jika tidak ada kategori:\n\n_(Ketik /cancel untuk membatalkan)_", 
        parse_mode='Markdown'
    )
    return PROD_CATEGORY
    
async def ask_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['prod_category'] = update.message.text
    await update.message.reply_text("Sip! Sekarang masukkan *Nama Produk*:\n\n_(Ketik /cancel untuk membatalkan)_", parse_mode='Markdown')
    return PROD_NAME

async def ask_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['prod_name'] = update.message.text
    await update.message.reply_text("Oke, berapa *Harga Jual* produk ini? (Hanya angka, contoh: 15000)\n\n_(Ketik /cancel untuk membatalkan)_", parse_mode='Markdown')
    return PROD_PRICE

async def ask_product_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ Harga harus berupa angka. Masukkan harga jual kembali:")
        return PROD_PRICE
    context.user_data['prod_price'] = int(update.message.text)
    await update.message.reply_text("Terakhir, masukkan *Stok Awal* produk ini (Hanya angka):\n\n_(Ketik /cancel untuk membatalkan)_", parse_mode='Markdown')
    return PROD_STOCK

async def save_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ Stok harus berupa angka. Masukkan stok awal kembali:")
        return PROD_STOCK
        
    stock = int(update.message.text)
    name = context.user_data['prod_name']
    price = context.user_data['prod_price']
    category = context.user_data['prod_category']
    user_id = update.effective_user.id
    
    access = get_user_access(user_id)
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (business_id, name, category, price, stock) VALUES (?, ?, ?, ?, ?)",
            (b_id, name, category, price, stock)
        )
        prod_id = cursor.lastrowid
        cursor.execute("INSERT INTO inventory_transactions (product_id, type, quantity, notes) VALUES (?, 'IN', ?, 'Initial stock')",
                       (prod_id, stock))
        conn.commit()
        
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu Produk", callback_data="menu_produk")]]
    await update.message.reply_text(f"✅ Produk *{name}* berhasil ditambahkan ke kategori *{category}*!", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def cancel_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("⬅️ Kembali ke Menu Produk", callback_data="menu_produk")]]
    await update.message.reply_text("❌ Penambahan produk dibatalkan.", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

def get_product_conversation():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_product, pattern="^add_product$")],
        states={
            PROD_CATEGORY: [CommandHandler("cancel", cancel_add_product), MessageHandler(filters.TEXT & ~filters.COMMAND, ask_product_name)],
            PROD_NAME: [CommandHandler("cancel", cancel_add_product), MessageHandler(filters.TEXT & ~filters.COMMAND, ask_product_price)],
            PROD_PRICE: [CommandHandler("cancel", cancel_add_product), MessageHandler(filters.TEXT & ~filters.COMMAND, ask_product_stock)],
            PROD_STOCK: [CommandHandler("cancel", cancel_add_product), MessageHandler(filters.TEXT & ~filters.COMMAND, save_product)],
        },
        fallbacks=[CommandHandler("cancel", cancel_add_product)]
    )

# --- DAFTAR PRODUK ---
async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, category, price, stock FROM products WHERE business_id = ? ORDER BY category, name", (b_id,))
        products = cursor.fetchall()
        
    if not products:
        text = "📋 *Daftar Produk*\n\nBelum ada produk yang ditambahkan."
    else:
        text = "📋 *Daftar Produk*\n\n"
        current_cat = ""
        for p in products:
            if p['category'] != current_cat:
                current_cat = p['category']
                text += f"\n📂 *{current_cat}*\n"
            harga = f"Rp{int(p['price']):,}".replace(',', '.')
            text += f"🔹 {p['name']} | {harga} | Stok: {p['stock']}\n"
            
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu_produk")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# --- KELOLA PRODUK ---
async def manage_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    if access['role'] != 'owner':
        await query.message.edit_text("⚠️ Akses ditolak.")
        return
        
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM products WHERE business_id = ?", (b_id,))
        products = cursor.fetchall()
        
    if not products:
        keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu_produk")]]
        await query.message.edit_text("⚠️ Belum ada produk.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
        
    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(p['name'], callback_data=f"prod_detail_{p['id']}")])
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="menu_produk")])
    
    await query.message.edit_text("⚙️ Pilih produk yang ingin diedit/dihapus:", reply_markup=InlineKeyboardMarkup(keyboard))

async def product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = query.data.split("_")[2]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, price, stock FROM products WHERE id = ?", (prod_id,))
        p = cursor.fetchone()
        
    harga = f"Rp{int(p['price']):,}".replace(',', '.')
    text = f"📦 *Detail Produk*\n\nKategori: {p['category']}\nNama: *{p['name']}*\nHarga: {harga}\nStok: {p['stock']}\n\nPilih aksi yang ingin dilakukan:"
    
    keyboard = [
        [InlineKeyboardButton("✏️ Ubah Harga", callback_data=f"edit_price_{p['id']}"),
         InlineKeyboardButton("📝 Ubah Nama", callback_data=f"edit_name_{p['id']}")],
        [InlineKeyboardButton("📂 Pindah Kategori", callback_data=f"edit_cat_{p['id']}")],
        [InlineKeyboardButton("❌ Hapus Produk", callback_data=f"delete_prod_{p['id']}")],
        [InlineKeyboardButton("⬅️ Kembali", callback_data="manage_products")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = query.data.split("_")[2]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
        conn.commit()
        
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data="manage_products")]]
    await query.message.edit_text("✅ Produk berhasil dihapus.", reply_markup=InlineKeyboardMarkup(keyboard))

# --- EDIT DATA PRODUK ---
async def start_edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['edit_prod_id'] = query.data.split("_")[2]
    await query.message.edit_text("✏️ Masukkan *Harga Baru* (Hanya angka):\n\n_(Ketik /cancel untuk membatalkan)_", parse_mode='Markdown')
    return EDIT_PRICE_STATE

async def save_edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ Harus berupa angka. Masukkan harga baru:")
        return EDIT_PRICE_STATE
        
    new_price = int(update.message.text)
    prod_id = context.user_data['edit_prod_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET price = ? WHERE id = ?", (new_price, prod_id))
        conn.commit()
        
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("⬅️ Kelola Produk", callback_data="manage_products")]]
    await update.message.reply_text("✅ Harga berhasil diubah!", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

async def start_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['edit_prod_id'] = query.data.split("_")[2]
    await query.message.edit_text("📝 Masukkan *Nama Produk* yang baru:\n\n_(Ketik /cancel untuk membatalkan)_", parse_mode='Markdown')
    return EDIT_NAME_STATE

async def save_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text
    prod_id = context.user_data['edit_prod_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET name = ? WHERE id = ?", (new_name, prod_id))
        conn.commit()
        
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("⬅️ Kelola Produk", callback_data="manage_products")]]
    await update.message.reply_text(f"✅ Nama berhasil diubah menjadi *{new_name}*!", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def start_edit_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['edit_prod_id'] = query.data.split("_")[2]
    await query.message.edit_text("📂 Masukkan *Kategori Baru* (contoh: Makanan, Minuman, Umum):\n\n_(Ketik /cancel untuk membatalkan)_", parse_mode='Markdown')
    return EDIT_CAT_STATE

async def save_edit_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_cat = update.message.text
    prod_id = context.user_data['edit_prod_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET category = ? WHERE id = ?", (new_cat, prod_id))
        conn.commit()
        
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("⬅️ Kelola Produk", callback_data="manage_products")]]
    await update.message.reply_text(f"✅ Kategori berhasil diubah menjadi *{new_cat}*!", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("⬅️ Kelola Produk", callback_data="manage_products")]]
    await update.message.reply_text("❌ Perubahan dibatalkan.", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

def get_edit_product_conversation():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_edit_price, pattern="^edit_price_"),
            CallbackQueryHandler(start_edit_name, pattern="^edit_name_"),
            CallbackQueryHandler(start_edit_cat, pattern="^edit_cat_")
        ],
        states={
            EDIT_PRICE_STATE: [CommandHandler("cancel", cancel_edit), MessageHandler(filters.TEXT & ~filters.COMMAND, save_edit_price)],
            EDIT_NAME_STATE: [CommandHandler("cancel", cancel_edit), MessageHandler(filters.TEXT & ~filters.COMMAND, save_edit_name)],
            EDIT_CAT_STATE: [CommandHandler("cancel", cancel_edit), MessageHandler(filters.TEXT & ~filters.COMMAND, save_edit_cat)],
        },
        fallbacks=[CommandHandler("cancel", cancel_edit)]
    )
