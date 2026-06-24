from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from firestore.journal import journal_db
from firestore.logs import logs_db
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

WAITING_FOR_JOURNAL_TEXT = 1


class JournalHandler:
    async def handle_journal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="📝 <b>Trading Journal Entry</b>\n\nWhat would you like to note?\n\n<i>Send your entry (or /cancel to abort)</i>",
            parse_mode='HTML'
        )
        logger.info(f"User {user_id} started /journal")
        return WAITING_FOR_JOURNAL_TEXT

    async def handle_journal_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        journal_text = update.message.text

        try:
            entry_id = f"journal_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            success = await journal_db.save_journal_entry(str(user_id), entry_id, journal_text)

            if success:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ <b>Journal Entry Saved</b>\n\nEntry ID: <code>{entry_id}</code>\n\nSynced to Dashboard.",
                    parse_mode='HTML'
                )
                await logs_db.log_command(str(user_id), '/journal', 'success', response=entry_id)
            else:
                await context.bot.send_message(chat_id=chat_id, text="❌ Failed to save journal entry.")
                await logs_db.log_command(str(user_id), '/journal', 'error', error='Firestore save failed')
        except Exception as e:
            logger.error(f"Journal error: {str(e)}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {str(e)}")
            await logs_db.log_command(str(user_id), '/journal', 'error', error=str(e))

        return ConversationHandler.END

    async def cancel_journal(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Journal entry cancelled.")
        logger.info(f"User {update.effective_user.id} cancelled /journal")
        return ConversationHandler.END


journal_handler = JournalHandler()
