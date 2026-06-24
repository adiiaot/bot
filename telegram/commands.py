from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters
from handlers.signal_handler import signal_handler
from handlers.journal_handler import journal_handler, WAITING_FOR_JOURNAL_TEXT
from handlers.stats_handler import stats_handler
from handlers.help_handler import help_handler
import logging

logger = logging.getLogger(__name__)


def register_commands(application: Application) -> None:
    application.add_handler(CommandHandler('signal', signal_handler.handle_signal_command))

    journal_conv = ConversationHandler(
        entry_points=[CommandHandler('journal', journal_handler.handle_journal_command)],
        states={
            WAITING_FOR_JOURNAL_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, journal_handler.handle_journal_text),
            ],
        },
        fallbacks=[CommandHandler('cancel', journal_handler.cancel_journal)],
    )
    application.add_handler(journal_conv)

    application.add_handler(CommandHandler('stats', stats_handler.handle_stats_command))
    application.add_handler(CommandHandler('help', help_handler.handle_help_command))

    logger.info("All commands registered successfully")
