import os
import tempfile

from aiogram import Router, F
from aiogram.types import Message
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, AI_MODEL
from database.db import get_history, save_message

router = Router()
ai = AsyncOpenAI(api_key=OPENAI_API_KEY)


@router.message(F.voice)
async def voice_handler(message: Message):
    await message.answer("🎙 Распознаю голосовое сообщение...")

    try:
        voice_file = await message.bot.get_file(message.voice.file_id)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name

        await message.bot.download_file(voice_file.file_path, tmp_path)

        with open(tmp_path, "rb") as audio:
            transcript = await ai.audio.transcriptions.create(
                model="whisper-1",
                file=audio
            )

        os.unlink(tmp_path)
        text = transcript.text

        await message.answer(f"🗣 <b>Ты сказал:</b> <i>{text}</i>")
        await message.bot.send_chat_action(message.chat.id, "typing")

        user_id = message.from_user.id
        await save_message(user_id, "user", text)
        history = await get_history(user_id, 10)

        messages = [
            {"role": "system", "content": "Ты умный AI-помощник в Telegram. Отвечай кратко и по делу."}
        ] + history

        response = await ai.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            max_tokens=500
        )
        answer = response.choices[0].message.content
        await save_message(user_id, "assistant", answer)
        await message.answer(answer)

    except Exception as e:
        await message.answer(f"❌ Ошибка обработки голосового: {e}")
