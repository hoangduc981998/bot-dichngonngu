import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "dummy-token")
os.environ.setdefault("OWNER_ID", "1")
os.environ.setdefault("OPENAI_API_KEY", "dummy-key")

import handlers


class HandlersTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_on_message_rejects_too_long_text_before_translate(self) -> None:
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=123),
            effective_chat=SimpleNamespace(id=456),
            message=SimpleNamespace(
                text="x" * (handlers.config.MAX_MESSAGE_LENGTH + 1),
                reply_text=AsyncMock(),
            ),
        )
        context = SimpleNamespace(bot=SimpleNamespace(send_chat_action=AsyncMock()))

        with (
            patch.object(handlers.access, "is_allowed", return_value=True),
            patch.object(handlers, "translate", new=AsyncMock()) as translate_mock,
            patch.object(handlers.message_rate_limiter, "check", new=AsyncMock()) as check_mock,
        ):
            await handlers.on_message(update, context)

        translate_mock.assert_not_awaited()
        check_mock.assert_not_awaited()
        context.bot.send_chat_action.assert_not_awaited()
        update.message.reply_text.assert_awaited_once()
        self.assertIn("Tin nhắn quá dài", update.message.reply_text.await_args.args[0])

    async def test_cmd_start_pending_user_does_not_notify_owner_again(self) -> None:
        user = SimpleNamespace(id=123, username="guest", full_name="Guest User")
        update = SimpleNamespace(
            effective_user=user,
            message=SimpleNamespace(reply_text=AsyncMock()),
        )
        context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))

        access_mock = MagicMock()
        access_mock.is_allowed.return_value = False
        access_mock.is_pending.return_value = True

        with (
            patch.object(handlers, "access", access_mock),
            patch.object(handlers.start_rate_limiter, "check", new=AsyncMock(return_value=False)) as check_mock,
        ):
            await handlers.cmd_start(update, context)

        check_mock.assert_awaited_once_with(123)
        context.bot.send_message.assert_not_awaited()
        access_mock.add_pending.assert_not_called()
        update.message.reply_text.assert_awaited_once()
        self.assertIn("đang chờ duyệt", update.message.reply_text.await_args.args[0])
