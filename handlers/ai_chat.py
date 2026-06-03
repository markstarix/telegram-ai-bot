import io
import random
import base64
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import CommandStart, Command
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, AI_MODEL, IMAGE_MODEL, MAX_HISTORY, TAVILY_API_KEY
from database.db import get_history, save_message, clear_history, get_image_usage, increment_image_usage
from services.rates import detect_rates_request, get_crypto_price, get_single_fiat_rate
from services.search import needs_search, web_search

router = Router()
ai = AsyncOpenAI(api_key=OPENAI_API_KEY)

DAILY_IMAGE_LIMIT = 3

# Голосовые настройки
TTS_VOICE = "onyx"
TTS_CHANCE = 0.20  # 20% шанс голосового ответа
TTS_MAX_LEN = 400  # не озвучиваем слишком длинные ответы

IMAGE_TRIGGERS = [
    "сгенерируй фото", "сгенерируй картинку", "сгенерируй изображение",
    "создай фото", "создай картинку", "создай изображение",
    "сделай фото", "сделай картинку", "сделай изображение",
    "нарисуй", "draw", "generate image", "create image"
]


def get_current_date_str() -> str:
    now = datetime.utcnow()
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    return f"{now.day} {months[now.month - 1]} {now.year} года"


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


async def text_to_voice(text: str) -> BufferedInputFile:
    """Конвертирует текст в голосовое сообщение через OpenAI TTS"""
    response = await ai.audio.speech.create(
        model="tts-1",
        voice=TTS_VOICE,
        input=text,
        response_format="opus",  # корректный формат для Telegram voice
    )
    audio_bytes = response.content
    return BufferedInputFile(audio_bytes, filename="voice.ogg")


async def send_answer(message: Message, answer: str, force_voice: bool = False):
    """Отправляет ответ — текстом или голосовым"""
    use_voice = force_voice or (len(answer) <= TTS_MAX_LEN and random.random() < TTS_CHANCE)
    if use_voice:
        try:
            await message.bot.send_chat_action(message.chat.id, "record_voice")
            voice_file = await text_to_voice(answer)
            await message.answer_voice(voice_file)
            return
        except Exception as e:
            pass  # если TTS упал — отвечаем текстом
    await message.answer(answer)


@router.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        f"👋 Привет, <b>{message.from_user.full_name}</b>!\n\n"
        "Я — твой AI-помощник. Вот что я умею:\n\n"
        "💬 Напиши мне — отвечу на любой вопрос\n"
        "🌐 Спрошу интернет если нужна актуальная информация\n"
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
        "🌐 Актуальные события — бот сам ищет в интернете\n"
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


VOICE_REQUEST_TRIGGERS = [
    "голосом", "голосовым", "голосовое", "войсом", "войс",
    "ответь голосом", "скажи голосом", "voice", "speak"
]


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

    # Проверяем явный запрос голосового ответа
    text_lower = user_text.lower()
    force_voice = any(t in text_lower for t in VOICE_REQUEST_TRIGGERS)

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
            result = await get_crypto_price(value) if kind == "crypto" else await get_single_fiat_rate(value)
            if result:
                await message.answer(result)
                return

        # 3. Веб-поиск для актуальных вопросов
        today = get_current_date_str()
        search_context = ""
        if TAVILY_API_KEY and needs_search(user_text):
            search_result = await web_search(user_text, TAVILY_API_KEY)
            if search_result:
                search_context = f"\n\nАктуальная информация из интернета (используй её в ответе):\n{search_result}"

        # 4. Обычный AI-ответ
        base_prompt = (
            f"Сегодня {today}. "
            "Ты умный AI-помощник в Telegram. "
            "Отвечай на русском языке если пишут по-русски. "
            "Ты умеешь отправлять голосовые сообщения — иногда отвечаешь голосом, это нормально. "
            "Никогда не говори что не можешь отвечать голосом. "
            "Будь точным и кратким."
            + search_context
        )
        group_prompt = (
            f"Сегодня {today}. "
            "Ты живой участник Telegram чата. "
            "Вмешивайся в разговор естественно и по теме. "
            "Отвечай коротко — 1-2 предложения. Без лишних вступлений. "
            "Ты умеешь отправлять голосовые сообщения — иногда отвечаешь голосом, это нормально. "
            "Никогда не говори что не можешь отвечать голосом. "
            "Пиши на том языке на котором пишут в чате."
            + search_context
        )
        system_prompt = group_prompt if is_group else base_prompt

        answer = await ask_ai(user_id, user_text, system_prompt)
        await send_answer(message, answer, force_voice=force_voice)

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
