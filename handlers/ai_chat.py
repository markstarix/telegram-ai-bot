from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, AI_MODEL, MAX_HISTORY
from database.db import get_history, save_message, clear_history

router = Router()
ai = AsyncOpenAI(api_key=OPENAI_API_KEY)


@router.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        f"👋 Привет, <b>{message.from_user.full_name}</b>!\n\n"
        "Я — твой AI-помощник. Вот что я умею:\n\n"
        "💬 Просто напиши мне — отвечу на любой вопрос\n"
        "🖼 /img &lt;описание&gt; — сгенерирую изображение\n"
        "🔊 Отправь голосовое — распознаю и отвечу\n"
        "🗑 /clear — очищу историю диалога\n"
        "❓ /help — список всех команд"
    )


@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "📋 <b>Список команд:</b>\n\n"
        "💬 <b>Текст</b> — задай любой вопрос\n"
        "🖼 /img &lt;описание&gt; — генерация изображения\n"
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

    await message.bot.send_chat_action(message.chat.id, "typing")
    await save_message(user_id, "user", user_text)

    history = await get_history(user_id, MAX_HISTORY)

    messages = [
        {
            "role": "system",
            "content": (
                "Ты умный и дружелюбный AI-помощник в Telegram. "
                "Отвечай на русском языке, если пользователь пишет по-русски. "
                "Будь полезным, точным и кратким."
            )
        }
    ] + history

    try:
        response = await ai.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            max_tokens=1000
        )
        answer = response.choices[0].message.content
        await save_message(user_id, "assistant", answer)
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"❌ Ошибка при обращении к AI: {e}")
