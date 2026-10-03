import sys
import os
import asyncio
from flask import Flask, request
from telegram import Update
from app.bot import get_application
from app.config import BOT_TOKEN

# Paksa deteksi PythonAnywhere agar proxy aktif
os.environ['PYTHONANYWHERE_SITE'] = 'true'
os.environ['http_proxy'] = 'http://proxy.server:3128'
os.environ['https_proxy'] = 'http://proxy.server:3128'

app = Flask(__name__)
ptb_app = get_application()

# Inisialisasi loop sinkron (tanpa background thread untuk menghindari suspended thread di uWSGI)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(ptb_app.initialize())
loop.run_until_complete(ptb_app.start())

@app.route('/', methods=['GET'])
def index():
    return "✅ Server Webhook KawanUsaha berjalan dengan baik!"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.method == "POST":
        update_data = request.get_json(force=True)
        update = Update.de_json(update_data, ptb_app.bot)
        
        # Eksekusi secara aman di dalam satu thread yang sama
        # Memastikan tidak ada thread block atau proxy timeout
        loop.run_until_complete(ptb_app.process_update(update))
        
        return "OK", 200

