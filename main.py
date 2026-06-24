import logging
import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from telegram.ext import Application
from config import Config
from telegram_bot.commands import register_commands
from firestore.client import firestore_client
from routers.trades import router as trades_router
from routers.signals import router as signals_router
from routers.telegram import router as telegram_router
from routers.admin import router as admin_router

os.makedirs(Config.LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{Config.LOG_DIR}/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bot_app: Application | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start Telegram bot polling when FastAPI starts, stop on shutdown."""
    global bot_app
    logger.info("=" * 50)
    logger.info("Starting AOT Analyzer Bot (FastAPI + Telegram)")
    logger.info("=" * 50)

    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled")
    else:
        try:
            _ = firestore_client
            logger.info("Firebase Firestore connected")
        except Exception as e:
            logger.warning(f"Firebase connection: {str(e)} — continuing without Firestore")

        bot_app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        register_commands(bot_app)
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling(allowed_updates=['message', 'callback_query'])
        logger.info("Telegram bot polling started")

    yield

    if bot_app:
        logger.info("Shutting down Telegram bot...")
        await bot_app.updater.stop()
        await bot_app.stop()
        logger.info("Bot stopped.")


app = FastAPI(
    title="AOT Analyzer Bot API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trades_router)
app.include_router(signals_router)
app.include_router(telegram_router)
app.include_router(admin_router)


@app.get("/health")
async def health():
    return {"status": "ok", "bot": bot_app is not None}
