import time
from collections import defaultdict
from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message

from config import SPAM_LIMIT, SPAM_WINDOW
from database.db import increment_banned


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self):
        self.user_messages: dict = defaultdict(list)
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any]
    ) -> Any:
        if event.chat.type not in ("group", "supergroup"):
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.time()

        self.user_messages[user_id] = [
            t for t in self.user_messages[user_id]
            if now - t < SPAM_WINDOW
        ]
        self.user_messages[user_id].append(now)

        if len(self.user_messages[user_id]) > SPAM_LIMIT:
            try:
                await event.chat.ban(user_id)
                await increment_banned()
                await event.answer(
                    f"🚫 <b>{event.from_user.full_name}</b> забанен за спам!"
                )
            except Exception:
                pass
            return

        return await handler(event, data)
