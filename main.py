import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp
from apscheduler.schedulers.asyncio import AsyncIOScheduler # Исправлено: заглавная O
from aiohttp import web

# --- ТВОИ ДАННЫЕ (УЖЕ ВШИТЫ) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@ua_trends_save" 
ADMIN_USERNAME = "@AlexUlqiora"     
MONO_BANK_URL = "https://send.monobank.ua/jar/qU4cLfSyf"  
CRYPTO_WALLET = "UQCEIz9srWZCOFgUHeh-ZHDFBc475ys8HFvkhF97h0S7Df0E"
# ВПИШИ НИЖЕ ЮЗЕРНЕЙМ СВОЕГО БОТА (например, @MyBot)
BOT_NICKNAME = "@Твой_Юзернейм_Бота" 
# -----------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_links = {}

# --- ОБМАНКА ДЛЯ RENDER (БЕСПЛАТНЫЙ ТАРИФ) ---
async def handle(request):
    return web.Response(text="Бот активен и работает!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Веб-сервер запущен на порту {port}")

# --- АВТОПОСТИНГ ТРЕНДОВ ---
async def auto_post_trend():
    logging.info("🔎 Поиск трендов для канала...")
    search_url = "ytsearch1:#trending #viral #shorts" 
    file_path = f"trend_{int(asyncio.get_event_loop().time())}.mp4"
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'outtmpl': file_path, 'quiet': True, 'noplaylist': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, search_url, download=True)
            video_title = info['entries'][0].get('title', '🔥 Трендовое видео')
            
        input_file = types.FSInputFile(file_path)
        caption_text = (
            f"🌟 **Мировой тренд дня**\n\n"
            f"🎬 {video_title}\n\n"
            f"🤖 Качай без знаков: {BOT_NICKNAME}\n"
            f"📢 Наш канал: {CHANNEL_ID}"
        )
        await bot.send_video(chat_id=CHANNEL_ID, video=input_file, caption=caption_text, parse_mode="Markdown")
        logging.info("✅ Автопост отправлен в канал!")
    except Exception as e:
        logging.error(f"❌ Ошибка автопостинга: {e}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)

# --- ПРОВЕРКА ПОДПИСКИ ---
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
    await message.answer(
        f"👋 Привет! Я твой AI Помощник.\n\n"
        f"📥 Пришли ссылку, и я скачаю видео без знаков.\n"
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
    if not await check_sub(message.from_user.id):
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Подписаться", url=f"https://t.me/ua_trends_save")
        return await message.answer(f"❌ Нужно подписаться на {CHANNEL_ID}!", reply_markup=kb.as_markup())

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

    msg = await callback.message.edit_text(f"⏳ Начинаю загрузку {choice}...")
    file_path = f"file_{callback.from_user.id}.{'mp4' if choice == 'video' else 'mp3'}"
    
    ydl_opts = {'format': 'best' if choice == 'video' else 'bestaudio/best', 'outtmpl': file_path, 'quiet': True}
    if choice == 'audio':
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        
        caption_text = f"✅ Готово! \n\n🤖 Бот: {BOT_NICKNAME}\n📢 Канал: {CHANNEL_ID}"
        kb = InlineKeyboardBuilder().button(text="☕ Поддержать проект", url=MONO_BANK_URL)

        if choice == 'video':
            await callback.message.answer_video(types.FSInputFile(file_path), caption=caption_text, reply_markup=kb.as_markup())
        else:
            await callback.message.answer_audio(types.FSInputFile(file_path), caption=caption_text, reply_markup=kb.as_markup())
    except Exception:
        await callback.message.answer("❌ Ошибка загрузки.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        await msg.delete()

async def main():
    await start_web_server() # Обманка порта
    
    scheduler = AsyncIOScheduler() # Исправлено: AsyncIOScheduler
    scheduler.add_job(auto_post_trend, "interval", hours=6)
    scheduler.start()
    
    logging.info("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
