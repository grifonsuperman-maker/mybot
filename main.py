import os, logging, asyncio, random, string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp
from aiohttp import web

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_NICKNAME = "@ua_trends_save_bot" 
# ------------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_links = {}

async def handle(request): return web.Response(text="Бот в сети и готов к обходу защит!")

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(f"👋 Привет! Я качаю **TikTok, Instagram и YouTube**.\nПришли ссылку!")

@dp.message(F.text.contains("http"))
async def handle_link(message: types.Message):
    url = message.text.strip()
    user_links[message.from_user.id] = url
    service = "Instagram" if "instagr" in url else "YouTube" if "youtu" in url else "видео"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Видео", callback_data="dl_video")
    kb.button(text="🎵 Музыка", callback_data="dl_audio")
    await message.answer(f"Нашел {service}. Скачиваем?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: types.CallbackQuery):
    url = user_links.get(callback.from_user.id)
    choice = callback.data.split("_")[1]
    if not url: return

    status_msg = await callback.message.answer("⏳ Обхожу защиту сервиса...")
    rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    file_path = f"file_{callback.from_user.id}_{rand_str}.{'mp4' if choice == 'video' else 'm4a'}"
    
    ydl_opts = {
        'outtmpl': file_path,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        # САМЫЙ ВАЖНЫЙ ПАРАМЕТР ДЛЯ ОБХОДА БЛОКИРОВОК:
        'extractor_args': {
            'youtube': {'player_client': ['ios', 'android', 'web_embedded']},
            'instagram': {'check_headers': True}
        },
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1',
    }

    if choice == 'video':
        ydl_opts['format'] = 'best[ext=mp4][filesize<50M]/best'
    else:
        ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        
        if os.path.exists(file_path):
            file = types.FSInputFile(file_path)
            if choice == 'video':
                await callback.message.answer_video(file, caption=f"✅ Готово!\n🤖 {BOT_NICKNAME}")
            else:
                await callback.message.answer_audio(file, caption=f"✅ Музыка!\n🤖 {BOT_NICKNAME}")
        else: raise Exception("Блок")
            
    except Exception as e:
        logging.error(f"Error: {e}")
        await callback.message.answer("❌ Сервис заблокировал запрос. Попробуйте через 5-10 минут или другую ссылку.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        await status_msg.delete()

async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
