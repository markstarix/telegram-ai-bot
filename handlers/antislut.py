import re
import logging

from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated, MessageReactionUpdated
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION

from database.db import increment_banned, get_stats

router = Router()
logger = logging.getLogger(__name__)

# ───── Паттерны шлюхоботов ─────
SLUT_PATTERNS = [
    r"onlyfan", r"only.?fan", r"of.?link", r"18\+", r"nsfw",
    r"\bсекс\b", r"\bintim", r"\bэскорт", r"\bescort",
    r"заработ", r"доход", r"\d{4,}.*руб", r"privat", r"vip.?girl",
    r"hot.?girl", r"sexy", r"xxx", r"porn", r"nude", r"naked",
    r"модел", r"фото.?видео", r"подпис", r"переход", r"ссылк",
    r"пиши в лс", r"пиши мне", r"напиши мне", r"писать в личк",
    r"t\.me\/\+", r"t\.me\/[a-z0-9_]{5,}",
    r"доход в день",
]

SLUT_EMOJIS = ["💋", "🍑", "👅", "💦", "🔞", "😈", "🌶"]


def is_slutbot(text: str) -> bool:
    """Проверяет текст на паттерны шлюхобота"""
    if not text:
        return False
    text_lower = text.lower()
    for pattern in SLUT_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    for emoji in SLUT_EMOJIS:
        if text.count(emoji) >= 2:
            return True
    return False


async def ban_slutbot(bot, chat_id: int, user_id: int, username: str):
    """Банит шлюхобота и отправляет сообщение со счётчиком"""
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


# ───── 1. Проверка при заходе в чат ─────
@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_user_join(event: ChatMemberUpdated):
    user = event.new_chat_member.user
    if user.is_bot:
        return

    full_name = f"{user.first_name or ''} {user.last_name or ''}"
    username = user.username or full_name

    if is_slutbot(full_name):
        await ban_slutbot(event.bot, event.chat.id, user.id, username)
        return

    emoji_count = sum(full_name.count(e) for e in SLUT_EMOJIS)
    if emoji_count >= 2:
        await ban_slutbot(event.bot, event.chat.id, user.id, username)


# ───── 2. Проверка сообщения ─────
@router.message(F.text)
async def on_message_slutcheck(message: Message):
    if not message.from_user or message.from_user.is_bot:
        return
    if message.chat.type not in ("group", "supergroup"):
        return

    user = message.from_user
    text = message.text or ""
    full_name = f"{user.first_name or ''} {user.last_name or ''}"
    username = user.username or full_name

    if is_slutbot(text) or is_slutbot(full_name):
        try:
            await message.delete()
        except Exception:
            pass
        await ban_slutbot(message.bot, message.chat.id, user.id, username)


# ───── 3. Проверка реакций ─────
@router.message_reaction()
async def on_reaction_slutcheck(event: MessageReactionUpdated):
    if not event.user or event.user.is_bot:
        return

    user = event.user
    full_name = f"{user.first_name or ''} {user.last_name or ''}"
    username = user.username or full_name

    if is_slutbot(full_name):
        await ban_slutbot(event.bot, event.chat.id, user.id, username)
