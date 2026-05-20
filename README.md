# 🤖 Telegram AI Bot

Полнофункциональный Telegram-бот с искусственным интеллектом.

## ✨ Возможности

- 💬 Отвечает на любые вопросы (GPT-4o)
- 🖼 Генерирует изображения по описанию (DALL·E 3)
- 🚫 Автоматически банит спамеров
- 🔊 Распознаёт голосовые сообщения (Whisper)
- 🧠 Помнит историю диалога
- 👮 Система ролей: admin / user

## 🚀 Быстрый старт

### 1. Установи зависимости
```bash
pip install -r requirements.txt
```

### 2. Настрой `.env`
```bash
cp .env.example .env
# Открой .env и вставь свои токены
```

### 3. Запусти бота
```bash
python bot.py
```

## 🔑 Где взять токены

- **BOT_TOKEN** — [@BotFather](https://t.me/BotFather) → `/newbot`
- **OPENAI_API_KEY** — [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **ADMIN_ID** — напиши [@userinfobot](https://t.me/userinfobot) — он пришлёт твой ID

## 📁 Структура проекта

```
telegram-ai-bot/
├── bot.py
├── config.py
├── requirements.txt
├── .env.example
├── handlers/
│   ├── ai_chat.py
│   ├── image_gen.py
│   ├── voice.py
│   └── admin.py
├── middlewares/
│   └── antispam.py
├── database/
│   └── db.py
└── utils/
    └── helpers.py
```

## 📋 Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветствие |
| `/help` | Список команд |
| `/img <описание>` | Генерация картинки |
| `/clear` | Очистить историю диалога |
| `/ban` | (Админ) Забанить пользователя |
| `/unban` | (Админ) Разбанить пользователя |
| `/mute` | (Админ) Заглушить на 1 час |
| `/stats` | (Админ) Статистика бота |
