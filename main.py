import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =================== SOZLAMALAR ===================
BOT_TOKEN = "8335969395:AAElrgYcf3vkFDoNi7st_NFAjnTmeUpeZ8U"
ADMIN_ID = 6884014716
CHANNEL_USERNAME = "@kinolashamz"
START_IMAGE_PATH = "start.jpg"

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# =================== DATABASE ======================
DB_DIR = "/tmp/data"  # ✅ tuzatildi
os.makedirs(DB_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, "kino.db")

db = sqlite3.connect(DB_PATH)
cur = db.cursor()

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

cur.execute("""
CREATE TABLE IF NOT EXISTS serials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    title TEXT,
    file_id TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS saved (
    user_id INTEGER,
    movie_id TEXT
)
""")
db.commit()

# =================== OBUNA ===================
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

dp.data = {}

# =================== START ===================
@dp.message(F.text.startswith("/start"))
async def start(msg: Message):
    args = msg.text.split()
    code = args[1] if len(args) > 1 else None

    if not await check_sub(msg.from_user.id):
        kb = InlineKeyboardBuilder()
        kb.button(text="📢 Obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
        kb.button(text="✅ Tekshirish", callback_data="check_sub")
        kb.adjust(2)
        await msg.answer("❗ Avval kanalga obuna bo‘ling", reply_markup=kb.as_markup())
        return

    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)",
                (msg.from_user.id, msg.from_user.username))
    db.commit()

    if code:
        cur.execute("SELECT title,file_id FROM movies WHERE code=?", (code,))
        movie = cur.fetchone()
        if movie:
            await bot.send_video(msg.chat.id, movie[1], caption=f"🎬 {movie[0]}")
            return

    await msg.answer("👋 Xush kelibsiz!")

# =================== INLINE ===================
@dp.inline_query()
async def inline_search(query: InlineQuery):
    text = query.query
    results = []

    cur.execute("SELECT id,title,file_id FROM movies WHERE title LIKE ?", (f"%{text}%",))
    for m in cur.fetchall():
        results.append(
            InlineQueryResultCachedVideo(
                id=str(m[0]),
                video_file_id=m[2],
                title=m[1]
            )
        )

    await query.answer(results, cache_time=1)

# =================== KOD ===================
@dp.message(F.text.regexp(r"^\d{1,15}$"))
async def by_code(msg: Message):
    cur.execute("SELECT title,file_id FROM movies WHERE code=?", (msg.text,))
    movie = cur.fetchone()
    if movie:
        await bot.send_video(msg.chat.id, movie[1], caption=f"🎬 {movie[0]}")
    else:
        await msg.answer("❌ Topilmadi")

# =================== ADMIN PANEL ===================
@dp.message(F.from_user.id == ADMIN_ID, F.text == "/admin")
async def admin_panel(msg: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Qo‘shish", callback_data="add")
    kb.button(text="🗑 O‘chirish", callback_data="del")
    kb.button(text="✏️ Tahrirlash", callback_data="edit")
    kb.button(text="📃 Ro‘yxat", callback_data="list")
    kb.adjust(2)
    await msg.answer("Admin panel", reply_markup=kb.as_markup())

# =================== ADMIN BOSHQARUV ===================
@dp.callback_query()
async def admin_actions(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    if call.data == "add":
        dp.data["mode"] = "add"
        await call.message.answer("Video yubor: kod|nom")

    elif call.data == "del":
        dp.data["mode"] = "del"
        await call.message.answer("Kod yubor")

    elif call.data == "edit":
        dp.data["mode"] = "edit"
        await call.message.answer("Kod|yangi nom")

    elif call.data == "list":
        cur.execute("SELECT code,title FROM movies")
        data = cur.fetchall()
        text = "\n".join([f"{c} - {t}" for c, t in data]) or "Bo‘sh"
        await call.message.answer(text)

# =================== ADMIN UNIVERSAL ===================
@dp.message(F.from_user.id == ADMIN_ID)
async def admin_handler(msg: Message):
    mode = dp.data.get("mode")

    if mode == "add" and msg.video:
        code, title = msg.caption.split("|")
        cur.execute("INSERT INTO movies (code,title,file_id) VALUES (?,?,?)",
                    (code.strip(), title.strip(), msg.video.file_id))
        db.commit()
        await msg.answer("✅ Qo‘shildi")
        dp.data["mode"] = None

    elif mode == "del":
        cur.execute("DELETE FROM movies WHERE code=?", (msg.text,))
        db.commit()
        await msg.answer("✅ O‘chirildi")
        dp.data["mode"] = None

    elif mode == "edit":
        code, title = msg.text.split("|")
        cur.execute("UPDATE movies SET title=? WHERE code=?",
                    (title.strip(), code.strip()))
        db.commit()
        await msg.answer("✅ Tahrirlandi")
        dp.data["mode"] = None

# =================== RUN ===================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
