import os
import re
import logging
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ─── Keep Alive ───────────────────────────────────────────
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot ishlayapti!"

def run_flask():
    app_flask.run(host='0.0.0.0', port=8000)

def keep_alive():
    Thread(target=run_flask).start()

# ─── Sozlamalar ───────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Ogohlantirish hisoblagichi: {chat_id: {user_id: count}}
warnings = {}

# Whitelist: {chat_id: ["@iforafashion", "instagram.com/iforafashion", ...]}
whitelist = {}

# Reklama kalit so'zlari — faqat aniq reklama so'zlari
AD_KEYWORDS = [
    "реклама", "рекламa", "куплю", "продам",
    "подписывайтесь на канал", "подписывайтесь на наш",
    "заработок в интернете", "заработай легко",
    "крипто инвест", "crypto invest",
    "casino", "казино", "букмекер", "forex сигнал",
    "бизнес предложение", "biznes taklif",
    "100% гарантия", "100% kafolat",
    "реф ссылка", "referral link"
]

# Link pattern
LINK_PATTERN = re.compile(
    r'(https?://\S+|www\.\S+|t\.me/\S+)', re.IGNORECASE
)
USERNAME_PATTERN = re.compile(r'@(\w{5,})')

# ─── Yordamchi funksiyalar ────────────────────────────────
def is_admin(status: str) -> bool:
    return status in ("administrator", "creator")

def is_whitelisted(text: str, chat_id: int) -> bool:
    allowed = whitelist.get(chat_id, [])
    text_lower = text.lower()
    for entry in allowed:
        if entry.lower() in text_lower:
            return True
    return False

def get_start_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Ruxsat berilgan link qo'shish", callback_data="add_whitelist")],
        [InlineKeyboardButton("📋 Ruxsat berilgan linklar ro'yxati", callback_data="list_whitelist")],
        [InlineKeyboardButton("❌ Linkni ro'yxatdan o'chirish", callback_data="remove_whitelist")],
        [InlineKeyboardButton("ℹ️ Bot haqida", callback_data="about")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ─── /start komandasi ─────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Men <b>Yordamchi Admin</b> botiman!\n\n"
        "🛡 <b>Mening vazifalarim:</b>\n\n"
        "🔗 Ruxsatsiz link yuborilsa — o'chiraman\n"
        "📢 Reklama yuborilsa — o'chiraman\n"
        "⚠️ 3 marta qoida buzilsa — guruhdan chiqaraman\n"
        "👋 Kirish/chiqish xabarlarini o'chiraman\n\n"
        "⚙️ <b>Quyidagi tugmalardan sozlang:</b>",
        parse_mode="HTML",
        reply_markup=get_start_keyboard()
    )

# ─── Tugma bosilganda ─────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "about":
        await query.edit_message_text(
            "ℹ️ <b>Yordamchi Admin Bot</b>\n\n"
            "Guruhda tartibni saqlaydi:\n"
            "• Ruxsatsiz link va reklamalarni o'chiradi\n"
            "• 3 ogohlantirishdan keyin chiqaradi\n"
            "• Kirish/chiqish xabarlarini tozalaydi\n\n"
            "Sozlash uchun botga shaxsiy xabar yozing yoki\n"
            "guruhda /start ni bosing.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back")
            ]])
        )

    elif data == "add_whitelist":
        await query.edit_message_text(
            "➕ <b>Ruxsat beriladigan link yoki username qo'shish</b>\n\n"
            "Quyidagi formatda yuboring:\n\n"
            "<code>/allow @iforafashion</code>\n"
            "<code>/allow instagram.com/iforafashion</code>\n"
            "<code>/allow t.me/iforafashion</code>\n\n"
            "💡 Bir vaqtda bir dona qo'shiladi.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back")
            ]])
        )

    elif data == "list_whitelist":
        cid = query.message.chat.id
        allowed = whitelist.get(cid, [])
        if allowed:
            items = "\n".join([f"• <code>{a}</code>" for a in allowed])
            text = f"📋 <b>Ruxsat berilgan linklar:</b>\n\n{items}"
        else:
            text = "📋 Hozircha ruxsat berilgan link yo'q.\n\n/allow @username orqali qo'shing."
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back")
            ]])
        )

    elif data == "remove_whitelist":
        cid = query.message.chat.id
        allowed = whitelist.get(cid, [])
        if not allowed:
            await query.edit_message_text(
                "❌ Ro'yxat bo'sh. Avval /allow orqali qo'shing.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="back")
                ]])
            )
            return
        keyboard = [
            [InlineKeyboardButton(f"🗑 {a}", callback_data=f"del_{a}")]
            for a in allowed
        ]
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back")])
        await query.edit_message_text(
            "❌ <b>Qaysi linkni o'chirmoqchisiz?</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("del_"):
        entry = data[4:]
        cid = query.message.chat.id
        if cid in whitelist and entry in whitelist[cid]:
            whitelist[cid].remove(entry)
        await query.edit_message_text(
            f"✅ <code>{entry}</code> ro'yxatdan o'chirildi.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back")
            ]])
        )

    elif data == "back":
        await query.edit_message_text(
            "⚙️ <b>Yordamchi Admin — Boshqaruv paneli</b>\n\n"
            "Quyidagi tugmalardan foydalaning:",
            parse_mode="HTML",
            reply_markup=get_start_keyboard()
        )

# ─── /allow komandasi ─────────────────────────────────────
async def allow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat = update.message.chat

    member = await context.bot.get_chat_member(chat.id, user.id)
    if not is_admin(member.status):
        await update.message.reply_text("⛔ Faqat adminlar whitelist boshqara oladi.")
        return

    if not context.args:
        await update.message.reply_text(
            "❗ Format: <code>/allow @username</code> yoki <code>/allow instagram.com/sahifa</code>",
            parse_mode="HTML"
        )
        return

    entry = context.args[0].lower()
    if chat.id not in whitelist:
        whitelist[chat.id] = []

    if entry not in whitelist[chat.id]:
        whitelist[chat.id].append(entry)
        await update.message.reply_text(
            f"✅ <code>{entry}</code> ruxsat ro'yxatiga qo'shildi.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(f"ℹ️ <code>{entry}</code> allaqachon ro'yxatda.", parse_mode="HTML")

# ─── /remove komandasi ────────────────────────────────────
async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat = update.message.chat

    member = await context.bot.get_chat_member(chat.id, user.id)
    if not is_admin(member.status):
        await update.message.reply_text("⛔ Faqat adminlar whitelist boshqara oladi.")
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

# ─── Asosiy tekshirish ────────────────────────────────────
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

    violation = None
    reason = ""
    advice = ""

    # Link tekshirish
    links_found = LINK_PATTERN.findall(text)
    usernames_found = USERNAME_PATTERN.findall(text)

    if links_found or usernames_found:
        if not is_whitelisted(text, chat.id):
            violation = "link"
            reason = "🔗 Ruxsatsiz link yoki username yuborildi"
            advice = "Guruhda ruxsatsiz link yuborish taqiqlanadi."

    # Reklama tekshirish
    if not violation:
        lower_text = text.lower()
        for kw in AD_KEYWORDS:
            if kw in lower_text:
                violation = "ad"
                reason = "📢 Reklama xabari yuborildi"
                advice = "Guruhda reklama yuborish taqiqlanadi."
                break

    if violation:
        try:
            await message.delete()
        except Exception:
            pass

        if chat.id not in warnings:
            warnings[chat.id] = {}
        warnings[chat.id][user_id] = warnings[chat.id].get(user_id, 0) + 1
        warn_count = warnings[chat.id][user_id]

        if warn_count >= 3:
            try:
                await context.bot.ban_chat_member(chat.id, user_id)
                await context.bot.unban_chat_member(chat.id, user_id)
            except Exception:
                pass
            warnings[chat.id][user_id] = 0
            await context.bot.send_message(
                chat.id,
                f"🚫 {mention} guruhdan chiqarildi!\n"
                f"Sabab: 3 marta qoidani buzdi.",
                parse_mode="HTML"
            )
        else:
            remaining = 3 - warn_count
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

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("allow", allow_command))
    bot_app.add_handler(CommandHandler("remove", remove_command))
    bot_app.add_handler(CallbackQueryHandler(button_handler))

    bot_app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, check_message
    ))
    bot_app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.Document.ALL, check_message
    ))
    bot_app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS, delete_service_message
    ))
    bot_app.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER, delete_service_message
    ))

    print("✅ Bot ishga tushdi!")
    bot_app.run_polling()

if __name__ == "__main__":
    main()
