from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config
import logging

logger = logging.getLogger(__name__)


class DashboardHandler:
    async def handle_dashboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        dashboard_url = Config.DASHBOARD_URL
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Open Dashboard", url=dashboard_url)]
        ])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "<b>📊 Trading Dashboard</b>\n\n"
                "Click below to view your live performance metrics, "
                "trade history, signals, and AI Learning Hub."
            ),
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        logger.info(f"Dashboard link sent to user {update.effective_user.id}")


dashboard_handler = DashboardHandler()
