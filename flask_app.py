import asyncio
from flask import Flask, request, jsonify
from telegram import Update
from app.bot import get_application
from app.config import BOT_TOKEN

# Inisialisasi Flask (Untuk PythonAnywhere)
app = Flask(__name__)

# Buat dan Inisialisasi PTB Application
ptb_app = get_application()

# Kita butuh event loop background untuk menginisialisasi bot secara sinkron
loop = asyncio.get_event_loop()
loop.run_until_complete(ptb_app.initialize())

@app.route('/', methods=['GET'])
def index():
    return "✅ Server Webhook KawanUsaha berjalan dengan baik!"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    """Endpoint untuk menerima kiriman data dari Telegram"""
    if request.method == "POST":
        update_data = request.get_json(force=True)
        update = Update.de_json(update_data, ptb_app.bot)
        
        # Eksekusi secara async
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        new_loop.run_until_complete(ptb_app.process_update(update))
        
        return "OK", 200

# Untuk menjalankan manual via python flask_app.py
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
