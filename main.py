import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

# --- ТВОИ ДАННЫЕ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@ua_trends_save" 
ADMIN_USERNAME = "@AlexUlqiora"     
MONO_BANK_URL = "https://send.monobank.ua/jar/qU4cLfSyf"  
CRYPTO_WALLET = "UQCEIz9srWZCOFgUHeh-ZHDFBc475ys8HFvkhF97h0S7Df0E"
BOT_NICKNAME = "@Твой_Юзернейм_Бота" 
# -----------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_links = {}

async def handle(request):
    return web.Response(text="Бот активен!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def auto_post_trend():
    search_url = "ytsearch1:#trending #viral #shorts" 
    file_path = f"trend_{int(asyncio.get_event_loop().time())}.mp4"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'outtmpl': file_path, 'quiet': True, 'noplaylist': True,
        'nocheckcertificate': True, 'geo_bypass': True # Обход блокировок
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, search_url, download=True)
            video_title = info['entries'][0].get('title', '🔥 Трендовое видео')
        await bot.send_video(chat_id=CHANNEL_ID, video=types.FSInputFile(file_path), caption=f"🎬 {video_title}\n\n🤖 {BOT_NICKNAME}")
    except Exception as e:
        logging.error(f"Ошибка автопостинга: {e}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)

async def check_sub(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception: return False

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Реклама", callback_data="ads_info")
    kb.button(text="☕ Поддержать", callback_data="donate_info")
    kb.adjust(2)
    await message.answer(f"👋 Привет! Пришли ссылку, и я скачаю видео.\n📢 Канал: {CHANNEL_ID}", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "ads_info")
async def ads_handler(callback: types.CallbackQuery):
    await callback.message.answer(f"💎 Реклама: {ADMIN_USERNAME}")

@dp.callback_query(F.data == "donate_info")
async def donate_handler(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇦 Monobank", url=MONO_BANK_URL)
    kb.button(text="💰 Crypto", callback_data="show_crypto")
    await callback.message.answer("Поддержать проект:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "show_crypto")
async def crypto_handler(callback: types.CallbackQuery):
    await callback.message.answer(f"Адрес USDT/TON:\n`{CRYPTO_WALLET}`", parse_mode="Markdown")

@dp.message(F.text.contains("http"))
async def handle_link(message: types.Message):
    if not await check_sub(message.from_user.id):
        kb = InlineKeyboardBuilder().button(text="✅ Подписаться", url="https://t.me/ua_trends_save")
        return await message.answer(f"❌ Нужно подписаться на {CHANNEL_ID}!", reply_markup=kb.as_markup())
    user_links[message.from_user.id] = message.text
    kb = InlineKeyboardBuilder().button(text="🎬 Видео", callback_data="dl_video").button(text="🎵 Музыка", callback_data="dl_audio")
    await message.answer("Выбери формат:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: types.CallbackQuery):
    url = user_links.get(callback.from_user.id)
    choice = callback.data.split("_")[1]
    if not url: return
    msg = await callback.message.answer(f"⏳ Качаю {choice}...")
    file_path = f"file_{callback.from_user.id}.{'mp4' if choice == 'video' else 'mp3'}"
    
    # Новые настройки для обхода блокировок
    ydl_opts = {
        'format': 'best' if choice == 'video' else 'bestaudio/best',
        'outtmpl': file_path,
        'quiet': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'cookiefile': None # Можно будет добавить cookies, если TikTok заупрямится
    }
    if choice == 'audio':
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        if choice == 'video':
            await callback.message.answer_video(types.FSInputFile(file_path), caption=f"✅ Готово!\n🤖 {BOT_NICKNAME}")
        else:
            await callback.message.answer_audio(types.FSInputFile(file_path), caption=f"✅ Готово!\n🤖 {BOT_NICKNAME}")
    except Exception as e:
        logging.error(f"Download error: {e}")
        await callback.message.answer(f"❌ Ошибка. Возможно, видео защищено или сервер перегружен.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        await msg.delete()

async def main():
    await start_web_server()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(auto_post_trend, "interval", hours=6)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
