from telegram import Update
from telegram.ext import ContextTypes
from firestore.signals import signals_db
from firestore.logs import logs_db
import logging
import time

logger = logging.getLogger(__name__)


class StatsHandler:
    async def handle_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        start_time = time.time()

        try:
            signals = await signals_db.get_latest_signals(user_id=str(user_id), limit=3)

            if not signals:
                await context.bot.send_message(chat_id=chat_id, text="📊 <b>Trading Statistics</b>\n\nNo signals generated yet.")
                await logs_db.log_command(str(user_id), '/stats', 'success', response='No signals', processing_time_ms=int((time.time() - start_time) * 1000))
                return

            msg = f"<b>📊 Trading Statistics</b>\n\n<b>Total Signals:</b> {len(signals)}\n\n<b>Latest Signals:</b>\n"
            for i, s in enumerate(signals, 1):
                trend = "📈 UP" if s.get('trend') == 'UP' else "📉 DOWN"
                msg += f"{i}. {trend} | Support: {s.get('supportLevel', 'N/A')} | Resistance: {s.get('resistanceLevel', 'N/A')}\n"

            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML')
            await logs_db.log_command(str(user_id), '/stats', 'success', response=f'{len(signals)} signals', processing_time_ms=int((time.time() - start_time) * 1000))
        except Exception as e:
            logger.error(f"Error in /stats: {str(e)}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {str(e)}")
            await logs_db.log_command(str(user_id), '/stats', 'error', error=str(e))


stats_handler = StatsHandler()
