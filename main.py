import asyncio
import aiohttp
import os
import logging
import http.server
import socketserver
import threading
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- БАЗА ДАННЫХ (SQLite) ---
# На Render файл .db будет удаляться при перезагрузке, 
# но это не вызовет ошибок, таблицы создадутся заново.
def init_db():
    try:
        conn = sqlite3.connect("bot_data.db")
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
        cur.execute("CREATE TABLE IF NOT EXISTS music_cache (msg_id INTEGER PRIMARY KEY, music_url TEXT, title TEXT)")
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"DB Error: {e}")

def add_user(user_id):
    try:
        with sqlite3.connect("bot_data.db") as conn:
            conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    except: pass

def save_music(msg_id, url, title):
    try:
        with sqlite3.connect("bot_data.db") as conn:
            conn.execute("INSERT OR REPLACE INTO music_cache (msg_id, music_url, title) VALUES (?, ?, ?)", (msg_id, url, title))
    except: pass

def get_music(msg_id):
    try:
        with sqlite3.connect("bot_data.db") as conn:
            return conn.execute("SELECT music_url, title FROM music_cache WHERE msg_id = ?", (msg_id,)).fetchone()
    except: return None

init_db()

# --- СЕРВЕР ДЛЯ KEEP-ALIVE (RENDER) ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 8000))
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            logging.info(f"🌐 Keep-alive server running on port {port}")
            httpd.serve_forever()
    except Exception as e:
        logging.error(f"Server Error: {e}")

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = os.getenv('BOT_TOKEN', '8445491297:AAFmePw4OSKHLWDSIm86pgWdYjjiQIBZiJg')
CHANNEL_ID = '@ua_trends_save'
CHANNEL_URL = 'https://t.me/ua_trends_save'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Хранилище сессии
session_holder = {"session": None}

async def get_session():
    if session_holder["session"] is None or session_holder["session"].closed:
        # Увеличиваем таймаут до 30 секунд для стабильности
        timeout = aiohttp.ClientTimeout(total=30)
        session_holder["session"] = aiohttp.ClientSession(timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        })
    return session_holder["session"]

async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    add_user(message.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="1. Подписаться 📢", url=CHANNEL_URL))
    builder.row(types.InlineKeyboardButton(text="2. Я подписался ✅", callback_data="verify"))
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        "Пришли ссылку на TikTok, и я скачаю видео, фото или музыку.", 
        reply_markup=builder.as_markup()
    )

@dp.message(Command("stats"))
async def stats(message: types.Message):
    # Команда только для админа (если хочешь ограничить)
    try:
        with sqlite3.connect("bot_data.db") as conn:
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        await message.answer(f"📊 Всего пользователей в базе: {count}")
    except:
        await message.answer("📊 Ошибка доступа к базе данных.")

@dp.callback_query(F.data == "verify")
async def verify(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.edit_text("✅ Доступ разрешен! Просто пришли мне ссылку на TikTok.")
    else:
        await call.answer("❌ Сначала подпишись на канал!", show_alert=True)

@dp.message(F.text.regexp(r'(https?://[^\s]+tiktok\.com/[^\s]+)'))
async def handle_tiktok(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer("⚠️ Сначала подпишись на наш канал: @ua_trends_save")
        return

    status_msg = await message.answer("⌛ Загрузка...")
    try:
        session = await get_session()
        # Используем актуальное API Tiklydown
        async with session.get(f"https://api.tiklydown.eu.org/api/download?url={message.text.strip()}") as resp:
            if resp.status != 200:
                await message.answer("❌ Ошибка API. Возможно, видео удалено или ссылка неверна.")
                return
            
            data = await resp.json()
            
            # Извлекаем музыку
            m_info = data.get('music', {})
            m_url = m_info.get('play_url') or m_info.get('playUrl')
            m_title = m_info.get('title', 'audio')

            # Сценарий 1: ВИДЕО
            video_url = data.get('video', {}).get('noWatermark')
            if video_url:
                sent = await message.answer_video(video_url, caption="✅ @ua_trends_save")
                if m_url:
                    save_music(sent.message_id, m_url, m_title)
                    kb = InlineKeyboardBuilder()
                    kb.row(types.InlineKeyboardButton(text="🎵 Скачать музыку (MP3)", callback_data=f"audio_{sent.message_id}"))
                    await sent.edit_reply_markup(reply_markup=kb.as_markup())
                return

            # Сценарий 2: ФОТО (Слайдшоу)
            images = data.get('images')
            if images:
                # Ограничение Telegram на альбом - 10 фото
                media = [types.InputMediaPhoto(media=img['url'], caption="📸 Слайдшоу @ua_trends_save" if i==0 else "") 
                         for i, img in enumerate(images[:10])]
                await message.answer_media_group(media)
                
                if m_url:
                    # Для фото привязываем музыку к ID сообщения со ссылкой
                    save_music(message.message_id, m_url, m_title)
                    kb = InlineKeyboardBuilder()
                    kb.row(types.InlineKeyboardButton(text="🎵 Скачать музыку (MP3)", callback_data=f"audio_{message.message_id}"))
                    await message.answer("🎶 Музыка из этого слайдшоу:", reply_markup=kb.as_markup())
                return

            await message.answer("❌ Не удалось найти видео или фото. Попробуйте другую ссылку.")

    except Exception as e:
        logging.error(f"Process Error: {e}")
        await message.answer("❌ Ошибка при скачивании. Попробуйте еще раз.")
    finally:
        try:
            await status_msg.delete()
        except:
            pass

@dp.callback_query(F.data.startswith("audio_"))
async def send_audio(call: types.CallbackQuery):
    try:
        msg_id = int(call.data.split("_")[1])
        music_data = get_music(msg_id)
        
        if music_data:
            await call.answer("Отправляю...")
            await call.message.answer_audio(music_data[0], title=f"{music_data[1]} @ua_trends_save")
        else:
            await call.answer("❌ Файл не найден в кэше. Пришлите ссылку заново.", show_alert=True)
    except Exception as e:
        logging.error(f"Audio Error: {e}")
        await call.answer("❌ Ошибка загрузки аудио.", show_alert=True)

async def main():
    logging.info("🚀 Бот полностью запущен и готов к работе!")
    try:
        await dp.start_polling(bot)
    finally:
        session = await get_session()
        await session.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

