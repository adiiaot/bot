from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from firestore.trades import trades_db
from firestore.logs import logs_db
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

(ENTRY_PRICE, EXIT_PRICE, TRADE_RESULT, CONFIRM) = range(4)


class LogTradeHandler:
    async def handle_log_trade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data.clear()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="<b>📝 Log a Trade</b>\n\nLet's record your completed trade.\n\n"
                 "<b>Step 1/3:</b> What was the <b>entry price</b>?\n"
                 "<i>Example: 2325.50</i>\n\n"
                 "Send /cancel to abort.",
            parse_mode='HTML'
        )
        logger.info(f"User {update.effective_user.id} started /log_trade")
        return ENTRY_PRICE

    async def handle_entry_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = update.message.text.strip()
        try:
            entry = float(text)
            if entry <= 0:
                raise ValueError
            context.user_data['entry_price'] = entry
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Entry price: <b>{entry}</b>\n\n"
                     f"<b>Step 2/3:</b> What was the <b>exit price</b>?\n"
                     "<i>Example: 2355.80</i>\n\n"
                     "Send /cancel to abort.",
                parse_mode='HTML'
            )
            return EXIT_PRICE
        except (ValueError, TypeError):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Invalid price. Please enter a valid number like <b>2325.50</b>\n\n"
                     "Send /cancel to abort.",
                parse_mode='HTML'
            )
            return ENTRY_PRICE

    async def handle_exit_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = update.message.text.strip()
        try:
            exit_p = float(text)
            if exit_p <= 0:
                raise ValueError
            context.user_data['exit_price'] = exit_p
            keyboard = ReplyKeyboardMarkup(
                [['✅ Win', '❌ Loss']],
                one_time_keyboard=True,
                resize_keyboard=True
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Exit price: <b>{exit_p}</b>\n\n"
                     f"<b>Step 3/3:</b> What was the <b>result</b>?\n"
                     "Choose below or type 'win' or 'loss'.",
                parse_mode='HTML',
                reply_markup=keyboard
            )
            return TRADE_RESULT
        except (ValueError, TypeError):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Invalid price. Please enter a valid number like <b>2355.80</b>\n\n"
                     "Send /cancel to abort.",
                parse_mode='HTML'
            )
            return EXIT_PRICE

    async def handle_result(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = update.message.text.strip().lower().replace('✅', '').replace('❌', '').strip()
        if text not in ('win', 'loss'):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Please choose <b>Win</b> or <b>Loss</b> from the buttons or type 'win' or 'loss'.\n\n"
                     "Send /cancel to abort.",
                parse_mode='HTML',
                reply_markup=ReplyKeyboardMarkup(
                    [['✅ Win', '❌ Loss']],
                    one_time_keyboard=True,
                    resize_keyboard=True
                )
            )
            return TRADE_RESULT

        context.user_data['result'] = text
        entry = context.user_data['entry_price']
        exit_p = context.user_data['exit_price']

        pnl = exit_p - entry
        direction = "LONG" if pnl >= 0 else "SHORT"
        pnl_abs = abs(pnl)
        pnl_percent = (pnl / entry) * 100 if entry else 0

        direction_label = "📈 LONG" if direction == "LONG" else "📉 SHORT"

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"<b>📋 Trade Summary</b>\n\n"
                f"Entry: <b>{entry}</b>\n"
                f"Exit: <b>{exit_p}</b>\n"
                f"Direction: {direction_label}\n"
                f"PnL: <b>${pnl_abs:.2f}</b> ({'✅' if text == 'win' else '❌'} {pnl_percent:+.2f}%)\n"
                f"Result: <b>{text.upper()}</b>\n\n"
                f"Send <b>/confirm</b> to save or /cancel to discard."
            ),
            parse_mode='HTML',
            reply_markup=ReplyKeyboardRemove()
        )
        return CONFIRM

    async def handle_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        entry = context.user_data['entry_price']
        exit_p = context.user_data['exit_price']
        result = context.user_data['result']

        pnl = exit_p - entry
        pnl_percent = (pnl / entry) * 100 if entry else 0

        trade_id = f"trade_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"

        trade_data = {
            'tradeId': trade_id,
            'userId': str(user_id),
            'timestamp': datetime.utcnow(),
            'entryPrice': entry,
            'exitPrice': exit_p,
            'entrySize': 0.01,
            'entryTime': datetime.utcnow(),
            'exitTime': datetime.utcnow(),
            'pnl': round(pnl, 2),
            'pnlPercent': round(pnl_percent, 2),
            'result': result,
            'trend': 'UP' if pnl >= 0 else 'DOWN',
            'supportLevel': 0,
            'resistanceLevel': 0,
            'stopLoss': 0,
            'takeProfit': 0,
            'riskRewardRatio': 0,
            'status': 'closed',
            'holdTimeSeconds': None,
            'journalNotes': '',
            'tradingConditions': '',
        }

        try:
            saved_id = await trades_db.save_trade(trade_data)
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ <b>Trade Logged Successfully!</b>\n\n"
                    f"ID: <code>{trade_id}</code>\n"
                    f"PnL: <b>${pnl:+.2f}</b> ({pnl_percent:+.2f}%)\n"
                    f"Result: {'✅ WIN' if result == 'win' else '❌ LOSS'}\n\n"
                    f"Synced to Dashboard."
                ),
                parse_mode='HTML'
            )
            await logs_db.log_command(str(user_id), '/log_trade', 'success', response=trade_id)
        except Exception as e:
            logger.error(f"Error saving trade: {str(e)}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Failed to save trade. Please try again."
            )
            await logs_db.log_command(str(user_id), '/log_trade', 'error', error=str(e))

        context.user_data.clear()
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data.clear()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Trade logging cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
        logger.info(f"User {update.effective_user.id} cancelled /log_trade")
        return ConversationHandler.END


log_trade_handler = LogTradeHandler()
