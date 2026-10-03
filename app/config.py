import os
from dotenv import load_dotenv

# Memuat variabel environment dari file .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("⚠️ BOT_TOKEN tidak ditemukan. Pastikan Anda telah mengatur file .env dengan benar.")
