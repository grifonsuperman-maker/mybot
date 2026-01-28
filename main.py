import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

# --- ТВОИ ДАННЫЕ (ПРОВЕРЕНО) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@ua_trends_save" 
ADMIN_USERNAME = "@AlexUlqiora"     
MONO_BANK_URL = "https://send.monobank.ua/jar/qU4cLfSyf"  
CRYPTO_WALLET = "UQCEIz9srWZCOFgUHeh-ZHDFBc475ys8HFvkhF97h0S7Df0E"
BOT_NICKNAME = "@ua_trends_save_bot" # ЗАМЕНИ НА СТОПРОЦЕНТНЫЙ НИК БОТА
# -----------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_links = {}

# Веб-сервер для "обмана" Render
async def handle(request):
    return web.Response(text="Бот активен и качает всё!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# Автопостинг трендов
async def auto_post_trend():
    logging.info("🔎 Ищу тренды для канала...")
    file_path = f"trend_{int(asyncio.get_event_loop().time())}.mp4"
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': file_path,
        'quiet': True,
        'noplaylist': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, "ytsearch1:#trending #viral #shorts", download=True)
            video_title = info['entries'][0].get('title', '🔥 Трендовое видео')
        await bot.send_video(chat_id=CHANNEL_ID, video=types.FSInputFile(file_path), caption=f"🎬 {video_title}\n\n🤖 {BOT_NICKNAME}")
    except Exception as e:
        logging.error(f"Ошибка автопостинга: {e}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Реклама", callback_data="ads_info")
    kb.button(text="☕ Поддержать", callback_data="donate_info")
    kb.adjust(2)
    await message.answer(
        f"👋 Привет! Я качаю видео и музыку без знаков.\n\n"
        f"📢 Подпишись на канал: {CHANNEL_ID}",
        reply_markup=kb.as_markup()
    )

@dp.callback_query(F.data == "ads_info")
async def ads_handler(callback: types.CallbackQuery):
    await callback.message.answer(f"💎 По вопросам рекламы: {ADMIN_USERNAME}")

@dp.callback_query(F.data == "donate_info")
async def donate_handler(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇦 Monobank", url=MONO_BANK_URL)
    kb.button(text="💰 Crypto", callback_data="show_crypto")
    await callback.message.answer("Выберите способ поддержки:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "show_crypto")
async def crypto_handler(callback: types.CallbackQuery):
    await callback.message.answer(f"Адрес USDT/TON:\n`{CRYPTO_WALLET}`", parse_mode="Markdown")

@dp.message(F.text.contains("http"))
async def handle_link(message: types.Message):
    user_links[message.from_user.id] = message.text
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Видео", callback_data="dl_video")
    kb.button(text="🎵 Музыка", callback_data="dl_audio")
    await message.answer("В каком формате сохранить?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: types.CallbackQuery):
    url = user_links.get(callback.from_user.id)
    choice = callback.data.split("_")[1]
    if not url: return

    status_msg = await callback.message.answer(f"⏳ Начинаю загрузку {choice}...")
    
    # Для аудио используем m4a, чтобы не зависеть от ffmpeg
    ext = 'mp4' if choice == 'video' else 'm4a'
    file_path = f"file_{callback.from_user.id}.{ext}"
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best' if choice == 'video' else 'bestaudio/best',
        'outtmpl': file_path,
        'quiet': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        
        file = types.FSInputFile(file_path)
        if choice == 'video':
            await callback.message.answer_video(file, caption=f"✅ Готово!\n🤖 {BOT_NICKNAME}")
        else:
            await callback.message.answer_audio(file, caption=f"✅ Музыка извлечена!\n🤖 {BOT_NICKNAME}")
            
    except Exception as e:
        logging.error(f"Download error: {e}")
        await callback.message.answer("❌ Ошибка загрузки. Возможно, формат не поддерживается.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        await status_msg.delete()

async def main():
    await start_web_server()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(auto_post_trend, "interval", hours=6)
    scheduler.start()
    logging.info("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
