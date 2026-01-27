import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import yt_dlp

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем токен из переменных окружения Render
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Папка для временных файлов
DOWNLOAD_PATH = "downloads"
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("👋 Привет! Я твой AI Помощник. Пришли мне ссылку на видео (TikTok, Reels, YouTube), и я скачаю его для тебя!")

@dp.message(F.text.contains("http"))
async def download_video(message: types.Message):
    url = message.text
    status_msg = await message.answer("⏳ Обрабатываю ссылку, подождите...")
    
    # Настройки yt-dlp для скачивания
    file_path = os.path.join(DOWNLOAD_PATH, f"{message.from_user.id}.mp4")
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': file_path,
        'quiet': True,
        'noplaylist': True,
    }

    try:
        # Скачивание видео во временную папку
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        
        # Отправка видео пользователю
        video_file = types.FSInputFile(file_path)
        await message.answer_video(video_file, caption="✅ Ваше видео готово!")
        await status_msg.delete()
        
        # Удаляем файл после отправки
        os.remove(file_path)
        
    except Exception as e:
        logging.error(f"Ошибка при скачивании: {e}")
        await status_msg.edit_text("❌ Не удалось скачать видео. Возможно, ссылка не поддерживается или сервис временно недоступен.")
        if os.path.exists(file_path):
            os.remove(file_path)

async def main():
    logging.info("🚀 Бот полностью запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

