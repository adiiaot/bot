import logging
from fastapi import APIRouter
from app.tradingview_client import TradingViewClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["price"])
tv_client = TradingViewClient()


@router.get("/price")
async def get_price(timeframe: str = "1m", limit: int = 1):
    candles = await tv_client.get_candles(timeframe, limit)
    if not candles or len(candles) == 0:
        return {"success": False, "error": "No price data available"}

    latest = candles[-1]
    return {
        "success": True,
        "symbol": tv_client.symbol,
        "price": latest.close,
        "high": latest.high,
        "low": latest.low,
        "open": latest.open,
        "close": latest.close,
        "volume": latest.volume,
        "timestamp": latest.time,
        "change24h": 0,
        "changePercent24h": 0,
        "spread": 0.5,
    }
