import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from database.db import init_db
from handlers import ai_chat, image_gen, voice, admin, antislut
from handlers.antislut import AntiSlutMiddleware
from middlewares.antispam import AntiSpamMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.message.middleware(AntiSlutMiddleware())  # проверяет на шлюхоботов, не блокирует ai_chat
    dp.message.middleware(AntiSpamMiddleware())

    dp.include_router(antislut.router)  # chat_member + реакции
    dp.include_router(admin.router)
    dp.include_router(image_gen.router)
    dp.include_router(voice.router)
    dp.include_router(ai_chat.router)

    logger.info("Bot started!")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=[
        "message", "chat_member", "message_reaction", "callback_query"
    ])


if __name__ == "__main__":
    asyncio.run(main())
