import os
import re
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot ishlayapti!"

def run_flask():
    app_flask.run(host='0.0.0.0', port=8000)

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ.get("BOT_TOKEN")

whitelist = {}

LINK_PATTERN = re.compile(r'(https?://\S+|www\.\S+|t\.me/\S+)', re.IGNORECASE)
USERNAME_PATTERN = re.compile(r'@(\w{5,})')

def is_admin(status):
    return status in ("administrator", "creator")

def is_whitelisted(text, chat_id):
    allowed = whitelist.get(chat_id, [])
    text_lower = text.lower()
    for entry in allowed:
        if entry.lower() in text_lower:
            return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Men <b>Yordamchi Admin</b> botiman!\n\n"
        "🛡 <b>Mening vazifalarim:</b>\n\n"
        "🔗 Ruxsatsiz link yuborilsa — o'chirib ogohlantiraman\n"
        "👋 Kirish/chiqish xabarlarini o'chiraman\n\n"
        "📌 <b>Buyruqlar:</b>\n"
        "/allow @username — link ruxsat ro'yxatiga qo'shish\n"
        "/remove @username — ro'yxatdan o'chirish\n"
        "/list — ruxsat berilgan linklar\n\n"
        "➕ Meni guruhga admin qilib qo'shing!",
        parse_mode="HTML"
    )

async def allow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat
    user = update.message.from_user
    member = await context.bot.get_chat_member(chat.id, user.id)
    if not is_admin(member.status):
        await update.message.reply_text("⛔ Faqat adminlar bu buyruqdan foydalana oladi.")
        return
    if not context.args:
        await update.message.reply_text("❗ Format: <code>/allow @username</code>", parse_mode="HTML")
        return
    entry = context.args[0].lower()
    if chat.id not in whitelist:
        whitelist[chat.id] = []
    if entry not in whitelist[chat.id]:
        whitelist[chat.id].append(entry)
        await update.message.reply_text(f"✅ <code>{entry}</code> ruxsat ro'yxatiga qo'shildi.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"ℹ️ <code>{entry}</code> allaqachon ro'yxatda.", parse_mode="HTML")

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat
    user = update.message.from_user
    member = await context.bot.get_chat_member(chat.id, user.id)
    if not is_admin(member.status):
        await update.message.reply_text("⛔ Faqat adminlar bu buyruqdan foydalana oladi.")
        return
    if not context.args:
        await update.message.reply_text("❗ Format: <code>/remove @username</code>", parse_mode="HTML")
        return
    entry = context.args[0].lower()
    if chat.id in whitelist and entry in whitelist[chat.id]:
        whitelist[chat.id].remove(entry)
        await update.message.reply_text(f"🗑 <code>{entry}</code> ro'yxatdan o'chirildi.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"ℹ️ <code>{entry}</code> ro'yxatda yo'q.", parse_mode="HTML")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat
    allowed = whitelist.get(chat.id, [])
    if allowed:
        items = "\n".join([f"• <code>{a}</code>" for a in allowed])
        await update.message.reply_text(f"📋 <b>Ruxsat berilgan linklar:</b>\n\n{items}", parse_mode="HTML")
    else:
        await update.message.reply_text("📋 Hozircha ruxsat berilgan link yo'q.\n/allow @username orqali qo'shing.")

async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.from_user:
        return
    chat = message.chat
    user = message.from_user
    member = await context.bot.get_chat_member(chat.id, user.id)
    if is_admin(member.status):
        return
    text = message.text or message.caption or ""
    if not text:
        return
    user_id = user.id
    mention = f"<a href='tg://user?id={user_id}'>{user.first_name}</a>"
    links_found = LINK_PATTERN.findall(text)
    usernames_found = USERNAME_PATTERN.findall(text)
    if links_found or usernames_found:
        if not is_whitelisted(text, chat.id):
            try:
                await message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat.id,
                f"⚠️ {mention}, iltimos guruhda link yubormang!\n\n"
                f"❓ Muhim savolingiz bo'lsa — admin bilan bog'laning.",
                parse_mode="HTML"
            )

async def delete_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

def main():
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("allow", allow_command))
    bot_app.add_handler(CommandHandler("remove", remove_command))
    bot_app.add_handler(CommandHandler("list", list_command))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))
    bot_app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, check_message))
    bot_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, delete_service_message))
    bot_app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, delete_service_message))
    print("✅ Bot ishga tushdi!")
    bot_app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
