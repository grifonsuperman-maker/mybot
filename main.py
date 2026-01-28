import os
import logging
import asyncio
import random
import string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp
from aiohttp import web

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_NICKNAME = "@ua_trends_save_bot" 
CHANNEL_ID = "@ua_trends_save"
# ------------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_links = {}

async def handle(request):
    return web.Response(text="Бот активен и проверен на ошибки!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(f"👋 Привет! Я качаю из **TikTok, Instagram и YouTube**.\nПросто пришли мне ссылку!")

@dp.message(F.text.contains("http"))
async def handle_link(message: types.Message):
    url = message.text.strip()
    user_links[message.from_user.id] = url
    
    # ПРАВИЛЬНАЯ ЛОГИКА ОПРЕДЕЛЕНИЯ СЕРВИСА
    if "instagram.com" in url:
        service = "Instagram"
    elif "youtube.com" in url or "youtu.be" in url:
        service = "YouTube"
    elif "tiktok.com" in url:
        service = "TikTok"
    else:
        service = "видео"

    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Скачать Видео", callback_data="dl_video")
    kb.button(text="🎵 Скачать Музыку", callback_data="dl_audio")
    await message.answer(f"Обнаружена ссылка на {service}. Что скачиваем?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: types.CallbackQuery):
    url = user_links.get(callback.from_user.id)
    choice = callback.data.split("_")[1]
    if not url: return

    status_msg = await callback.message.answer(f"⏳ Начинаю загрузку {choice}...")
    
    # Генерация уникального имени файла
    rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    ext = 'mp4' if choice == 'video' else 'm4a'
    file_path = f"file_{callback.from_user.id}_{rand_str}.{ext}"
    
    ydl_opts = {
        'outtmpl': file_path,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    # Настройки форматов и обход 403 ошибки
    if choice == 'video':
        ydl_opts['format'] = 'best[ext=mp4][filesize<50M]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    else:
        ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'

    # ДОПОЛНИТЕЛЬНЫЕ АРГУМЕНТЫ ДЛЯ YOUTUBE И INSTAGRAM
    if "youtube.com" in url or "youtu.be" in url:
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['web_embedded', 'tv', 'default']}}
    
    if "instagram.com" in url:
        ydl_opts['add_header'] = ['Referer: https://www.instagram.com/']

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        
        if os.path.exists(file_path):
            file = types.FSInputFile(file_path)
            if choice == 'video':
                await callback.message.answer_video(file, caption=f"✅ Готово!\n🤖 {BOT_NICKNAME}")
            else:
                await callback.message.answer_audio(file, caption=f"✅ Музыка готова!\n🤖 {BOT_NICKNAME}")
        else:
            raise Exception("Файл не найден")
            
    except Exception as e:
        logging.error(f"Error: {e}")
        await callback.message.answer("❌ Ошибка. Возможно, видео приватное, слишком тяжелое ( >50MB ) или сервис временно заблокировал сервер.")
    finally:
        if os.path.exists(file_path): 
            try: os.remove(file_path)
            except: pass
        await status_msg.delete()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
