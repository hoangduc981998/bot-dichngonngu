"""Các handler cho lệnh, tin nhắn và nút duyệt/từ chối."""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
from access_control import AccessControl
from rate_limiter import RateLimiter
from translator import translate

logger = logging.getLogger(__name__)

access = AccessControl(config.ALLOWED_USERS_FILE, config.OWNER_ID)
message_rate_limiter = RateLimiter(
    max_requests=config.RATE_LIMIT_MAX,
    window_seconds=config.RATE_LIMIT_WINDOW,
    exempt_user_ids={config.OWNER_ID},
)
start_rate_limiter = RateLimiter(
    max_requests=1,
    window_seconds=config.START_COOLDOWN_SECONDS,
    exempt_user_ids={config.OWNER_ID},
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    uid = user.id

    if access.is_allowed(uid):
        await update.message.reply_text(
            "👋 Chào bạn! Gửi tin nhắn để mình dịch:\n"
            "• Tiếng Anh → Tiếng Việt\n"
            "• Tiếng Trung → Tiếng Việt (kèm pinyin)\n"
            "• Tiếng Việt → Tiếng Anh (mặc định)\n"
            "• Thêm `en` hoặc `zh` để chọn ngôn ngữ đích, ví dụ:\n"
            "   `en xin chào` hoặc `xin chào zh`"
        )
        return

    is_pending = access.is_pending(uid)

    if not await start_rate_limiter.check(uid):
        if is_pending:
            logger.info("User %s đang chờ duyệt và gửi lại /start.", uid)
            await update.message.reply_text("⏳ Yêu cầu của bạn đang chờ duyệt. Vui lòng đợi quản trị viên phản hồi.")
        else:
            retry_after = await start_rate_limiter.get_retry_after(uid)
            logger.warning("User %s bị giới hạn /start, thử lại sau %s giây.", uid, retry_after)
            await update.message.reply_text(
                f"⏳ Bạn thao tác quá nhanh. Vui lòng chờ {retry_after} giây rồi thử lại /start."
            )
        return

    if is_pending:
        logger.info("User %s đang chờ duyệt và gửi lại /start.", uid)
        await update.message.reply_text("⏳ Yêu cầu của bạn đang chờ duyệt. Vui lòng đợi quản trị viên phản hồi.")
        return

    # Người lạ -> gửi yêu cầu về chủ bot
    access.add_pending(uid)
    await update.message.reply_text(
        "⏳ Yêu cầu sử dụng bot của bạn đã được gửi tới quản trị viên. "
        "Vui lòng chờ được duyệt."
    )

    uname = f"@{user.username}" if user.username else "(không có username)"
    text = (
        "🔔 *Yêu cầu sử dụng bot mới*\n"
        f"• Tên: {user.full_name}\n"
        f"• Username: {uname}\n"
        f"• ID: `{uid}`"
    )
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Đồng ý", callback_data=f"approve:{uid}"),
            InlineKeyboardButton("❌ Từ chối", callback_data=f"reject:{uid}"),
        ]]
    )
    await context.bot.send_message(
        chat_id=config.OWNER_ID, text=text,
        parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard,
    )


async def on_approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.from_user.id != config.OWNER_ID:
        await query.answer("Bạn không có quyền.", show_alert=True)
        return

    action, uid_str = query.data.split(":")
    uid = int(uid_str)

    if action == "approve":
        access.approve(uid)
        await query.edit_message_text(f"✅ Đã duyệt user `{uid}`.", parse_mode=ParseMode.MARKDOWN)
        try:
            await context.bot.send_message(uid, "🎉 Bạn đã được duyệt! Gửi tin nhắn để bắt đầu dịch.")
        except Exception as e:  # noqa: BLE001
            logger.warning("Không gửi được thông báo cho %s: %s", uid, e)
    else:
        access.reject(uid)
        await query.edit_message_text(f"❌ Đã từ chối user `{uid}`.", parse_mode=ParseMode.MARKDOWN)
        try:
            await context.bot.send_message(uid, "😔 Rất tiếc, yêu cầu của bạn chưa được chấp thuận.")
        except Exception as e:  # noqa: BLE001
            logger.warning("Không gửi được thông báo cho %s: %s", uid, e)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not access.is_allowed(uid):
        await update.message.reply_text("⛔ Bạn chưa được phép dùng bot. Gõ /start để gửi yêu cầu.")
        return

    text = update.message.text
    if not text:
        return

    if len(text) > config.MAX_MESSAGE_LENGTH:
        logger.warning("User %s gửi tin quá dài: %s ký tự.", uid, len(text))
        await update.message.reply_text(
            f"⚠️ Tin nhắn quá dài (tối đa {config.MAX_MESSAGE_LENGTH} ký tự). "
            "Vui lòng rút gọn hoặc chia nhỏ."
        )
        return

    if not await message_rate_limiter.check(uid):
        retry_after = await message_rate_limiter.get_retry_after(uid)
        logger.warning("User %s bị rate limit, thử lại sau %s giây.", uid, retry_after)
        await update.message.reply_text(
            f"⏳ Bạn gửi quá nhanh. Vui lòng chờ {retry_after} giây rồi thử lại."
        )
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        result = await translate(text)
        await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi dịch: %s", e)
        await update.message.reply_text("⚠️ Có lỗi khi dịch, vui lòng thử lại sau.")
