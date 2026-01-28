import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@ua_trends_save"  # Твой канал
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_links = {}

async def check_sub(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(f"👋 Привет! Я AI Помощник.\n📥 Качаю видео и музыку.\n📢 Подпишись: {CHANNEL_ID}")

@dp.message(F.text.contains("http"))
async def handle_link(message: types.Message):
    if not await check_sub(message.from_user.id):
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Подписаться", url=f"https://t.me/ua_trends_save")
        return await message.answer(f"❌ Подпишись на {CHANNEL_ID}", reply_markup=kb.as_markup())

    user_links[message.from_user.id] = message.text
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Видео", callback_data="dl_video")
    kb.button(text="🎵 Музыка (MP3)", callback_data="dl_audio")
    await message.answer("Что скачать?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: types.CallbackQuery):
    url = user_links.get(callback.from_user.id)
    choice = callback.data.split("_")[1]
    if not url: return

    await callback.message.edit_text(f"⏳ Качаю {'видео' if choice == 'video' else 'аудио'}...")
    file_path = f"file_{callback.from_user.id}.{'mp4' if choice == 'video' else 'mp3'}"
    
    ydl_opts = {'format': 'best' if choice == 'video' else 'bestaudio/best', 'outtmpl': file_path, 'quiet': True}
    if choice == 'audio':
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        
        support_kb = InlineKeyboardBuilder()
        support_kb.button(text="☕ Поддержать проект", url="https://t.me/твой_ник")
        
        input_file = types.FSInputFile(file_path)
        if choice == 'video':
            await callback.message.answer_video(input_file, caption="✅ Готово!", reply_markup=support_kb.as_markup())
        else:
            await callback.message.answer_audio(input_file, caption="✅ MP3 Готово!", reply_markup=support_kb.as_markup())
    except Exception:
        await callback.message.answer("❌ Ошибка загрузки.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        await callback.message.delete()

async def main():
    logging.info("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

