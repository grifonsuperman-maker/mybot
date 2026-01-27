import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========================================================
# НАЛАШТУВАННЯ (ПЕРЕВІРЕНО)
# ========================================================
API_TOKEN = '8445491297:AAFmePW4OSKHLW0SIw86pgWdYjiQlBziOJg'
CHANNEL_ID = '@ua_trends_save'  # Виправлено (без пробілів)
CHANNEL_URL = 'https://t.me/ua_trends_save'
BOT_URL = 'https://t.me/tviy_bot_username' # ЗАМІНИ на юзернейм свого бота
# ========================================================

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
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1. Підписатися на канал 📢", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="2. Я підписався ✅", callback_data="verify")]
    ])
    await message.answer(
        f"Привіт! 👋 Надішли мені посилання на TikTok, і я завантажу відео без водяного знаку.\n\n"
        f"Спочатку підпишись на наш канал:",
        reply_markup=markup
    )

@dp.callback_query(F.data == "verify")
async def verify(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.edit_text("✅ Доступ відкрито! Чекаю на твоє посилання з TikTok.")
    else:
        await call.answer("❌ Підписка не знайдена!", show_alert=True)

@dp.message(F.text.contains("tiktok.com"))
async def handle_tiktok(message: types.Message):
    if not await check_sub(message.from_user.id):
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Підписатися на канал 📢", url=CHANNEL_URL)]
        ])
        await message.answer("⚠️ Для завантаження відео підпишись на наш канал!", reply_markup=markup)
        return

    status_msg = await message.answer("⏳ Обробка відео...")
    clean_url = message.text.split("?")[0]
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://www.tikwm.com/api/?url={clean_url}") as resp:
            res = await resp.json()
            
            if res.get('code') == 0:
                video_url = res['data']['play']
                
                # Кнопка для поширення бота (саморозвиток)
                share_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚀 Поділитися ботом", url=f"https://t.me/share/url?url={BOT_URL}")]
                ])

                await bot.send_video(
                    chat_id=message.chat.id,
                    video=video_url,
                    caption=f"✅ Готово! Підписуйся на тренди: {CHANNEL_ID}",
                    reply_markup=share_kb
                )
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ Помилка. Спробуй інше посилання.")

async def main():
    print("Бот запущений та готовий до роботи!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

