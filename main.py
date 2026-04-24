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
BOT_TOKEN = "8335969395:AAElrgYcf3vkFDoNi7st_NFAjnTmeUpeZ8U"
ADMIN_ID = 6884014716
CHANNEL_USERNAME = "@kinolashamz"
# ================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# 🔥 MUHIM: /tmp ga yozamiz
DB_PATH = "/tmp/kino.db"

db = sqlite3.connect(DB_PATH)
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
            f"Botdan foydalanish uchun kanalga obuna bo‘ling ❗️",
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
        f"🆕 Yangi foydalanuvchi\n👤 {user.full_name}\n🆔 {user.id}"
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
        f"🎬 Xush kelibsiz, {user.full_name}!",
        reply_markup=kb_main.as_markup()
    )

# =================== TEKSHIRISH ===================
@dp.callback_query(F.data == "check_sub")
async def check_subscription(call: CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await start(call.message)
    else:
        await call.answer("❌ Obuna bo‘ling", show_alert=True)

# =================== INLINE ===================
@dp.inline_query()
async def inline_search(query: InlineQuery):
    text = query.query.strip()

    cur.execute(
        "SELECT code, title FROM movies WHERE title LIKE ? LIMIT 50",
        (f"%{text}%",)
    )
    movies = cur.fetchall()

    results = []
    for code, title in movies:
        results.append(
            InlineQueryResultArticle(
                id=code,
                title=title,
                description=f"Kod: {code}",
                input_message_content=InputTextMessageContent(
                    message_text=code
                )
            )
        )

    await query.answer(results, cache_time=1)

# =================== KOD ===================
@dp.message(F.text.regexp(r"^\d{3}$"))
async def by_code(msg: Message):
    if not await check_sub(msg.from_user.id):
        return

    cur.execute(
        "SELECT title, file_id FROM movies WHERE code=?",
        (msg.text,)
    )
    movie = cur.fetchone()

    if not movie:
        await msg.answer("❌ Topilmadi")
        return

    await bot.send_video(
        msg.chat.id,
        movie[1],
        caption=f"🎬 {movie[0]}\n🔢 {msg.text}"
    )

# =================== ADMIN ===================
@dp.message(F.text == "/panel")
async def panel(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Kino qo‘shish", callback_data="add")
    kb.adjust(1)

    await msg.answer("Admin panel", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "add")
async def add_info(call: CallbackQuery):
    await call.message.answer("Video yubor: 001|Kino nomi")

@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def add_movie(msg: Message):
    if not msg.caption or "|" not in msg.caption:
        await msg.answer("Format xato")
        return

    code, title = msg.caption.split("|", 1)

    try:
        cur.execute(
            "INSERT INTO movies (code,title,file_id) VALUES (?,?,?)",
            (code.strip(), title.strip(), msg.video.file_id)
        )
        db.commit()
        await msg.answer("✅ Qo‘shildi")
    except:
        await msg.answer("❌ Kod mavjud")

# =================== RUN ===================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
