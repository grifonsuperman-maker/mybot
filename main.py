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
BOT_NICKNAME = "@ua_trends_save_bot" # ЗАМЕНИ НА СВОЙ НИК БОТА
# -----------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_links = {}

async def handle(request): return web.Response(text="Бот онлайн!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, "0.0.0.0", port).start()

async def auto_post_trend():
    file_path = f"trend_{int(asyncio.get_event_loop().time())}.mp4"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'outtmpl': file_path, 'quiet': True, 'noplaylist': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, "ytsearch1:#trending #shorts", download=True)
            title = info['entries'][0].get('title', 'Тренд')
        await bot.send_video(chat_id=CHANNEL_ID, video=types.FSInputFile(file_path), caption=f"🎬 {title}\n🤖 {BOT_NICKNAME}")
    except Exception: pass
    finally:
        if os.path.exists(file_path): os.remove(file_path)

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Реклама", callback_data="ads")
    kb.button(text="☕ Поддержать", callback_data="donate")
    kb.adjust(2)
    await message.answer(f"👋 Привет! Кидай ссылку TikTok/YouTube!\n📢 Канал: {CHANNEL_ID}", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "ads")
async def ads(c: types.CallbackQuery): await c.message.answer(f"💎 Реклама: {ADMIN_USERNAME}")

@dp.callback_query(F.data == "donate")
async def donate(c: types.CallbackQuery):
    kb = InlineKeyboardBuilder().button(text="🇺🇦 Monobank", url=MONO_BANK_URL).button(text="💰 Crypto", callback_data="crypto")
    await c.message.answer("Поддержать:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "crypto")
async def crypto(c: types.CallbackQuery): await c.message.answer(f"Адрес:\n`{CRYPTO_WALLET}`", parse_mode="Markdown")

@dp.message(F.text.contains("http"))
async def link_handler(message: types.Message):
    user_links[message.from_user.id] = message.text
    kb = InlineKeyboardBuilder().button(text="🎬 Видео", callback_data="dl_video").button(text="🎵 Музыка", callback_data="dl_audio")
    await message.answer("Качаем?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dl_"))
async def download(callback: types.CallbackQuery):
    url = user_links.get(callback.from_user.id)
    choice = callback.data.split("_")[1]
    if not url: return
    
    status_msg = await callback.message.answer("⏳ Загрузка началась (может занять 1-2 мин)...")
    file_path = f"dl_{callback.from_user.id}.{'mp4' if choice == 'video' else 'mp3'}"
    
    ydl_opts = {
        'format': 'best' if choice == 'video' else 'bestaudio/best',
        'outtmpl': file_path,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'quiet': True
    }
    if choice == 'audio':
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        file = types.FSInputFile(file_path)
        if choice == 'video':
            await callback.message.answer_video(file, caption=f"✅ Готово!\n🤖 {BOT_NICKNAME}")
        else:
            await callback.message.answer_audio(file, caption=f"✅ Готово!\n🤖 {BOT_NICKNAME}")
    except Exception as e:
        logging.error(f"Error: {e}")
        await callback.message.answer("❌ Ошибка. Сервис временно заблокирован платформой. Попробуй позже.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        await status_msg.delete()

async def main():
    await start_web_server()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(auto_post_trend, "interval", hours=6)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
