import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

# --- ДАННЫЕ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@ua_trends_save" 
ADMIN_USERNAME = "@AlexUlqiora"     
MONO_BANK_URL = "https://send.monobank.ua/jar/qU4cLfSyf"  
CRYPTO_WALLET = "UQCEIz9srWZCOFgUHeh-ZHDFBc475ys8HFvkhF97h0S7Df0E"
BOT_NICKNAME = "@ua_trends_save_bot"
# --------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_links = {}

async def handle(request):
    return web.Response(text="Бот запущен во Франкфурте и готов к работе!")

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
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Реклама", callback_data="ads_info")
    kb.button(text="☕ Поддержать", callback_data="donate_info")
    kb.adjust(2)
    await message.answer(f"👋 Привет! Качаю из TikTok, Instagram и YouTube!\n\n📢 Канал: {CHANNEL_ID}", reply_markup=kb.as_markup())

@dp.message(F.text.contains("http"))
async def handle_link(message: types.Message):
    user_links[message.from_user.id] = message.text
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Видео", callback_data="dl_video")
    kb.button(text="🎵 Музыка", callback_data="dl_audio")
    await message.answer("Что скачиваем?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: types.CallbackQuery):
    url = user_links.get(callback.from_user.id)
    choice = callback.data.split("_")[1]
    if not url: return

    status_msg = await callback.message.answer(f"⏳ Загрузка {choice}...")
    ext = 'mp4' if choice == 'video' else 'm4a'
    file_path = f"file_{callback.from_user.id}.{ext}"
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best' if choice == 'video' else 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': file_path,
        'quiet': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        
        file = types.FSInputFile(file_path)
        if choice == 'video':
            await callback.message.answer_video(file, caption=f"✅ Готово!\n🤖 {BOT_NICKNAME}")
        else:
            await callback.message.answer_audio(file, caption=f"✅ Музыка готова!\n🤖 {BOT_NICKNAME}")
    except Exception as e:
        await callback.message.answer("❌ Ошибка. Возможно, ссылка приватная или регион заблокирован.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        await status_msg.delete()

async def main():
    await start_web_server()
    logging.info("🚀 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
