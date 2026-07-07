"""Đọc cấu hình từ file .env."""
import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Thiếu biến môi trường bắt buộc: {key} (kiểm tra file .env)")
    return value


TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
OWNER_ID = int(_require("OWNER_ID"))
OPENAI_API_KEY = _require("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
ALLOWED_USERS_FILE = os.getenv("ALLOWED_USERS_FILE", "allowed_users.json")
