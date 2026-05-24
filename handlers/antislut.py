import re
import logging
from html import escape

from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated, MessageReactionUpdated
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION

from database.db import increment_banned, get_stats

router = Router()
logger = logging.getLogger(__name__)

# ───── Паттерны шлюхоботов ─────
SLUT_NAME_PATTERNS = [
    r"onlyfan", r"only.?fan", r"of.?link", r"18\+", r"nsfw",
    r"\bсекс\b", r"\bintim", r"\bэскорт", r"\bescort",
    r"заработ", r"доход", r"\d{4,}.*руб", r"privat", r"vip.?girl",
    r"hot.?girl", r"sexy", r"xxx", r"porn", r"nude", r"naked",
    r"модел", r"фото.?видео", r"подпис", r"переход", r"ссылк",
]

SLUT_TEXT_PATTERNS = SLUTNAME_PATTERNS = [
    r"onlyfan", r"only.?fan", r"18\+", r"nsfw", r"\bсекс\b",
    r"\bintim", r"\bэскорт", r"заработ", r"доход в день",
    r"privat", r"vip.?girl", r"hot.?girl", r"sexy", r"xxx",
    r"porn", r"nude", r"naked", r"подпис", r"переход по ссылк",
    r"пиши в лс", r"пиши мне", r"напиши мне", r"писать в личк",
    r"t\.me\/\+", r"t\.me\/[a-z0-9_]{5,}",
    r"💋", r"🔥.*💋", r"👅", r"🍑", r"💦",
]

SLUT_EMOJI_THRESHOLD = 5  # Если >5 одинаковых эмодзи в имени/тексте


def is_slutbot(text: str) -> bool:
    """Проверяет текст на паттерны шлюхобота"""
    if not text:
        return False
    text_lower = text.lower()
    for pattern in SLUTNAME_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    # Проверка на обилие сексуальных эмодзи
    slutty_emojis = ["💋", "🍑", "👅", "💦", "🔞", "😈", "🌶"]
    for emoji in slutty_emojis:
        if text.count(emoji) >= 2:
            return True
    return False


async def ban_slutbot(message_or_event, bot, chat_id: int, user_id: int, user_name: str):
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
        logger.info(f"Slutbot banned: {user_name} ({user_id}) in chat {chat_id}")
    except Exception as e:
        logger.warning(f"Failed to ban slutbot {user_id}: {e}")


# ───── 1. Проверка при заходе в чат ─────
@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_user_join(event: ChatMemberUpdated):
    user = event.new_chat_member.user
    if user.is_bot:
        return

    # Проверяем имя и фамилию
    full_name = f"{user.first_name or ''} {user.last_name or ''}"
    if is_slutbot(full_name):
        await ban_slutbot(event, event.bot, event.chat.id, user.id, user.username or full_name)
        return

    # Подозрительный профиль: нет юзернейма + странное имя
    slutty_emojis = ["💋", "🍑", "👅", "💦", "🔞", "😈"]
    emoji_count = sum(full_name.count(e) for e in slutty_emojis)
    if emoji_count >= 2:
        await ban_slutbot(event, event.bot, event.chat.id, user.id, user.username or full_name)


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

    if is_slutbot(text) or is_slutbot(full_name):
        try:
            await message.delete()
        except Exception:
            pass
        await ban_slutbot(message, message.bot, message.chat.id, user.id, user.username or full_name)


# ───── 3. Проверка реакций ─────
@router.message_reaction()
async def on_reaction_slutcheck(event: MessageReactionUpdated):
    if not event.user:
        return
    user = event.user
    if user.is_bot:
        return

    full_name = f"{user.first_name or ''} {user.last_name or ''}"
    if is_slutbot(full_name):
        await ban_slutbot(event, event.bot, event.chat.id, user.id, user.username or full_name)
