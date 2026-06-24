from telegram import Update
from telegram.ext import ContextTypes
from app.signal_generator import SignalGenerator
from app.tradingview_client import TradingViewClient
from firestore.signals import signals_db
from firestore.logs import logs_db
import logging
import time

logger = logging.getLogger(__name__)


class SignalHandler:
    def __init__(self):
        self.tv_client = TradingViewClient()
        self.signal_gen = SignalGenerator(self.tv_client)

    async def handle_signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        start_time = time.time()

        try:
            status_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="🔄 Analyzing XAU/USD... generating signal..."
            )

            signal, error_msg = await self.signal_gen.generate_signal()

            if not signal:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=f"❌ {error_msg}"
                )
                await logs_db.log_command(str(user_id), '/signal', 'error', error=error_msg)
                return

            try:
                await signals_db.save_signal(user_id=str(user_id), signal=signal)
            except Exception as e:
                logger.error(f"Firestore save failed: {str(e)}")

            msg = self._format_signal_message(signal)
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=msg,
                parse_mode='HTML'
            )

            elapsed = int((time.time() - start_time) * 1000)
            await logs_db.log_command(str(user_id), '/signal', 'success', response=signal.id, processing_time_ms=elapsed)
            logger.info(f"Signal {signal.id} sent ({elapsed}ms)")

        except Exception as e:
            logger.error(f"Error in /signal: {str(e)}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ {str(e)}")

    def _format_signal_message(self, signal) -> str:
        trend_emoji = "📈 UP" if signal.trend.value == "UP" else "📉 DOWN"
        entries = "\n".join(
            f"Entry {i+1}: {e.price:.2f} | TP: {e.tp:.2f} (+{e.tp_pips}p) {'🔄 AUTO' if e.auto_close else '✋ MANUAL'}"
            for i, e in enumerate(signal.entries)
        )
        return f"""
<b>🎯 SIGNAL GENERATED</b>

<b>Trend:</b> {trend_emoji}
<b>Confidence:</b> {signal.confidence * 100:.0f}%

<b>Levels:</b>
  Support: {signal.support_level:.2f}
  Resistance: {signal.resistance_level:.2f}

<b>Entry Structure:</b>
{entries}

<b>Valid Until:</b> {signal.valid_until.strftime('%H:%M UTC')}
""".strip()


signal_handler = SignalHandler()
