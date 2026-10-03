import logging
from datetime import time
import pytz
from telegram.ext import ContextTypes
from app.database.connection import get_db_connection
from app.utils.reports import get_report_text

logger = logging.getLogger(__name__)

async def send_daily_report_job(context: ContextTypes.DEFAULT_TYPE):
    """Job yang berjalan otomatis untuk mengirim laporan harian ke seluruh pemilik usaha."""
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
            await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            logger.info(f"Berhasil mengirim laporan otomatis ke {user_id}")
        except Exception as e:
            logger.error(f"Gagal mengirim laporan otomatis ke {user_id}: {e}")

def setup_jobs(job_queue):
    """Mendaftarkan jadwal cron job pada bot."""
    if job_queue is None:
        logger.warning("Job Queue tidak aktif! Auto-kirim laporan gagal di-setup.")
        return
        
    # Zona waktu Jakarta
    tz = pytz.timezone('Asia/Jakarta')
    
    # Jadwalkan jam 21:00 WIB
    t = time(hour=21, minute=0, tzinfo=tz)
    
    job_queue.run_daily(send_daily_report_job, t)
    logger.info("Berhasil mendaftarkan Job Auto-Kirim Laporan Harian (Setiap 21:00 WIB).")
