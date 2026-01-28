import os, logging, asyncio, random, string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp
from aiohttp import web

# --- НАЛАШТУВАННЯ (З твоїх скриншотів) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@ua_trends_save"  
ADMIN_USERNAME = "@AlexUlqiora" 
MONO_URL = "https://send.monobank.ua/jar/qU4cLtSyT"
BOT_NICKNAME = "@ua_trends_save_bot"
# ---------------------------------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_links = {}

# Веб-сервер для стабільності на Render
async def handle(request): 
    return web.Response(text="Бот працює стабільно. Конфлікти усунено.")

# 📢 АВТО-ПРОМО (Реклама каналу кожні 6 годин)
async def auto_promo():
    while True:
        try:
            await asyncio.sleep(21600)
            await bot.send_message(
                CHANNEL_ID, 
                f"📥 Качайте відео без знаків прямо тут!\n👉 Наш бот: {BOT_NICKNAME}"
            )
        except: pass

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Реклама", callback_data="ads_info")
    kb.button(text="☕ Підтримати", callback_data="donate_info")
    kb.adjust(2)
    
    welcome = (
        "👋 **Привіт! Я твій помічник із завантаження.**\n\n"
        "Я качу контент у найкращій якості з:\n"
        "✅ **TikTok** (без знака)\n"
        "✅ **Instagram** (Reels/Post)\n"
        "✅ **Facebook**\n"
        "✅ **Twitter (X)**\n"
        "✅ **Pinterest**\n\n"
        "📥 Просто надішли мені посилання!"
    )
    await message.answer(welcome, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "ads_info")
async def ads_handler(callback: types.CallbackQuery):
    await callback.message.answer(f"📊 З питань реклами: {ADMIN_USERNAME}")

@dp.callback_query(F.data == "donate_info")
async def donate_handler(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Monobank", url=MONO_URL)
    await callback.message.answer("🙏 Дякую за підтримку проекту!", reply_markup=kb.as_markup())

@dp.message(F.text.contains("http"))
async def handle_link(message: types.Message):
    url = message.text.strip()
    
    if "youtu" in url or "youtube" in url:
        await message.answer("⚠️ YouTube тимчасово не підтримується. Використовуйте TikTok або Instagram.")
        return

    user_links[message.from_user.id] = url
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Відео", callback_data="dl_video")
    kb.button(text="🎵 Музика", callback_data="dl_audio")
    await message.answer("🔍 Що саме скачати?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: types.CallbackQuery):
    url = user_links.get(callback.from_user.id)
    choice = callback.data.split("_")[1]
    if not url: return

    status_msg = await callback.message.answer("⏳ Готую файл... Зачекайте.")
    rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    ext = 'mp4' if choice == 'video' else 'm4a'
    file_path = f"file_{callback.from_user.id}_{rand_str}.{ext}"
    
    ydl_opts = {
        'outtmpl': file_path,
        'quiet': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
        'format': 'best[ext=mp4][filesize<50M]/best' if choice == 'video' else 'bestaudio[ext=m4a]/bestaudio/best',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        
        if os.path.exists(file_path):
            file = types.FSInputFile(file_path)
            if choice == 'video':
                await callback.message.answer_video(file)
            else:
                await callback.message.answer_audio(file)
        else: raise Exception("Файл не знайдено")
    except Exception as e:
        logging.error(f"Download Error: {e}")
        await callback.message.answer("❌ Помилка. Можливо, відео приватне або занадто довге.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        await status_msg.delete()

async def main():
    asyncio.create_task(auto_promo())
    
    # Запуск веб-сервера (порт 10000 для Render)
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()
    
    # ⚡ ВИРІШЕННЯ ПОМИЛКИ CONFLICT: Очищуємо старі повідомлення
    await bot.delete_webhook(drop_pending_updates=True)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
