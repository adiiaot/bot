import logging
from fastapi import APIRouter, Request
from app.telegram_handler import TelegramBotHandler

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Telegram"],
    prefix="/telegram"
)
bot_handler = TelegramBotHandler()


@router.post("")
async def telegram_webhook(update: dict):
    """Receive Telegram update via webhook (not actively used — bot runs in polling mode)."""
    logger.info("Received webhook update (stub)")
    return {"status": "ok"}
