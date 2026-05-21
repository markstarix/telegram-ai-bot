from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, IMAGE_MODEL

router = Router()
ai = AsyncOpenAI(api_key=OPENAI_API_KEY)


@router.message(Command("img"))
async def image_handler(message: Message):
    prompt = message.text.replace("/img", "").strip()

    if not prompt:
        await message.answer(
            "🖼 Напиши описание после команды.\n"
            "Пример: <code>/img закат над морем в стиле аниме</code>"
        )
        return

    await message.answer("🎨 Генерирую изображение, подожди...")
    await message.bot.send_chat_action(message.chat.id, "upload_photo")

    try:
        result = await ai.images.generate(
            model=IMAGE_MODEL,
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        image_url = result.data[0].url
        await message.answer_photo(
            photo=image_url,
            caption=f"🖼 <b>Сгенерировано по запросу:</b>\n<i>{prompt}</i>"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации изображения: {e}")
