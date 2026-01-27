import asyncio
import aiohttp
import os
import http.server
import socketserver
import threading
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- СЕРВЕР ДЛЯ RENDER ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 8000))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- НАСТРОЙКИ ---
API_TOKEN = '8445491297:AAFmePW4OSKHLW0SIw86pgWdYjiQlBziOJg'
CHANNEL_ID = '@ua_trends_save'
CHANNEL_URL = 'https://t.me/ua_trends_save'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

@dp.message(Command("start"))
async def start(message: types.Message):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="1. Подписаться на канал 📢", url=CHANNEL_URL)],
        [types.InlineKeyboardButton(text="2. Я подписался ✅", callback_data="verify")]
    ])
    await message.answer(f"Привет! 👋 Пришли ссылку на TikTok:", reply_markup=markup)

@dp.callback_query(F.data == "verify")
async def verify(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.edit_text("✅ Доступ открыт! Жду ссылку.")
    else:
        await call.answer("❌ Подписка не найдена!", show_alert=True)

@dp.message(F.text.contains("tiktok.com"))
async def handle_tiktok(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer("⚠️ Сначала подпишись!")
        return

    status_msg = await message.answer("⌛ Обработка видео...")
    try:
        async with aiohttp.ClientSession() as session:
            api_url = f"https://api.tiklydown.eu.org/api/download?url={message.text}"
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    video_url = data.get('video', {}).get('noWatermark')
                    if video_url:
                        await message.answer_video(video_url, caption="✅ Готово! @ua_trends_save")
                    else:
                        await message.answer("❌ Не удалось найти видео.")
                else:
                    await message.answer("❌ Сервис загрузки не отвечает.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    finally:
        await status_msg.delete()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    


