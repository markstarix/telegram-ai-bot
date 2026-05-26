import re
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import Router, BaseMiddleware
from aiogram.types import Message, ChatMemberUpdated, MessageReactionUpdated, TelegramObject
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION

from database.db import increment_banned, get_stats

router = Router()
logger = logging.getLogger(__name__)

# ───── Явные стоп-слова (срабатывают одиночно — 100% спам) ─────
# Только то что никогда не встречается в нормальной речи
HARD_PATTERNS = [
    r"onlyfan", r"only.?fan", r"of.?link",
    r"\bnsfw\b", r"\bxxx\b", r"\bporn\b", r"\bnude\b", r"\bnaked\b",
    r"\bescort\b", r"\bэскорт\b",
    r"vip.?girl", r"hot.?girl",
    r"t\.me\/\+[a-z0-9]+",          # инвайт-ссылки t.me/+xxxxx
]

# ───── Мягкие признаки (нужно 2+ для бана) ─────
SOFT_PATTERNS = [
    r"18\+",
    r"\bintim\b", r"\bинтим\b",
    r"\bsexy\b",
    r"пиши.{0,5}(лс|лично|мне)",
    r"напиши.{0,5}мне",
    r"писать.{0,10}лич",
    r"заработ.{0,20}(день|час|неделю|руб|тыс|\$)",
    r"доход.{0,20}(день|час|неделю|руб|тыс|\$)",
    r"\d{3,}.{0,10}(руб|тыс|к) в (день|час)",
    r"подпис.{0,15}(канал|ссылк|перейд)",
    r"переход.{0,10}(ссылк|канал)",
    r"t\.me\/[a-z0-9_]{5,}",        # любая t.me ссылка — мягкий признак
    r"фото.{0,5}видео.{0,20}(личн|лс|прива)",
    r"privat.{0,10}(фото|фот|контент)",
]

SLUT_EMOJIS = ["💋", "🍑", "👅", "💦", "🔞", "😈"]

# ───── Паттерны только для имён профилей (строгие) ─────
NAME_PATTERNS = [
    r"onlyfan", r"only.?fan", r"\bnsfw\b", r"\bxxx\b", r"\bporn\b",
    r"\bnude\b", r"\bnaked\b", r"\bescort\b", r"\bэскорт\b",
    r"vip.?girl", r"hot.?girl", r"\bsexy\b", r"18\+",
    r"\bintim\b", r"\bинтим\b",
]


def _count_soft(text: str) -> int:
    """Считает сколько мягких признаков найдено в тексте"""
    text_lower = text.lower()
    count = 0
    for pattern in SOFT_PATTERNS:
        if re.search(pattern, text_lower):
            count += 1
    return count


def is_slutbot_message(text: str) -> bool:
    """Проверяет текст сообщения — нужен хотя бы 1 жёсткий ИЛИ 2+ мягких признака"""
    if not text:
        return False
    text_lower = text.lower()

    # Жёсткие паттерны — достаточно одного
    for pattern in HARD_PATTERNS:
        if re.search(pattern, text_lower):
            return True

    # Мягкие паттерны — нужно 2+
    if _count_soft(text) >= 2:
        return True

    # 3+ сексуальных эмодзи в одном сообщении
    emoji_count = sum(text.count(e) for e in SLUT_EMOJIS)
    if emoji_count >= 3:
        return True

    return False


def is_slutbot_name(name: str) -> bool:
    """Проверяет имя профиля — более строгие паттерны"""
    if not name:
        return False
    name_lower = name.lower()
    for pattern in NAME_PATTERNS:
        if re.search(pattern, name_lower):
            return True
    # 2+ сексуальных эмодзи в имени
    emoji_count = sum(name.count(e) for e in SLUT_EMOJIS)
    if emoji_count >= 2:
        return True
    return False


async def ban_slutbot(bot, chat_id: int, user_id: int, username: str):
    try:
        await bot.ban_chat_member(chat_id, user_id)
        await increment_banned()
        stats = await get_stats()
        count = stats["banned"]
        await bot.send_message(
            chat_id,
            f"🚫 Шлюх*боты не пройдут 😎\n"
            f"┗ уничтожено: <b>{count}</b>",
        )
        logger.info(f"Slutbot banned: {username} ({user_id}) in chat {chat_id}")
    except Exception as e:
        logger.warning(f"Failed to ban slutbot {user_id}: {e}")


# ───── Middleware для проверки текстовых сообщений ─────
class AntiSlutMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if event.chat.type in ("group", "supergroup") and event.from_user and not event.from_user.is_bot:
            user = event.from_user
            text = event.text or ""
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            username = user.username or full_name

            # Имя — строгая проверка, текст — комбинированная
            if is_slutbot_name(full_name) or is_slutbot_message(text):
                try:
                    await event.delete()
                except Exception:
                    pass
                await ban_slutbot(event.bot, event.chat.id, user.id, username)
                return

        return await handler(event, data)


# ───── 1. Проверка при заходе в чат ─────
@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_user_join(event: ChatMemberUpdated):
    user = event.new_chat_member.user
    if user.is_bot:
        return

    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = user.username or full_name

    if is_slutbot_name(full_name):
        await ban_slutbot(event.bot, event.chat.id, user.id, username)


# ───── 2. Проверка реакций ─────
@router.message_reaction()
async def on_reaction_slutcheck(event: MessageReactionUpdated):
    if not event.user or event.user.is_bot:
        return

    user = event.user
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = user.username or full_name

    if is_slutbot_name(full_name):
        await ban_slutbot(event.bot, event.chat.id, user.id, username)
