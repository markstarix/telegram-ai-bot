import random
import base64
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import CommandStart, Command
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, AI_MODEL, IMAGE_MODEL, MAX_HISTORY
from database.db import get_history, save_message, clear_history, get_image_usage, increment_image_usage
from services.rates import (
    detect_rates_request, get_crypto_price,
    get_single_fiat_rate, get_cbr_rates
)

router = Router()
ai = AsyncOpenAI(api_key=OPENAI_API_KEY)

DAILY_IMAGE_LIMIT = 3

IMAGE_TRIGGERS = [
    "сгенерируй фото", "сгенерируй картинку", "сгенерируй изображение",
    "создай фото", "создай картинку", "создай изображение",
    "сделай фото", "сделай картинку", "сделай изображение",
    "нарисуй", "draw", "generate image", "create image"
]


async def is_image_request(text: str) -> bool:
    return any(trigger in text.lower() for trigger in IMAGE_TRIGGERS)


async def extract_image_prompt(text: str) -> str:
    response = await ai.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Extract the image description from the message. Return only the description in English, no extra words."
            },
            {"role": "user", "content": text}
        ],
        max_tokens=100
    )
    return response.choices[0].message.content


async def generate_image(prompt: str) -> BufferedInputFile:
    result = await ai.images.generate(
        model=IMAGE_MODEL,
        prompt=prompt,
        size="1024x1024",
        quality="medium",
        n=1
    )
    image_data = base64.b64decode(result.data[0].b64_json)
    return BufferedInputFile(image_data, filename="image.png")


async def ask_ai(user_id: int, user_text: str, system_prompt: str) -> str:
    await save_message(user_id, "user", user_text)
    history = await get_history(user_id, MAX_HISTORY)
    messages = [{"role": "system", "content": system_prompt}] + history
    response = await ai.chat.completions.create(
        model=AI_MODEL,
        messages=messages,
        max_tokens=500
    )
    answer = response.choices[0].message.content
    await save_message(user_id, "assistant", answer)
    return answer


@router.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        f"👋 Привет, <b>{message.from_user.full_name}</b>!\n\n"
        "Я — твой AI-помощник. Вот что я умею:\n\n"
        "💬 Напиши мне — отвечу на любой вопрос\n"
        "💱 Спроси курс — <b>курс BTC</b>, <b>курс доллара</b>\n"
        f"🖼 Напиши <b>сгенерируй/создай/нарисуй фото ...</b> — сделаю картинку (до {DAILY_IMAGE_LIMIT} в день)\n"
        "🔊 Отправь голосовое — распознаю и отвечу\n"
        "🗑 /clear — очищу историю диалога\n"
        "❓ /help — список всех команд"
    )


@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "📋 <b>Список команд:</b>\n\n"
        "💬 <b>Текст</b> — задай любой вопрос\n"
        "💱 <b>Курс BTC / ETH / TON</b> — курс крипты\n"
        "💱 <b>Курс доллара / евро</b> — курс валют ЦБ РФ\n"
        f"🖼 <b>Сгенерируй/создай фото ...</b> — генерация изображения (до {DAILY_IMAGE_LIMIT} в день)\n"
        "🔊 <b>Голосовое</b> — распознавание речи + ответ\n"
        "🗑 /clear — очистить историю диалога\n"
        "❓ /help — эта справка"
    )


@router.message(Command("clear"))
async def clear_handler(message: Message):
    await clear_history(message.from_user.id)
    await message.answer("🗑 История диалога очищена!")


@router.message(F.text)
async def chat_handler(message: Message):
    user_id = message.from_user.id
    user_text = message.text
    is_group = message.chat.type in ("group", "supergroup")

    if is_group:
        bot_info = await message.bot.get_me()
        bot_username = bot_info.username
        is_mentioned = f"@{bot_username}" in user_text
        is_reply_to_bot = (
            message.reply_to_message and
            message.reply_to_message.from_user and
            message.reply_to_message.from_user.username == bot_username
        )

        if is_mentioned or is_reply_to_bot:
            user_text = user_text.replace(f"@{bot_username}", "").strip()
        elif random.random() > 0.05:
            return

    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        # 1. Генерация изображения
        if await is_image_request(user_text):
            usage = await get_image_usage(user_id)
            if usage >= DAILY_IMAGE_LIMIT:
                await message.answer(
                    f"🚫 Ты уже сгенерировал {DAILY_IMAGE_LIMIT} изображения сегодня.\n"
                    "⏳ Лимит обновится в полночь (00:00 UTC)."
                )
                return

            await message.answer("🎨 Генерирую изображение, подожди...")
            await message.bot.send_chat_action(message.chat.id, "upload_photo")
            prompt = await extract_image_prompt(user_text)
            image_file = await generate_image(prompt)
            await increment_image_usage(user_id)
            remaining = DAILY_IMAGE_LIMIT - usage - 1
            await message.answer_photo(
                photo=image_file,
                caption=f"🖼 <i>{user_text}</i>\n\n<i>Осталось генераций сегодня: {remaining}</i>"
            )
            return

        # 2. Курсы валют и крипты
        rate_request = detect_rates_request(user_text)
        if rate_request:
            kind, value = rate_request
            if kind == "crypto":
                result = await get_crypto_price(value)
            else:
                result = await get_single_fiat_rate(value)

            if result:
                await message.answer(result)
                return

        # 3. Обычный AI-ответ
        system_prompt = (
            "Ты умный AI-помощник в Telegram. "
            "Отвечай на русском языке если пишут по-русски. "
            "Будь точным и кратким."
        ) if not is_group else (
            "Ты живой участник Telegram чата. "
            "Вмешивайся в разговор естественно и по теме. "
            "Отвечай коротко — 1-2 предложения. Без лишних вступлений. "
            "Пиши на том языке на котором пишут в чате."
        )

        answer = await ask_ai(user_id, user_text, system_prompt)
        await message.answer(answer)

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
