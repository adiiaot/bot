from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)


class HelpHandler:
    async def handle_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        help_text = """
<b>🤖 AOT Analyzer Bot Commands</b>

<b>/signal</b> — Generate a new XAU/USD trading signal
Uses 4-timeframe scalping strategy
Returns entry prices, TP levels, confidence

<b>/log_trade</b> — Log a completed trade
Step-by-step: entry price → exit price → result
Saves to Firestore, viewable on Dashboard

<b>/journal</b> — Add trading journal entry
Free-form text notes synced to Dashboard

<b>/stats</b> — View trading statistics
Shows total trades, win rate, P&L, streaks

<b>/dashboard</b> — Open web dashboard
Inline button linking to live analytics

<b>/clear</b> — Clear chat history
Resets the conversation

<b>/help</b> — Show this help message

<b>ℹ️ How It Works:</b>
1. <code>/signal</code> → get entry levels
2. Take the trade on MT5
3. <code>/log_trade</code> → record entry/exit/result
4. <code>/dashboard</code> → view performance
5. <code>/journal</code> → log your thoughts

<b>⚠️ Demo mode — no real money at risk.</b>
        """
        await update.message.reply_text(help_text.strip(), parse_mode='HTML')
        logger.info(f"Help sent to user {update.effective_user.id}")


help_handler = HelpHandler()
