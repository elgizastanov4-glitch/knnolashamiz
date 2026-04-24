import asyncio
import sqlite3
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
    file_id TEXT,
    type TEXT DEFAULT 'film'
)
""")

db.commit()

# =================== OBUNA ===================
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

    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    kb.button(text="✅ Tekshirish", callback_data="check_sub")
    kb.adjust(1)

    if not await check_sub(user.id):
        await msg.answer("Obuna bo‘ling ❗️", reply_markup=kb.as_markup())
        return

    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (user.id, user.username))
    db.commit()

    await msg.answer("🎬 Kino botga xush kelibsiz!")


# =================== CHECK ===================
@dp.callback_query(F.data == "check_sub")
async def check(call: CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
    else:
        await call.answer("Obuna bo‘ling ❗️", show_alert=True)


# =================== INLINE ===================
@dp.inline_query()
async def inline(query: InlineQuery):
    text = query.query.strip()

    cur.execute("SELECT code,title FROM movies WHERE title LIKE ? LIMIT 20", (f"%{text}%",))
    data = cur.fetchall()

    results = [
        InlineQueryResultArticle(
            id=code,
            title=title,
            input_message_content=InputTextMessageContent(message_text=code)
        )
        for code, title in data
    ]

    await query.answer(results, cache_time=1, is_personal=True)


# =================== CODE ===================
@dp.message(F.text.regexp(r"^\d{2,6}$"))
async def by_code(msg: Message):
    code = msg.text.strip()

    cur.execute("SELECT title,file_id,type FROM movies WHERE code=?", (code,))
    movie = cur.fetchone()

    if not movie:
        await msg.answer("❌ Topilmadi")
        return

    title, file_id, mtype = movie

    await bot.send_video(
        msg.chat.id,
        file_id,
        caption=f"🎬 {title}\n📂 {mtype}\n🔢 {code}"
    )


# =================== PANEL ===================
@dp.message(F.text == "/panel")
async def panel(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Kino qo‘shish", callback_data="add")
    kb.button(text="🗑 O‘chirish", callback_data="del")
    kb.button(text="✏ Edit", callback_data="edit")
    kb.button(text="📋 Ro‘yxat", callback_data="list")
    kb.button(text="📊 Statistika", callback_data="stat")
    kb.adjust(1)

    await msg.answer("🛠 Panel", reply_markup=kb.as_markup())


# =================== ADD ===================
@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def add(msg: Message):
    if not msg.caption or "|" not in msg.caption:
        await msg.answer("001|film|Nomi")
        return

    code, mtype, title = msg.caption.split("|", 2)

    try:
        cur.execute(
            "INSERT INTO movies (code,title,file_id,type) VALUES (?,?,?,?)",
            (code, title, msg.video.file_id, mtype)
        )
        db.commit()
        await msg.answer("✅ Qo‘shildi")
    except:
        await msg.answer("❌ Kod bor")


# =================== EDIT ===================
@dp.message(F.text.startswith("/edit"))
async def edit(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    parts = msg.text.split(maxsplit=2)

    if len(parts) < 3:
        await msg.answer("/edit 001 yangi nom")
        return

    code = parts[1]
    title = parts[2]

    cur.execute("UPDATE movies SET title=? WHERE code=?", (title, code))
    db.commit()

    await msg.answer("✏ Yangilandi")


# =================== LIST ===================
@dp.message(F.text == "/list")
async def list_movies(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    cur.execute("SELECT code,title,type FROM movies")
    data = cur.fetchall()

    text = "📋 RO‘YXAT:\n\n"
    for c, t, tp in data:
        text += f"{c} | {tp} | {t}\n"

    await msg.answer(text)


# =================== DELETE ===================
@dp.callback_query(F.data == "del")
async def delete_list(call: CallbackQuery):
    cur.execute("SELECT id,title FROM movies")
    data = cur.fetchall()

    kb = InlineKeyboardBuilder()
    for i, t in data:
        kb.button(text=t, callback_data=f"d_{i}")
    kb.adjust(1)

    await call.message.answer("O‘chirish:", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("d_"))
async def delete(call: CallbackQuery):
    mid = int(call.data.split("_")[1])
    cur.execute("DELETE FROM movies WHERE id=?", (mid,))
    db.commit()
    await call.message.edit_text("O‘chirildi")


# =================== STAT ===================
@dp.callback_query(F.data == "stat")
async def stat(call: CallbackQuery):
    cur.execute("SELECT COUNT(*) FROM users")
    u = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM movies")
    m = cur.fetchone()[0]

    await call.message.answer(f"👥 {u}\n🎬 {m}")


# =================== BROADCAST ===================
@dp.message(F.text.startswith("/sendall"))
async def broadcast(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    text = msg.text.replace("/sendall", "")

    cur.execute("SELECT user_id FROM users")
    for (uid,) in cur.fetchall():
        try:
            await bot.send_message(uid, text)
        except:
            pass

    await msg.answer("Yuborildi")


# =================== RUN ===================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
