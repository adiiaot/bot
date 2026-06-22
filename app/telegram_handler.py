from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
from app.signal_generator import SignalGenerator
from app.firebase_manager import FirebaseManager
from app.tradingview_client import TradingViewClient
from app.models import TradeLog, ResultEnum
from app.services.multi_model_pipeline import MultiModelPipeline
from config import Config
from utils.validators import validate_trade_args

logger = logging.getLogger(__name__)


class TelegramBotHandler:
    """Handles all Telegram bot interactions including commands and photo processing.

    Registers 6 slash commands and a photo handler with python-telegram-bot.
    Delegates signal generation, trade logging, and statistics to their respective
    backend services.
    """

    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.tv_client = TradingViewClient()
        self.signal_gen = SignalGenerator(self.tv_client)
        self.db = FirebaseManager()
        self.pipeline = MultiModelPipeline(self.signal_gen)

    async def setup_commands(self, app: Application):
        """Register slash commands with Telegram bot."""
        commands = [
            BotCommand('signal', 'Generate signal from API data'),
            BotCommand('analyze', 'Upload chart for dual-verified signal'),
            BotCommand('log_trade', 'Log a completed trade'),
            BotCommand('stats', 'View trading statistics'),
            BotCommand('dashboard', 'Open web dashboard'),
            BotCommand('help', 'Show all commands'),
        ]
        await app.bot.set_my_commands(commands)

    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signal — generate a signal from TradingView API data."""
        try:
            user_id = update.effective_user.id
            logger.info(f"User {user_id} requested signal")

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⏳ Analyzing XAU/USD chart...",
                parse_mode='Markdown'
            )

            signal, message = await self.signal_gen.generate_signal()

            if signal:
                response = self._format_signal_message(signal)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=response,
                    parse_mode='Markdown'
                )
                await self.db.save_signal(signal)
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ {message}"
                )

        except Exception as e:
            logger.error(f"Error in signal command: {str(e)}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Error: {str(e)}"
            )

    async def log_trade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /log_trade — record a completed trade with entry/exit prices."""
        try:
            args = context.args

            if len(args) < 3:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Usage: `/log_trade entry:2345.50 exit:2365.50 result:win`\nor `/log_trade entry:2345.50 exit:2340.00 result:loss`"
                )
                return

            parsed = validate_trade_args(args)
            if not parsed:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Invalid format. Use: entry:PRICE exit:PRICE result:win|loss"
                )
                return

            trade = TradeLog(
                entry_price=parsed['entry'],
                exit_price=parsed['exit'],
                result=ResultEnum(parsed['result'])
            )

            trade_result = await self.db.log_trade(trade)

            if trade_result:
                response = f"""
✅ **Trade Logged Successfully!**
📊 Entry: {trade.entry_price}
📊 Exit: {trade.exit_price}
💰 PnL: ${trade_result['pnl']:,.2f} ({trade_result['pnl_percent']:.2f}%)
✔️ Result: {trade.result.value.upper()}
                """
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=response,
                    parse_mode='Markdown'
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Error logging trade"
                )

        except ValueError as e:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Invalid format: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error in log_trade: {str(e)}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Error: {str(e)}"
            )

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats — display aggregated trading statistics."""
        try:
            stats = await self.db.calculate_stats()

            response = f"""
📊 **Trading Statistics (Demo)**
━━━━━━━━━━━━━━━━━━━━━━
📈 Total Trades: {stats['total_trades']}
✅ Wins: {stats['wins']}
❌ Losses: {stats['losses']}
🎯 Win Rate: {stats['win_rate']*100:.1f}%

💵 Total P&L: ${stats['total_pnl']:,.2f}
📊 Profit Factor: {stats['profit_factor']:.2f}x
📍 Avg Win: ${stats['avg_win']:,.2f}
📍 Avg Loss: ${stats['avg_loss']:,.2f}
            """

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=response,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error in stats command: {str(e)}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Error: {str(e)}"
            )

    async def dashboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dashboard — send inline button linking to the web dashboard."""
        try:
            dashboard_url = "https://analyzer-dashboard.vercel.app"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Open Dashboard", url=dashboard_url)]
            ])

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📊 **Trading Dashboard**\n\nClick below to view your performance metrics and trade logs.",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error in dashboard command: {str(e)}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help — display all available commands and instructions."""
        help_text = """
🤖 **Analyzer Bot - Commands**
━━━━━━━━━━━━━━━━━━━━━━
/signal - Generate signal from API data
/analyze - Upload chart for dual-verified signal
/log_trade - Log a completed trade
/stats - View trading statistics
/dashboard - Open web dashboard
/help - Show this message

📌 **How to Use:**
1. Request a signal with `/signal`
2. Execute 4 buy limit orders in MT5
3. Log trade result: `/log_trade entry:2345.50 exit:2365.50 result:win`
4. View stats: `/stats`
5. Monitor performance: `/dashboard`

⚙️ Trading Settings:
• Pair: XAU/USD
• Max Hold: 5 minutes
• Lot Size: 0.01
        """

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=help_text,
            parse_mode='Markdown'
        )

    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze — prompt user to upload a chart screenshot for vision-based analysis."""
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="""📊 **Chart Analysis Mode**

Please upload a XAU/USD chart screenshot for advanced verification.

The bot will:
1. Analyze your chart visually (support/resistance levels, patterns, trend)
2. Compare with TradingView API data
3. Generate a dual-verified signal with confidence score

Simply send the chart image and I'll process it!""",
                parse_mode='Markdown'
            )
            logger.info(f"User {update.effective_user.id} requested chart analysis")
        except Exception as e:
            logger.error(f"Error in analyze command: {str(e)}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Error starting analysis mode"
            )

    async def handle_screenshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process an uploaded chart screenshot through the multi-model pipeline."""
        try:
            if not update.message.photo:
                return

            user_id = update.effective_user.id
            logger.info(f"User {user_id} uploaded screenshot")

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⏳ Processing chart with multi-model AI (Vision + API verification)...",
                parse_mode='Markdown'
            )

            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)

            if file.file_size > Config.MAX_SCREENSHOT_SIZE_MB * 1024 * 1024:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ Screenshot too large (max {Config.MAX_SCREENSHOT_SIZE_MB}MB)"
                )
                return

            import base64
            file_data = await file.download_as_bytearray()
            image_base64 = base64.b64encode(file_data).decode()

            result = await self.pipeline.process_with_screenshot(
                api_data={},
                screenshot_base64=image_base64
            )

            if result['success']:
                response = self._format_verified_signal_message(result)
            else:
                response = f"❌ Analysis failed: {result.get('message', 'Unknown error')}"

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=response,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error processing screenshot: {str(e)}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Error processing screenshot: {str(e)}"
            )

    def _format_verified_signal_message(self, result: dict) -> str:
        """Format a dual-verified signal into a Markdown message string."""
        signal = result['signal']
        verification = result['verification']

        entries_text = "\n".join([
            f"Entry {i+1}: ${entry.price} | TP: ${entry.tp} (+{entry.tp_pips}pips)"
            for i, entry in enumerate(signal.entries)
        ])

        discrepancies_text = "\n".join(verification.get('discrepancies', ['None']))

        message = f"""
🎯 **XAU/USD VERIFIED SIGNAL** ✅
━━━━━━━━━━━━━━━━━━━━━━
📈 Trend: **{signal.trend.value}**
⏰ Time: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

**Entry Points:**
{entries_text}

📊 Support: ${signal.support_level}
📊 Resistance: ${signal.resistance_level}

**Verification Details:**
🔍 Score: {verification['score']}/100
📊 Data Source: {verification['data_source']}
🎯 Confidence Boost: {verification.get('confidence_boost', 'N/A')}
🤖 Chart Confidence: {verification.get('vision_confidence', 0):.1%}

**Discrepancies Found:**
{discrepancies_text}

⏱️ Valid Until: {signal.valid_until.strftime('%H:%M:%S UTC')} (3 hours)
        """
        return message

    def _format_signal_message(self, signal) -> str:
        """Format a standard (API-only) signal into a Markdown message string."""
        entries_text = "\n".join([
            f"Entry {i+1}: ${entry.price} | TP: ${entry.tp} (+{entry.tp_pips}pips) | {'Auto Close' if entry.auto_close else 'Manual'}"
            for i, entry in enumerate(signal.entries)
        ])

        message = f"""
🎯 **XAU/USD SIGNAL**
━━━━━━━━━━━━━━━━━━━━━━
📈 Trend: **{signal.trend.value}** ✅
⏰ Time: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

**Entry Points:**
{entries_text}

📊 Support: ${signal.support_level}
📊 Resistance: ${signal.resistance_level}
🔥 Confidence: {signal.confidence*100:.0f}%

⏱️ Valid Until: {signal.valid_until.strftime('%H:%M:%S UTC')} (3 hours)

✨ **Execute:** Place 4 buy limit orders as shown above
        """
        return message

    async def start_bot(self):
        """Build the PTB Application, register handlers, and start polling."""
        app = Application.builder().token(self.token).build()

        app.add_handler(CommandHandler("signal", self.signal_command))
        app.add_handler(CommandHandler("analyze", self.analyze_command))
        app.add_handler(CommandHandler("log_trade", self.log_trade_command))
        app.add_handler(CommandHandler("stats", self.stats_command))
        app.add_handler(CommandHandler("dashboard", self.dashboard_command))
        app.add_handler(CommandHandler("help", self.help_command))

        app.add_handler(MessageHandler(filters.PHOTO, self.handle_screenshot))

        await self.setup_commands(app)

        logger.info("Telegram bot started with screenshot analysis support")
        await app.run_polling()
