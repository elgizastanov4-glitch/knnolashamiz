import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    CallbackQuery
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =================== SOZLAMALAR ===================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6884014716
CHANNEL_USERNAME = "@kinolashamz"
# ================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

db = sqlite3.connect("kino.db")
cur = db.cursor()

# =================== DATABASE ===================
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    title TEXT,
    file_id TEXT
)
""")

db.commit()
# ==============================================

# =================== OBUNA TEKSHIRISH ===================
async def check_sub(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

# =================== START ===================
@dp.message(F.text.startswith("/start"))
async def start(msg: Message):
    user = msg.from_user
    args = msg.text.split(maxsplit=1)
    start_code = args[1] if len(args) > 1 else None

    kb_sub = InlineKeyboardBuilder()
    kb_sub.button(
        text="📢 Kanalga obuna bo‘lish",
        url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
    )
    kb_sub.button(
        text="✅ Tekshirish",
        callback_data="check_sub"
    )
    kb_sub.adjust(1)

    if not await check_sub(user.id):
        await msg.answer(
            f"Salom {user.full_name} 👋\n\n"
            f"Botdan foydalanish uchun rasmiy kanalimizga obuna bo‘lishingiz kerak ❗️",
            reply_markup=kb_sub.as_markup()
        )
        return

    cur.execute(
        "INSERT OR IGNORE INTO users VALUES (?,?)",
        (user.id, user.username)
    )
    db.commit()

    await bot.send_message(
        ADMIN_ID,
        f"🆕 Yangi foydalanuvchi\n"
        f"👤 {user.full_name}\n"
        f"🆔 {user.id}"
    )

    if start_code and start_code.isdigit():
        cur.execute(
            "SELECT title, file_id FROM movies WHERE code=?",
            (start_code,)
        )
        m = cur.fetchone()
        if m:
            await bot.send_video(
                user.id,
                m[1],
                caption=f"🎬 {m[0]}\n🔢 Kod: {start_code}"
            )

    kb_main = InlineKeyboardBuilder()
    kb_main.button(
        text="🔍 Inline qidiruv",
        switch_inline_query_current_chat=""
    )

    await msg.answer(
        f"🎬 Xush kelibsiz, {user.full_name}!\n\n"
        f"Inline qidiruv orqali kinolarni toping yoki 3 xonali kod yuboring.",
        reply_markup=kb_main.as_markup()
    )

# =================== RUN ===================
async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN topilmadi! .env ga qo‘shing")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
