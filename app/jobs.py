import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from app.database.connection import get_db_connection
from app.utils.reports import get_report_text

logger = logging.getLogger(__name__)

async def execute_daily_report(bot):
    """Fungsi mandiri untuk mengirim laporan harian ke seluruh pemilik usaha."""
    logger.info("Mulai mengeksekusi Auto-Kirim Laporan Harian...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Ambil semua user_id (Telegram ID) pemilik usaha
        cursor.execute("SELECT u.id as user_id, b.id as business_id FROM users u JOIN businesses b ON u.id = b.user_id")
        owners = cursor.fetchall()
        
    for owner in owners:
        user_id = owner['user_id']
        b_id = owner['business_id']
        
        # Buat teks laporan
        text = get_report_text(b_id, "today")
        message = f"🔔 *AUTO-KIRIM LAPORAN HARIAN*\n\n{text}"
        
        try:
            await bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            logger.info(f"Berhasil mengirim laporan otomatis ke {user_id}")
        except Exception as e:
            logger.error(f"Gagal mengirim laporan otomatis ke {user_id}: {e}")

def start_background_scheduler(bot):
    """Menjalankan background scheduler mandiri tanpa PTB JobQueue."""
    tz = pytz.timezone('Asia/Jakarta')
    scheduler = AsyncIOScheduler(timezone=tz)
    
    # Jadwalkan setiap hari jam 21:00 WIB
    trigger = CronTrigger(hour=21, minute=0, timezone=tz)
    
    # Bungkus eksekusi bot ke dalam lambda atau pass args
    scheduler.add_job(execute_daily_report, trigger, args=[bot])
    
    scheduler.start()
    logger.info("Berhasil mendaftarkan Job Auto-Kirim Laporan Harian (Setiap 21:00 WIB) via Native APScheduler.")

