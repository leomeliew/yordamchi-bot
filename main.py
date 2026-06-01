import os
import re
import json
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

# ─── Logging ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ.get("BOT_TOKEN")

DATA_FILE = "bot_data.json"

# ─── Persistent storage ───────────────────────────────────
def load_data():
    global group_admins, whitelist, warnings
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
            # JSON keys are strings — convert back to int
            group_admins = {int(k): v for k, v in data.get("group_admins", {}).items()}
            whitelist    = {int(k): v for k, v in data.get("whitelist", {}).items()}
            warnings     = {int(k): {int(uid): cnt for uid, cnt in v.items()}
                            for k, v in data.get("warnings", {}).items()}
            logging.info(f"Ma'lumotlar yuklandi: {len(group_admins)} guruh, {len(whitelist)} whitelist")
        except Exception as e:
            logging.warning(f"Ma'lumot yuklashda xato: {e}")

def save_data():
    try:
        with open(DATA_FILE, "w") as f:
            json.dump({
                "group_admins": group_admins,
                "whitelist":    whitelist,
                "warnings":     warnings,
            }, f)
    except Exception as e:
        logging.warning(f"Ma'lumot saqlashda xato: {e}")

# ─── Ma'lumotlar ──────────────────────────────────────────
warnings     = {}   # {chat_id: {user_id: count}}
whitelist    = {}   # {chat_id: [entry, ...]}
group_admins = {}   # {chat_id: admin_user_id}
waiting_add  = {}   # {user_id: chat_id}  — link kutilayotgan adminlar

load_data()

LINK_PATTERN = re.compile(r'(https?://\S+|www\.\S+|t\.me/\S+)', re.IGNORECASE)
USERNAME_PATTERN = re.compile(r'@(\w{5,})')

# ─── Yordamchi ────────────────────────────────────────────
def is_admin_status(status):
    return status in ("administrator", "creator")

async def get_member_status(context, chat_id, user_id):
    try:
        m = await context.bot.get_chat_member(chat_id, user_id)
        return m.status
    except Exception:
        return "member"

def is_whitelisted(text, chat_id):
    for entry in whitelist.get(chat_id, []):
        if entry.lower() in text.lower():
            return True
    return False

def panel_keyboard(chat_id):
    count = len(whitelist.get(chat_id, []))
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Ruxsat link qo'shish", callback_data=f"add|{chat_id}")],
        [InlineKeyboardButton(f"📋 Ro'yxat ({count} ta)", callback_data=f"list|{chat_id}")],
        [InlineKeyboardButton("❌ Ro'yxatdan o'chirish", callback_data=f"delmenu|{chat_id}")],
    ])

async def send_panel(target_id, chat_id, context, title="Guruh"):
    await context.bot.send_message(
        target_id,
        f"⚙️ <b>{title}</b> — Boshqaruv paneli\n\nQuyidagi tugmalar orqali sozlang:",
        parse_mode="HTML",
        reply_markup=panel_keyboard(chat_id)
    )

async def notify_admin(context, chat_id, text):
    admin_id = group_admins.get(chat_id)
    if not admin_id:
        return
    try:
        await context.bot.send_message(admin_id, text, parse_mode="HTML")
    except Exception as e:
        logging.warning(f"Admin ga yuborib bo'lmadi: {e}")

# ─── /start ───────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat
    user = update.message.from_user

    if chat.type == "private":
        my_groups = [cid for cid, uid in group_admins.items() if uid == user.id]
        if my_groups:
            chat_id = my_groups[0]
            try:
                info = await context.bot.get_chat(chat_id)
                title = info.title
            except Exception:
                title = "Guruh"
            await send_panel(user.id, chat_id, context, title)
        else:
            await update.message.reply_text(
                "👋 Salom!\n\n"
                "Botni guruhga admin sifatida qo'shing,\n"
                "keyin guruhda /start bosing."
            )
        return

    if chat.type in ("group", "supergroup"):
        status = await get_member_status(context, chat.id, user.id)
        if not is_admin_status(status):
            try:
                await update.message.delete()
            except Exception:
                pass
            return

        group_admins[chat.id] = user.id
        save_data()
        logging.info(f"Admin saqlandi: chat={chat.id}, user={user.id}")

        sent_private = False
        try:
            await send_panel(user.id, chat.id, context, chat.title)
            sent_private = True
        except Exception as e:
            logging.warning(f"Shaxsiy panel yuborib bo'lmadi: {e}")

        if sent_private:
            try:
                await update.message.reply_text("✅ Boshqaruv paneli shaxsiy xabaringizga yuborildi!")
            except Exception:
                pass
        else:
            try:
                await update.message.reply_text(
                    f"⚙️ <b>{chat.title}</b> — Boshqaruv paneli",
                    parse_mode="HTML",
                    reply_markup=panel_keyboard(chat.id)
                )
            except Exception:
                pass

# ─── Callback tugmalar ────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    parts = data.split("|")
    action = parts[0]

    if action == "about":
        await query.edit_message_text(
            "ℹ️ Bot ruxsatsiz link yuborilsa o'chiradi,\n"
            "3 ogohlantirishdan keyin chiqaradi.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data=f"back|{parts[1]}")
            ]])
        )
        return

    chat_id = int(parts[1]) if len(parts) > 1 else None

    if action == "back":
        try:
            info = await context.bot.get_chat(chat_id)
            title = info.title
        except Exception:
            title = "Guruh"
        await query.edit_message_text(
            f"⚙️ <b>{title}</b> — Boshqaruv paneli\n\nQuyidagi tugmalar orqali sozlang:",
            parse_mode="HTML",
            reply_markup=panel_keyboard(chat_id)
        )

    elif action == "add":
        waiting_add[user.id] = chat_id
        await query.edit_message_text(
            "⚙️ <b>Boshqaruv paneli</b>\n\nRuxsat link qo'shish rejimi faol.",
            parse_mode="HTML"
        )
        await query.message.reply_text(
            "➕ <b>Ruxsat beriladigan link yoki username yuboring:</b>\n\n"
            "• <code>@sahifa</code>\n"
            "• <code>instagram.com/sahifa</code>\n"
            "• <code>t.me/sahifa</code>\n\n"
            "👇 Shu yerga yozing — men avtomatik qo'shaman.\n"
            "Bekor qilish: /cancel",
            parse_mode="HTML"
        )

    elif action == "list":
        allowed = whitelist.get(chat_id, [])
        if allowed:
            items = "\n".join([f"• <code>{a}</code>" for a in allowed])
            text = f"📋 <b>Ruxsat berilgan ({len(allowed)} ta):</b>\n\n{items}"
        else:
            text = "📋 Ro'yxat bo'sh."
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data=f"back|{chat_id}")
            ]])
        )

    elif action == "delmenu":
        allowed = whitelist.get(chat_id, [])
        if not allowed:
            await query.edit_message_text(
                "❌ Ro'yxat bo'sh.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data=f"back|{chat_id}")
                ]])
            )
            return
        keyboard = [
            [InlineKeyboardButton(f"🗑 {a}", callback_data=f"del|{chat_id}|{a}")]
            for a in allowed
        ]
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"back|{chat_id}")])
        await query.edit_message_text(
            "❌ O'chirmoqchi bo'lgan linkni tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif action == "del":
        entry = parts[2]
        if chat_id in whitelist and entry in whitelist[chat_id]:
            whitelist[chat_id].remove(entry)
            save_data()
        try:
            info = await context.bot.get_chat(chat_id)
            title = info.title
        except Exception:
            title = "Guruh"
        await query.edit_message_text(
            f"✅ <code>{entry}</code> o'chirildi.\n\n"
            f"⚙️ <b>{title}</b> — Boshqaruv paneli",
            parse_mode="HTML",
            reply_markup=panel_keyboard(chat_id)
        )

# ─── Shaxsiy xabarlar ─────────────────────────────────────
async def private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = (update.message.text or "").strip()

    if text == "/cancel":
        waiting_add.pop(user.id, None)
        await update.message.reply_text("❌ Bekor qilindi.")
        return

    if user.id in waiting_add:
        chat_id = waiting_add.pop(user.id)
        entry = text.lower().strip()

        if not entry:
            await update.message.reply_text("❗ Bo'sh xabar yuborildi.")
            return

        if chat_id not in whitelist:
            whitelist[chat_id] = []

        if entry not in whitelist[chat_id]:
            whitelist[chat_id].append(entry)
            save_data()
            try:
                info = await context.bot.get_chat(chat_id)
                title = info.title
            except Exception:
                title = "Guruh"
            await update.message.reply_text(
                f"✅ <code>{entry}</code> qo'shildi!\n\n"
                f"⚙️ <b>{title}</b> — Boshqaruv paneli",
                parse_mode="HTML",
                reply_markup=panel_keyboard(chat_id)
            )
        else:
            await update.message.reply_text(
                f"ℹ️ <code>{entry}</code> allaqachon ro'yxatda.",
                parse_mode="HTML"
            )
        return

    my_groups = [cid for cid, uid in group_admins.items() if uid == user.id]
    if my_groups:
        chat_id = my_groups[0]
        try:
            info = await context.bot.get_chat(chat_id)
            title = info.title
        except Exception:
            title = "Guruh"
        await send_panel(user.id, chat_id, context, title)
    else:
        await update.message.reply_text("Botni guruhga qo'shing va /start bosing.")

# ─── Guruhda xabar tekshirish ─────────────────────────────
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.from_user:
        return

    chat = message.chat
    user = message.from_user

    status = await get_member_status(context, chat.id, user.id)
    if is_admin_status(status):
        return

    text = message.text or message.caption or ""
    if not text:
        return

    links = LINK_PATTERN.findall(text)
    usernames = USERNAME_PATTERN.findall(text)

    if not links and not usernames:
        return

    if is_whitelisted(text, chat.id):
        return

    detail = links[0][:60] if links else f"@{usernames[0]}"
    mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

    try:
        await message.delete()
    except Exception:
        pass

    if chat.id not in warnings:
        warnings[chat.id] = {}
    warnings[chat.id][user.id] = warnings[chat.id].get(user.id, 0) + 1
    count = warnings[chat.id][user.id]
    save_data()

    if count >= 3:
        try:
            await context.bot.ban_chat_member(chat.id, user.id)
            await context.bot.unban_chat_member(chat.id, user.id)
        except Exception:
            pass
        warnings[chat.id][user.id] = 0
        save_data()

        await notify_admin(
            context, chat.id,
            f"🚫 <b>Ban</b> | {chat.title}\n"
            f"👤 {mention} (ID: <code>{user.id}</code>)\n"
            f"📎 <code>{detail}</code>\n"
            f"💬 <code>{text[:150]}</code>"
        )
    else:
        await notify_admin(
            context, chat.id,
            f"⚠️ <b>Ogohlantirish {count}/3</b> | {chat.title}\n"
            f"👤 {mention} (ID: <code>{user.id}</code>)\n"
            f"📎 <code>{detail}</code>\n"
            f"💬 <code>{text[:150]}</code>"
        )

# ─── Kirish xabari ────────────────────────────────────────
async def new_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = message.chat

    for new_member in message.new_chat_members:
        if new_member.id == context.bot.id:
            added_by = message.from_user
            if added_by:
                group_admins[chat.id] = added_by.id
                save_data()
                logging.info(f"Bot qo'shildi: chat={chat.id}, admin={added_by.id}")
                try:
                    await context.bot.send_message(
                        added_by.id,
                        f"👋 Salom <b>{added_by.first_name}</b>!\n\n"
                        f"✅ Bot <b>{chat.title}</b> ga qo'shildi.\n"
                        f"Hisobotlar va boshqaruv shu yerda bo'ladi.\n\n"
                        f"⚙️ Boshqaruv paneli:",
                        parse_mode="HTML",
                        reply_markup=panel_keyboard(chat.id)
                    )
                except Exception as e:
                    logging.warning(f"Admin ga yuborib bo'lmadi: {e}")
                    try:
                        await context.bot.send_message(
                            chat.id,
                            "✅ Bot sozlandi! Admin, menga shaxsiy /start yuboring.",
                        )
                    except Exception:
                        pass
    try:
        await message.delete()
    except Exception:
        pass

# ─── Chiqish xabari ───────────────────────────────────────
async def left_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

# ─── Main ─────────────────────────────────────────────────
def main():
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT, private_message
    ))
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, check_message
    ))
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & (filters.PHOTO | filters.VIDEO | filters.Document.ALL),
        check_message
    ))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member_handler
    ))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER, left_member_handler
    ))

    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
