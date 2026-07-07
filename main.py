"""Điểm khởi động bot dịch ngôn ngữ Telegram."""
import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import config
from handlers import cmd_start, on_approval, on_message

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_approval, pattern=r"^(approve|reject):\d+$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("Bot đang khởi động... (model: %s)", config.OPENAI_MODEL)
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
