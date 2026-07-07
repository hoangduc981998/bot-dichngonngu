"""Đọc cấu hình từ file .env."""
import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Thiếu biến môi trường bắt buộc: {key} (kiểm tra file .env)")
    return value


def _get_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None or value == "":
        return default
    return int(value)


TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
OWNER_ID = int(_require("OWNER_ID"))
OPENAI_API_KEY = _require("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
ALLOWED_USERS_FILE = os.getenv("ALLOWED_USERS_FILE", "allowed_users.json")
RATE_LIMIT_MAX = _get_int("RATE_LIMIT_MAX", 20)
RATE_LIMIT_WINDOW = _get_int("RATE_LIMIT_WINDOW", 60)
MAX_MESSAGE_LENGTH = _get_int("MAX_MESSAGE_LENGTH", 2000)
START_COOLDOWN_SECONDS = _get_int("START_COOLDOWN_SECONDS", 30)
