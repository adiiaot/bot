from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)


class HelpHandler:
    async def handle_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        help_text = """
<b>🤖 AOT Analyzer Bot Commands</b>

<b>/signal</b> — Generate a new trading signal
Analyzes XAU/USD using Mr PFX strategy
Returns entry prices, TP levels, confidence score

<b>/journal</b> — Add trading journal entry
Log your thoughts and observations
Synced to Dashboard

<b>/stats</b> — View trading statistics
Shows total signals and latest signals

<b>/help</b> — Show this help message

<b>ℹ️ How It Works:</b>
1. Use <code>/signal</code> to generate a signal
2. Take the trade manually on MT5
3. Log your thoughts with <code>/journal</code>
4. Check Dashboard for performance

<b>⚠️ Demo mode — no real money at risk.</b>
        """
        await update.message.reply_text(help_text.strip(), parse_mode='HTML')
        logger.info(f"Help sent to user {update.effective_user.id}")


help_handler = HelpHandler()
