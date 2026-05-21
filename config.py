import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))

SPAM_LIMIT: int = 5
SPAM_WINDOW: int = 10

MAX_HISTORY: int = 10
AI_MODEL: str = "gpt-4o"
IMAGE_MODEL: str = "dall-e-3"

DB_PATH: str = "bot_database.db"
