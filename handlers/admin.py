from datetime import datetime, timedelta

from aiogram import Router
from aiogram.types import Message, ChatPermissions
from aiogram.filters import Command

from config import ADMIN_ID
from database.db import get_stats

router = Router()


def is_admin(message: Message) -> bool:
    return message.from_user.id == ADMIN_ID


@router.message(Command("ban"))
async def ban_handler(message: Message):
    if not is_admin(message):
        await message.answer("⛔ У тебя нет прав администратора.")
        return
    if not message.reply_to_message:
        await message.answer("↩️ Ответь на сообщение пользователя, которого хочешь забанить.")
        return
    target = message.reply_to_message.from_user
    try:
        await message.chat.ban(target.id)
        await message.answer(f"🚫 Пользователь <b>{target.full_name}</b> забанен.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(Command("unban"))
async def unban_handler(message: Message):
    if not is_admin(message):
        await message.answer("⛔ У тебя нет прав администратора.")
        return
    if not message.reply_to_message:
        await message.answer("↩️ Ответь на сообщение пользователя, которого хочешь разбанить.")
        return
    target = message.reply_to_message.from_user
    try:
        await message.chat.unban(target.id)
        await message.answer(f"✅ Пользователь <b>{target.full_name}</b> разбанен.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(Command("mute"))
async def mute_handler(message: Message):
    if not is_admin(message):
        await message.answer("⛔ У тебя нет прав администратора.")
        return
    if not message.reply_to_message:
        await message.answer("↩️ Ответь на сообщение пользователя, которого хочешь заглушить.")
        return
    target = message.reply_to_message.from_user
    try:
        until = datetime.now() + timedelta(hours=1)
        await message.chat.restrict(
            target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until
        )
        await message.answer(f"🔇 Пользователь <b>{target.full_name}</b> заглушен на 1 час.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(Command("stats"))
async def stats_handler(message: Message):
    if not is_admin(message):
        await message.answer("⛔ У тебя нет прав администратора.")
        return
    stats = await get_stats()
    await message.answer(
        f"📊 <b>Статистика бота:</b>\n\n"
        f"👥 Пользователей: <b>{stats['users']}</b>\n"
        f"💬 Сообщений: <b>{stats['messages']}</b>\n"
        f"🚫 Забанено спамеров: <b>{stats['banned']}</b>"
    )
