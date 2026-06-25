from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)


class ClearHandler:
    async def handle_clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id

        try:
            sent = await context.bot.send_message(
                chat_id=chat_id,
                text="🧹 <b>Clearing chat history...</b>\n\n<i>Telegram bots cannot delete messages sent by users. "
                     "I'll delete my own messages from this chat instead.</i>",
                parse_mode='HTML'
            )

            await context.bot.delete_message(chat_id=chat_id, message_id=sent.message_id)

            try:
                await context.bot.delete_message(
                    chat_id=chat_id,
                    message_id=update.message.message_id
                )
            except Exception:
                pass

            await context.bot.send_message(
                chat_id=chat_id,
                text="✅ Chat cleared. Use /help to see available commands."
            )
            logger.info(f"Chat cleared for user {update.effective_user.id}")

        except Exception as e:
            logger.error(f"Error clearing chat: {str(e)}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="✅ <b>Chat Reset</b>\n\nStarted fresh! Use /help to see commands.",
                parse_mode='HTML'
            )


clear_handler = ClearHandler()
