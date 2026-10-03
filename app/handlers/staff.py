import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler
from app.database.connection import get_db_connection
from app.utils.auth import get_user_access

async def staff_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    if not access or access['role'] != 'owner':
        await query.message.edit_text("⚠️ Akses ditolak. Hanya pemilik yang dapat mengakses menu ini.")
        return
        
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM staff WHERE business_id = ?", (b_id,))
        staff_list = cursor.fetchall()
        
        cursor.execute("SELECT invite_code FROM businesses WHERE id = ?", (b_id,))
        biz = cursor.fetchone()
        invite_code = biz['invite_code'] if biz else None
        
    text = "👨‍💼 *Manajemen Pegawai (Kasir)*\n\n"
    if not staff_list:
        text += "Belum ada pegawai yang terdaftar."
    else:
        text += "Daftar Pegawai:\n"
        for i, s in enumerate(staff_list, 1):
            text += f"{i}. {s['name']}\n"
            
    if invite_code:
        text += f"\n\n🔑 *Kode Undangan Aktif:* `{invite_code}`\n_(Berikan kode ini ke calon kasir untuk perintah /join)_"
            
    keyboard = [
        [InlineKeyboardButton("➕ Tambah Pegawai (Generate Kode)", callback_data="generate_invite")],
        [InlineKeyboardButton("❌ Hapus Pegawai", callback_data="remove_staff_menu")] if staff_list else [],
        [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data="menu_main")]
    ]
    # Filter empty rows
    keyboard = [row for row in keyboard if row]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def generate_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    b_id = access['business_id']
    
    code = "EMP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE businesses SET invite_code = ? WHERE id = ?", (code, b_id))
        conn.commit()
        
    text = (
        f"✅ *Kode Undangan Berhasil Dibuat!*\n\n"
        f"KODE: `{code}`\n\n"
        f"Minta pegawai Anda untuk membuka bot ini di HP-nya dan mengetikkan perintah:\n"
        f"`/join {code}`\n\n"
        f"_(Kode akan terus berlaku sampai Anda men-generate kode baru)_"
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu_pegawai")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def remove_staff_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    access = get_user_access(update.effective_user.id)
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM staff WHERE business_id = ?", (b_id,))
        staff_list = cursor.fetchall()
        
    keyboard = []
    for s in staff_list:
        keyboard.append([InlineKeyboardButton(f"❌ {s['name']}", callback_data=f"del_staff_{s['id']}")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="menu_pegawai")])
    
    await query.message.edit_text("Pilih pegawai yang ingin dihapus dari sistem:", reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_staff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    staff_id = query.data.split("_")[2]
    access = get_user_access(update.effective_user.id)
    b_id = access['business_id']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM staff WHERE id = ? AND business_id = ?", (staff_id, b_id))
        conn.commit()
        
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data="menu_pegawai")]]
    await query.message.edit_text("✅ Pegawai berhasil dihapus. Mereka tidak bisa lagi mengakses bot.", reply_markup=InlineKeyboardMarkup(keyboard))

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /join <kode>"""
    if not context.args:
        await update.message.reply_text("⚠️ Format salah. Gunakan: /join KODE")
        return
        
    code = context.args[0]
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Cari bisnis dengan kode tersebut
        cursor.execute("SELECT id, name FROM businesses WHERE invite_code = ?", (code,))
        biz = cursor.fetchone()
        
        if not biz:
            await update.message.reply_text("❌ Kode tidak valid atau sudah diganti.")
            return
            
        b_id = biz['id']
        
        # Cek jika dia adalah owner
        cursor.execute("SELECT id FROM businesses WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            await update.message.reply_text("⚠️ Anda adalah pemilik bisnis. Tidak perlu join sebagai pegawai.")
            return
            
        # Cek jika sudah pernah join
        cursor.execute("SELECT id FROM staff WHERE telegram_user_id = ?", (user_id,))
        if cursor.fetchone():
            await update.message.reply_text("⚠️ Anda sudah terdaftar sebagai pegawai.")
            return
            
        # Insert ke staff
        cursor.execute("INSERT INTO staff (business_id, telegram_user_id, name) VALUES (?, ?, ?)", (b_id, user_id, name))
        conn.commit()
        
    from app.handlers.menu import show_main_menu
    await update.message.reply_text(f"🎉 Berhasil! Anda sekarang terdaftar sebagai Kasir di toko *{biz['name']}*.", parse_mode='Markdown')
    await show_main_menu(update, context)

