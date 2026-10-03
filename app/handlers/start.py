from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from app.database.connection import get_db_connection
from app.handlers.menu import show_main_menu

# State untuk percakapan
ASK_BUSINESS_NAME = 1

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler awal saat user mengetik /start."""
    user = update.effective_user
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Cek apakah user sudah terdaftar di database
        cursor.execute("SELECT id FROM users WHERE id = ?", (user.id,))
        user_record = cursor.fetchone()
        
        if not user_record:
            # User Baru -> Daftarkan dan minta nama usaha
            cursor.execute(
                "INSERT INTO users (id, first_name, username) VALUES (?, ?, ?)",
                (user.id, user.first_name, user.username)
            )
            conn.commit()
            
            welcome_message = (
                f"👋 Halo, {user.first_name}!\n\n"
                "Selamat datang di KawanUsaha.\n\n"
                "Saya akan membantu kamu mengelola produk, stok, penjualan, dan laporan usaha.\n\n"
                "🏪 Apa nama usaha kamu?"
            )
            await update.message.reply_text(welcome_message)
            return ASK_BUSINESS_NAME
            
        else:
            # User Lama -> Cek apakah sudah punya bisnis
            cursor.execute("SELECT name FROM businesses WHERE user_id = ?", (user.id,))
            business = cursor.fetchone()
            
            if business:
                # Sudah ada bisnis -> Langsung masuk Menu Utama
                await update.message.reply_text(f"👋 Selamat datang kembali di KawanUsaha, {user.first_name}!")
                await show_main_menu(update, context)
                return ConversationHandler.END
            else:
                # Belum ada bisnis (misal proses terputus sebelumnya)
                await update.message.reply_text("🏪 Apa nama usaha kamu?")
                return ASK_BUSINESS_NAME

async def save_business_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menyimpan nama bisnis setelah user menjawab."""
    business_name = update.message.text
    user = update.effective_user
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO businesses (user_id, name) VALUES (?, ?)",
            (user.id, business_name)
        )
        conn.commit()
    
    await update.message.reply_text(
        f"✅ Usaha *{business_name}* berhasil didaftarkan!\n\nSelamat datang di KawanUsaha!",
        parse_mode='Markdown'
    )
    # Setelah selesai, tampilkan menu utama
    await show_main_menu(update, context)
    return ConversationHandler.END

async def cancel_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Membatalkan proses pendaftaran jika user mengetik /cancel."""
    await update.message.reply_text("❌ Pendaftaran dibatalkan. Ketik /start untuk mengulang.")
    return ConversationHandler.END

def get_onboarding_handler():
    """Mengembalikan konfigurasi ConversationHandler untuk proses onboarding."""
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            ASK_BUSINESS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_business_name)]
        },
        fallbacks=[CommandHandler("cancel", cancel_onboarding)]
    )
