import os
import re
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, MessageHandler,
    ContextTypes, filters
)

# ─── Keep Alive ───────────────────────────────────────────
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot ishlayapti!"

def run_flask():
    app_flask.run(host='0.0.0.0', port=8000)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# ─── Sozlamalar ───────────────────────────────────────────
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Ogohlantirish hisoblagichi
warnings = {}

# Reklama kalit so'zlari
AD_KEYWORDS = [
    "реклама", "reklama", "куплю", "продам", "sotiladi", "xarid",
    "подписывайтесь", "obuna", "subscribe", "promo", "скидка", "chegirma",
    "заработок", "daromad", "заработай", "invest", "крипто", "crypto",
    "casino", "казино", "bet", "букмекер", "форекс", "forex",
    "бизнес предложение", "biznes taklif", "100%", "гарантия", "kafolat"
]

# Link pattern
LINK_PATTERN = re.compile(
    r'(https?://|www\.|t\.me/|@\w{5,})', re.IGNORECASE
)

# ─── Yordamchi funksiya ───────────────────────────────────
def is_admin(status: str) -> bool:
    return status in ("administrator", "creator")

# ─── Asosiy tekshirish ────────────────────────────────────
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.from_user:
        return

    chat = message.chat
    user = message.from_user

    # Admin bo'lsa — tekshirmaslik
    member = await context.bot.get_chat_member(chat.id, user.id)
    if is_admin(member.status):
        return

    text = message.text or message.caption or ""
    user_id = user.id
    mention = f"<a href='tg://user?id={user_id}'>{user.first_name}</a>"

    violation = None

    # Link tekshirish
    if LINK_PATTERN.search(text):
        violation = "link"

    # Reklama tekshirish
    if not violation:
        lower_text = text.lower()
        for kw in AD_KEYWORDS:
            if kw in lower_text:
                violation = "ad"
                break

    if violation:
        # Xabarni o'chirish
        try:
            await message.delete()
        except Exception:
            pass

        # Ogohlantirish sonini oshirish
        warnings[user_id] = warnings.get(user_id, 0) + 1
        warn_count = warnings[user_id]

        if warn_count >= 3:
            # 3 ta ogohlantirish — kicklash
            try:
                await context.bot.ban_chat_member(chat.id, user_id)
                await context.bot.unban_chat_member(chat.id, user_id)
            except Exception:
                pass
            warnings[user_id] = 0
            await context.bot.send_message(
                chat.id,
                f"🚫 {mention} guruhdan chiqarildi!\n"
                f"Sabab: 3 marta qoidani buzdi.",
                parse_mode="HTML"
            )
        else:
            remaining = 3 - warn_count
            if violation == "link":
                reason = "🔗 Link yuborildi"
                advice = "Guruhda link yuborish taqiqlanadi."
            else:
                reason = "📢 Reklama yuborildi"
                advice = "Guruhda reklama yuborish taqiqlanadi."

            await context.bot.send_message(
                chat.id,
                f"⚠️ {mention}, diqqat!\n\n"
                f"{reason}\n"
                f"{advice}\n\n"
                f"Ogohlantirish: {warn_count}/3\n"
                f"Yana {remaining} marta buzsangiz — guruhdan chiqarilasiz.",
                parse_mode="HTML"
            )

# ─── Kirish/Chiqish xabarlarini o'chirish ─────────────────
async def delete_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

# ─── Ishga tushirish ──────────────────────────────────────
def main():
    keep_alive()

    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Matn xabarlar
    bot_app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, check_message
    ))

    # Rasm, video, hujjat (caption tekshirish uchun)
    bot_app.add_handler(MessageHandler(
        (filters.PHOTO | filters.VIDEO | filters.Document.ALL), check_message
    ))

    # Kirish xabarini o'chirish
    bot_app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS, delete_service_message
    ))

    # Chiqish xabarini o'chirish
    bot_app.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER, delete_service_message
    ))

    print("✅ Bot ishga tushdi!")
    bot_app.run_polling()

if __name__ == "__main__":
    main()
