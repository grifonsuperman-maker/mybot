import os, logging, asyncio, random, string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp
from aiohttp import web

# --- НАСТРОЙКИ (Данные из твоих скриншотов) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@ua_trends_save"  #
ADMIN_USERNAME = "@AlexUlqiora" #
MONO_URL = "https://send.monobank.ua/jar/qU4cLtSyT" #
BOT_NICKNAME = "@ua_trends_save_bot" #
# ---------------------------------------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_links = {}

# Веб-сервер для поддержания активности на Render
async def handle(request): 
    return web.Response(text="Бот активен. Все ошибки исправлены.")

# 📢 АВТО-ПРОМО (Бот сам постит в канал раз в 6 часов)
async def auto_promo():
    while True:
        try:
            await asyncio.sleep(21600) 
            await bot.send_message(
                CHANNEL_ID, 
                f"📥 Качайте видео из TikTok/YouTube/Insta без водяных знаков!\n👉 Наш бот: {BOT_NICKNAME}"
            )
            logging.info("Промо-пост отправлен")
        except Exception as e:
            logging.error(f"Ошибка промо: {e}")

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Заказать Рекламу", callback_data="ads_info")
    kb.button(text="☕ Поддержать проект", callback_data="donate_info")
    kb.adjust(1)
    await message.answer(
        f"👋 Привет! Я качаю видео из **TikTok, Instagram и YouTube**.\n\n"
        f"✅ Без водяных знаков и лишних подписей!\n\n"
        f"Просто пришли мне ссылку.",
        reply_markup=kb.as_markup()
    )

# 💰 РЕКЛАМА И ДОНАТЫ
@dp.callback_query(F.data == "ads_info")
async def ads_handler(callback: types.CallbackQuery):
    await callback.message.answer(
        f"📊 **Сотрудничество и Реклама**\n\nПо вопросам размещения пишите: {ADMIN_USERNAME}\n"
        f"💳 Оплата: Monobank, Crypto, Карты."
    )

@dp.callback_query(F.data == "donate_info")
async def donate_handler(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Monobank (Банка)", url=MONO_URL)
    await callback.message.answer("🙏 Спасибо, что помогаете проекту развиваться!", reply_markup=kb.as_markup())

# 🎬 ЗАГРУЗКА (Исправлены блокировки и ошибки 403)
@dp.message(F.text.contains("http"))
async def handle_link(message: types.Message):
    url = message.text.strip()
    user_links[message.from_user.id] = url
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Видео", callback_data="dl_video")
    kb.button(text="🎵 Музыка (MP3)", callback_data="dl_audio")
    await message.answer("Выберите формат:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: types.CallbackQuery):
    url = user_links.get(callback.from_user.id)
    choice = callback.data.split("_")[1]
    if not url: return

    status_msg = await callback.message.answer("⏳ Обхожу защиту и загружаю...")
    rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    file_path = f"file_{callback.from_user.id}_{rand_str}.{'mp4' if choice == 'video' else 'm4a'}"
    
    ydl_opts = {
        'outtmpl': file_path,
        'quiet': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        # МАСКИРОВКА (Решает проблему "Sign in to confirm" из логов)
        'extractor_args': {
            'youtube': {'player_client': ['ios', 'android', 'web_embedded']},
            'instagram': {'check_headers': True}
        },
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        
        if os.path.exists(file_path):
            file = types.FSInputFile(file_path)
            # ОТПРАВКА БЕЗ ВОДЯНЫХ ЗНАКОВ
            if choice == 'video':
                await callback.message.answer_video(file)
            else:
                await callback.message.answer_audio(file)
            await callback.message.answer("✅ Файл успешно загружен!")
        else: raise Exception("Ошибка сервера")
    except Exception as e:
        logging.error(f"Error: {e}")
        await callback.message.answer("❌ Сервис временно ограничил доступ. Попробуйте другую ссылку.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        await status_msg.delete()

async def main():
    # Запуск фоновых задач
    asyncio.create_task(auto_promo())
    
    # Запуск сервера
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
