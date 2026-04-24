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

    # user bazaga
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

    # deep link orqali kino
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

# =================== TEKSHIRISH ===================
@dp.callback_query(F.data == "check_sub")
async def check_subscription(call: CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await start(
            Message(
                message_id=call.message.message_id,
                date=call.message.date,
                chat=call.message.chat,
                from_user=call.from_user,
                text="/start"
            )
        )
    else:
        await call.answer("❌ Avval kanalga obuna bo‘ling", show_alert=True)

# =================== INLINE QIDIRUV ===================
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
                description=f"Kodni yuborib tomosha qiling: {code}",
                input_message_content=InputTextMessageContent(
                    message_text=code
                )
            )
        )

    await query.answer(results, cache_time=1, is_personal=True)

# =================== KOD ORQALI KINO ===================
@dp.message(F.text.regexp(r"^\d{2,100}$"))
async def by_code(msg: Message):

    if not await check_sub(msg.from_user.id):
        await msg.answer("❗ Avval obuna bo‘ling")
        return

    code = msg.text.strip()

    cur.execute("SELECT id, title, file_id FROM movies WHERE code=?", (code,))
    movie = cur.fetchone()

    if not movie:
        await msg.answer("❌ Topilmadi")
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="💾 Saqlash", callback_data=f"save_movie_{movie[0]}")
    kb.adjust(1)

    await bot.send_video(
        msg.chat.id,
        movie[2],
        caption=f"🎬 {movie[1]}\n🔢 Kod: {code}",
        reply_markup=kb.as_markup()
    )
    if not await check_sub(msg.from_user.id):
        return

    cur.execute(
        "SELECT title, file_id FROM movies WHERE code=?",
        (msg.text,)
    )
    movie = cur.fetchone()

    if not movie:
        await msg.answer("❌ Bu kodda kino topilmadi")
        return

    await bot.send_video(
        msg.chat.id,
        movie[1],
        caption=f"🎬 {movie[0]}\n🔢 Kod: {msg.text}"
    )

# =================== ADMIN PANEL ===================
@dp.message(F.text == "/panel")
async def panel(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Kino qo‘shish", callback_data="add")
    kb.button(text="🗑 Kino o‘chirish", callback_data="del")
    kb.button(text="📊 Statistika", callback_data="stat")
    kb.button(text="📢 Xabar yuborish", callback_data="send")
    kb.adjust(1)

    await msg.answer("🛠 Admin panel", reply_markup=kb.as_markup())

# =================== KINO QO‘SHISH ===================
@dp.callback_query(F.data == "add")
async def add_info(call: CallbackQuery):
    await call.message.answer("🎬 Video yuboring:\n`001|Kino nomi`")

@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def add_movie(msg: Message):
    if not msg.caption or "|" not in msg.caption:
        await msg.answer("❗ Format: 001|Kino nomi")
        return

    code, title = msg.caption.split("|", 1)
    try:
        cur.execute(
            "INSERT INTO movies (code,title,file_id) VALUES (?,?,?)",
            (code.strip(), title.strip(), msg.video.file_id)
        )
        db.commit()
        await msg.answer("✅ Kino qo‘shildi")
    except:
        await msg.answer("❌ Bu kod mavjud")

# =================== KINO O‘CHIRISH ===================
@dp.callback_query(F.data == "del")
async def del_list(call: CallbackQuery):
    cur.execute("SELECT id,title FROM movies")
    movies = cur.fetchall()

    kb = InlineKeyboardBuilder()
    for mid, title in movies:
        kb.button(text=f"🗑 {title}", callback_data=f"d_{mid}")
    kb.adjust(1)

    await call.message.answer("O‘chirish uchun tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("d_"))
async def delete(call: CallbackQuery):
    mid = int(call.data.split("_")[1])
    cur.execute("DELETE FROM movies WHERE id=?", (mid,))
    db.commit()
    await call.message.edit_text("✅ O‘chirildi")

# =================== STATISTIKA ===================
@dp.callback_query(F.data == "stat")
async def stat(call: CallbackQuery):
    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM movies")
    movies = cur.fetchone()[0]

    await call.message.answer(
        f"📊 Statistika\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"🎬 Kinolar: {movies}"
    )

# =================== BROADCAST ===================
@dp.callback_query(F.data == "send")
async def send_info(call: CallbackQuery):
    await call.message.answer("📢 Yuboriladigan xabarni yozing:")

@dp.message(F.from_user.id == ADMIN_ID)
async def broadcast(msg: Message):
    if msg.text.startswith("/"):
        return

    cur.execute("SELECT user_id FROM users")
    for (uid,) in cur.fetchall():
        try:
            await bot.send_message(uid, msg.text)
        except:
            pass

    await msg.answer("✅ Xabar yuborildi")

# =================== RUN ===================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
