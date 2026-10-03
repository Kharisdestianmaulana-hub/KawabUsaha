import asyncio
import threading
from flask import Flask, request
from telegram import Update
from app.bot import get_application
from app.config import BOT_TOKEN

app = Flask(__name__)
ptb_app = get_application()

# 1. Buat event loop di background agar library asinkron Telegram berjalan stabil
worker_loop = asyncio.new_event_loop()

def run_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

thread = threading.Thread(target=run_loop, args=(worker_loop,), daemon=True)
thread.start()

# 2. Inisialisasi bot (Wajib dilakukan di PTB v20+)
async def init_bot():
    await ptb_app.initialize()
    await ptb_app.start()

# Jalankan inisialisasi di background loop
asyncio.run_coroutine_threadsafe(init_bot(), worker_loop).result()

@app.route('/', methods=['GET'])
def index():
    return "✅ Server Webhook KawanUsaha berjalan dengan baik!"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.method == "POST":
        update_data = request.get_json(force=True)
        update = Update.de_json(update_data, ptb_app.bot)
        
        # Lempar update ke background loop agar diproses
        future = asyncio.run_coroutine_threadsafe(ptb_app.process_update(update), worker_loop)
        future.result() # Tunggu sampai selesai diproses
        
        return "OK", 200
