import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from app.config import BOT_TOKEN
from app.handlers.start import get_onboarding_handler
from app.handlers.menu import handle_menu_callback
from app.handlers.products import (
    get_product_conversation, product_menu, list_products,
    manage_products, product_detail, delete_product, get_edit_product_conversation
)
from app.handlers.kasbon import (
    get_kasbon_conversation, kasbon_menu, list_debtors, debtor_detail
)
from app.database.migrations import run_migrations

# Konfigurasi logging dasar untuk memonitor error dan aktivitas bot
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Kurangi log level dari modul httpx agar terminal tidak terlalu penuh
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani error yang terjadi saat bot berjalan."""
    logger.error("Exception saat menangani update:", exc_info=context.error)
    
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Maaf, terjadi kesalahan internal sistem. Silakan coba beberapa saat lagi."
        )

def run_bot():
    """Fungsi utama untuk inisialisasi dan menjalankan bot."""
    # Workaround untuk Python 3.14+: buat event loop baru jika belum ada
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    # Jalankan inisialisasi database (Buat tabel jika belum ada)
    run_migrations()
    logger.info("✅ Database berhasil diinisialisasi.")

    # Inisialisasi bot menggunakan token
    application = Application.builder().token(BOT_TOKEN).build()

    # Daftarkan handlers (Urutan sangat penting!)
    application.add_handler(get_onboarding_handler())
    
    # Handler khusus untuk Modul Produk
    application.add_handler(get_product_conversation())
    application.add_handler(get_edit_product_conversation())
    application.add_handler(get_kasbon_conversation())
    application.add_handler(CallbackQueryHandler(kasbon_menu, pattern="^menu_kasbon$"))
    application.add_handler(CallbackQueryHandler(list_debtors, pattern="^manage_debtors$"))
    application.add_handler(CallbackQueryHandler(debtor_detail, pattern="^debtor_"))
    
    # Handler khusus untuk Modul Stok
    from app.handlers.inventory import get_stock_conversation, manage_stock_list, stock_detail
    application.add_handler(get_stock_conversation())
    application.add_handler(CallbackQueryHandler(manage_stock_list, pattern="^manage_stock_list$"))
    application.add_handler(CallbackQueryHandler(stock_detail, pattern="^stock_detail_"))
    
    # Handler khusus untuk Modul Penjualan (Kasir Terintegrasi)
    from app.handlers.sales import get_sales_conversation
    application.add_handler(get_sales_conversation())
    
    # Handler khusus untuk Modul Laporan
    from app.handlers.reports import reports_menu, generate_report
    application.add_handler(CallbackQueryHandler(reports_menu, pattern="^menu_laporan$"))
    application.add_handler(CallbackQueryHandler(generate_report, pattern="^report_(today|7d|month)$"))
    
    # Handler khusus untuk Modul Pelanggan
    from app.handlers.customers import (
        customers_menu, get_customer_conversation, list_customers,
        manage_customers, customer_detail, delete_customer
    )
    application.add_handler(get_customer_conversation())
    application.add_handler(CallbackQueryHandler(customers_menu, pattern="^menu_pelanggan$"))
    application.add_handler(CallbackQueryHandler(list_customers, pattern="^list_customers$"))
    application.add_handler(CallbackQueryHandler(manage_customers, pattern="^manage_customers$"))
    application.add_handler(CallbackQueryHandler(customer_detail, pattern="^cust_detail_"))
    application.add_handler(CallbackQueryHandler(delete_customer, pattern="^delete_cust_"))
    
    # Handler khusus untuk Modul Invoice
    from app.handlers.invoices import invoices_menu, send_invoice_callback
    application.add_handler(CallbackQueryHandler(invoices_menu, pattern="^menu_invoice$"))
    application.add_handler(CallbackQueryHandler(send_invoice_callback, pattern="^send_invoice_"))
    
    # Handler khusus untuk Modul Pengaturan
    from app.handlers.settings import settings_menu, get_settings_conversation
    application.add_handler(get_settings_conversation())
    application.add_handler(CallbackQueryHandler(settings_menu, pattern="^menu_pengaturan$"))
    
    # Handler khusus untuk Modul Pengeluaran
    from app.handlers.expenses import get_expense_conversation, expenses_menu, list_expenses, delete_expense
    application.add_handler(get_expense_conversation())
    application.add_handler(CallbackQueryHandler(expenses_menu, pattern="^menu_pengeluaran$"))
    application.add_handler(CallbackQueryHandler(list_expenses, pattern="^list_expenses$"))
    application.add_handler(CallbackQueryHandler(delete_expense, pattern="^del_exp_"))
    
    # Handler khusus untuk Modul Pegawai
    from app.handlers.staff import staff_menu, generate_invite, remove_staff_menu, delete_staff, join_command
    application.add_handler(CallbackQueryHandler(staff_menu, pattern="^menu_pegawai$"))
    application.add_handler(CallbackQueryHandler(generate_invite, pattern="^generate_invite$"))
    application.add_handler(CallbackQueryHandler(remove_staff_menu, pattern="^remove_staff_menu$"))
    application.add_handler(CallbackQueryHandler(delete_staff, pattern="^del_staff_"))
    application.add_handler(CommandHandler("join", join_command))
    
    application.add_handler(CallbackQueryHandler(product_menu, pattern="^menu_produk$"))
    application.add_handler(CallbackQueryHandler(list_products, pattern="^list_products$"))
    application.add_handler(CallbackQueryHandler(manage_products, pattern="^manage_products$"))
    application.add_handler(CallbackQueryHandler(product_detail, pattern="^prod_detail_"))
    application.add_handler(CallbackQueryHandler(delete_product, pattern="^delete_prod_"))
    
    # Handler Menu Utama & fallbacks (Menangkap menu_* lainnya)
    application.add_handler(CallbackQueryHandler(handle_menu_callback, pattern="^menu_"))
    
    # Daftarkan error handler
    application.add_error_handler(error_handler)

    logger.info("✅ Bot KawanUsaha sedang berjalan (Polling mode)...")

    # Jalankan bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)
