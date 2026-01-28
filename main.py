import os, logging, asyncio, random, string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramConflictError
import yt_dlp
from aiohttp import web

# --- НАЛАШТУВАННЯ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@ua_trends_save"  
ADMIN_USERNAME = "@AlexUlqiora" 
MONO_URL = "https://send.monobank.ua/jar/qU4cLtSyT"
BOT_NICKNAME = "@ua_trends_save_bot"
# --------------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_links = {}

# Веб-сервер для Render (захист від сну та 502 помилки)
async def handle(request): 
    return web.Response(text="Бот онлайн та працює.")

# Перевірка підписки на канал
async def check_subscription(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Реклама", callback_data="ads_info")
    kb.button(text="☕ Підтримати", callback_data="donate_info")
    kb.adjust(2)
    
    await message.answer(
        "👋 **Привіт! Я качаю відео без водяних знаків.**\n\n"
        "✅ TikTok, Instagram, FB, Pinterest, Twitter.\n"
        "📥 Просто надішли мені посилання!",
        reply_markup=kb.as_markup(), parse_mode="Markdown"
    )

@dp.callback_query(F.data == "ads_info")
async def ads_handler(callback: types.CallbackQuery):
    await callback.message.answer(f"📊 З питань реклами: {ADMIN_USERNAME}")

@dp.callback_query(F.data == "donate_info")
async def donate_handler(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Monobank", url=MONO_URL)
    await callback.message.answer("🙏 Дякую за підтримку! Це допоможе боту працювати швидше.", reply_markup=kb.as_markup())

@dp.message(F.text.contains("http"))
async def handle_link(message: types.Message):
    if not await check_subscription(message.from_user.id):
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Підписатися на канал", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")
        await message.answer(
            f"❌ **Доступ обмежено!**\n\nБудь ласка, підпишіться на наш канал {CHANNEL_ID}, щоб користуватися ботом.",
            reply_markup=kb.as_markup()
        )
        return

    url = message.text.strip()
    if "youtu" in url:
        await message.answer("⚠️ YouTube не підтримується. Спробуйте TikTok або Instagram.")
        return

    user_links[message.from_user.id] = url
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Відео", callback_data="dl_video")
    kb.button(text="🎵 Музика", callback_data="dl_audio")
    await message.answer("🔍 Посилання прийнято! Що скачати?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: types.CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.answer("❌ Спочатку підпишіться!", show_alert=True)
        return

    url = user_links.get(callback.from_user.id)
    choice = callback.data.split("_")[1]
    if not url: return

    status_msg = await callback.message.answer("⏳ Обробка... Зачекайте.")
    rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    ext = 'mp4' if choice == 'video' else 'm4a'
    file_path = f"file_{callback.from_user.id}_{rand_str}.{ext}"
    
    # Текст самореклами під відео
    promo_caption = f"🎬 Без водяних знаків через {BOT_NICKNAME}\n\n🔥 Більше трендів тут: {CHANNEL_ID}"

    ydl_opts = {
        'outtmpl': file_path,
        'quiet': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
        'format': 'best[ext=mp4][filesize<50M]/best' if choice == 'video' else 'bestaudio[ext=m4a]/bestaudio/best',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        
        if os.path.exists(file_path):
            file = types.FSInputFile(file_path)
            
            # Відправка відео або аудіо користувачу
            if choice == 'video':
                sent_msg = await callback.message.answer_video(file, caption=promo_caption)
                
                # АВТОПОСТИНГ У КАНАЛ
                try:
                    await bot.send_video(
                        chat_id=CHANNEL_ID, 
                        video=sent_msg.video.file_id, 
                        caption=f"🔥 Новий тренд!\n\nСкачати без знаків: {BOT_NICKNAME}"
                    )
                except Exception as post_e:
                    logging.error(f"Помилка автопостингу: {post_e}")
            else:
                await callback.message.answer_audio(file, caption=promo_caption)
        else: 
            raise Exception("File missing")
    except Exception as e:
        logging.error(f"Помилка: {e}")
        await callback.message.answer("❌ Помилка завантаження. Спробуйте інше посилання.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        await status_msg.delete()

async def main():
    # Запуск веб-сервера для Render
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()
    
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        await dp.start_polling(bot)
    except TelegramConflictError:
        logging.error("Конфлікт: бот вже запущений.")

if __name__ == "__main__":
    asyncio.run(main())
