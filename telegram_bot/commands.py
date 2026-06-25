from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters
from handlers.signal_handler import signal_handler
from handlers.journal_handler import journal_handler, WAITING_FOR_JOURNAL_TEXT
from handlers.stats_handler import stats_handler
from handlers.help_handler import help_handler
from handlers.dashboard_handler import dashboard_handler
from handlers.clear_handler import clear_handler
from handlers.log_trade_handler import log_trade_handler, ENTRY_PRICE, EXIT_PRICE, TRADE_RESULT, CONFIRM
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

    log_trade_conv = ConversationHandler(
        entry_points=[CommandHandler('log_trade', log_trade_handler.handle_log_trade_command)],
        states={
            ENTRY_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, log_trade_handler.handle_entry_price),
            ],
            EXIT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, log_trade_handler.handle_exit_price),
            ],
            TRADE_RESULT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, log_trade_handler.handle_result),
            ],
            CONFIRM: [
                CommandHandler('confirm', log_trade_handler.handle_confirm),
                MessageHandler(filters.TEXT & ~filters.COMMAND, log_trade_handler.handle_confirm),
            ],
        },
        fallbacks=[CommandHandler('cancel', log_trade_handler.cancel)],
    )
    application.add_handler(log_trade_conv)

    application.add_handler(CommandHandler('stats', stats_handler.handle_stats_command))
    application.add_handler(CommandHandler('dashboard', dashboard_handler.handle_dashboard_command))
    application.add_handler(CommandHandler('clear', clear_handler.handle_clear_command))
    application.add_handler(CommandHandler('help', help_handler.handle_help_command))

    logger.info("All commands registered successfully")
