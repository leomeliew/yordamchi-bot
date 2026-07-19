import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot ishlayapti!"

def run_flask():
    app_flask.run(host='0.0.0.0', port=8000)

def keep_alive():
    Thread(target=run_flask, daemon=True).start()

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def delete_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
        print("✅ Xabar o'chirildi")
    except Exception as e:
        print(f"❌ Xato: {e}")

def main():
    keep_alive()
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, delete_service_message))
    bot_app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, delete_service_message))
    print("✅ Bot ishga tushdi!")
    bot_app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
