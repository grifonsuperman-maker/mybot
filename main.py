import os, logging, asyncio, random, string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp
from aiohttp import web

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@ua_trends_save"  
ADMIN_USERNAME = "@AlexUlqiora" 
MONO_URL = "https://send.monobank.ua/jar/qU4cLtSyT"
BOT_NICKNAME = "@ua_trends_save_bot"
# ------------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_links = {}

async def handle(request): 
    return web.Response(text="Бот-комбайн запущен!")

# 📢 АВТО-ПРОМО (Каждые 6 часов в канал)
async def auto_promo():
    while True:
        try:
            await asyncio.sleep(21600)
            await bot.send_message(
                CHANNEL_ID, 
                f"📥 Качаю видео БЕЗ знаков из всех соцсетей!\n👉 Бот: {BOT_NICKNAME}"
            )
        except: pass

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Реклама", callback_data="ads_info")
    kb.button(text="☕ Поддержать", callback_data="donate_info")
    kb.adjust(2)
    
    welcome_text = (
        "👋 **Я — твой универсальный загрузчик!**\n\n"
        "Я легко скачиваю видео и музыку из:\n"
        "✅ **TikTok** (без знака)\n"
        "✅ **YouTube** (Shorts и видео)\n"
        "✅ **Instagram** (Reels и посты)\n"
        "✅ **Facebook**\n"
        "✅ **Twitter (X)**\n"
        "✅ **Pinterest**\n\n"
        "🚀 Просто пришли мне ссылку, и я сделаю всё за тебя!"
    )
    await message.answer(welcome_text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "ads_info")
async def ads_handler(callback: types.CallbackQuery):
    await callback.message.answer(f"📊 По рекламе: {ADMIN_USERNAME}\n💳 Оплата: Mono, Crypto.")

@dp.callback_query(F.data == "donate_info")
async def donate_handler(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Monobank", url=MONO_URL)
    await callback.message.answer("🙏 Спасибо за поддержку!", reply_markup=kb.as_markup())

@dp.message(F.text.contains("http"))
async def handle_link(message: types.Message):
    url = message.text.strip()
    user_links[message.from_user.id] = url
    
    # Определяем соцсеть для текста
    service = "видео"
    if "tiktok" in url: service = "TikTok"
    elif "youtu" in url: service = "YouTube"
    elif "instagr" in url: service = "Instagram"
    elif "facebook" in url or "fb.watch" in url: service = "Facebook"
    elif "pin.it" in url or "pinterest" in url: service = "Pinterest"
    elif "twitter" in url or "x.com" in url: service = "Twitter (X)"

    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Скачать Видео", callback_data="dl_video")
    kb.button(text="🎵 Скачать Музыку", callback_data="dl_audio")
    await message.answer(f"Обнаружена ссылка на **{service}**. Выбирай формат:", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: types.CallbackQuery):
    url = user_links.get(callback.from_user.id)
    choice = callback.data.split("_")[1]
    if not url: return

    status_msg = await callback.message.answer("⏳ Маскируюсь и качаю... Подождите.")
    rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    ext = 'mp4' if choice == 'video' else 'm4a'
    file_path = f"file_{callback.from_user.id}_{rand_str}.{ext}"
    
    ydl_opts = {
        'outtmpl': file_path,
        'quiet': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'extractor_args': {
            'youtube': {'player_client': ['android', 'ios']},
            'instagram': {'check_headers': True}
        },
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
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
            await (callback.message.answer_video(file) if choice == 'video' else callback.message.answer_audio(file))
            await callback.message.answer("✅ Файл готов! Пользуйся.")
        else: raise Exception("File missing")
    except:
        await callback.message.answer("❌ Ошибка. Сервис блокирует доступ. Попробуйте другую ссылку.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        await status_msg.delete()

async def main():
    asyncio.create_task(auto_promo())
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
