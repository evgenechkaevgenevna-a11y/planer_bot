from flask import Flask
import threading
import os
import subprocess

app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health_check():
    return "Бот работает!", 200

def run_bot():
    # Запускаем бота в отдельном процессе
    subprocess.run(["python", "bot.py"])

# Запускаем бота при старте сервера
thread = threading.Thread(target=run_bot)
thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
