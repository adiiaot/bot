from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.firebase_manager import FirebaseManager
from app.models import TradeLog, TradeLogResponse, TradingStats

router = APIRouter(
    tags=["Trades"],
    prefix="/api"
)

db = FirebaseManager()


@router.post("/trades", response_model=TradeLogResponse)
async def log_trade(trade: TradeLog):
    """Log a completed trade with entry/exit prices and result.

    Calculates P&L and persists to Firestore.
    """
    result = await db.log_trade(trade)

    if result:
        return TradeLogResponse(
            id=result['id'],
            entry_price=trade.entry_price,
            exit_price=trade.exit_price,
            pnl=result['pnl'],
            pnl_percent=result['pnl_percent'],
            result=trade.result,
            timestamp=datetime.utcnow(),
            message="Trade logged successfully"
        )
    else:
        raise HTTPException(status_code=500, detail="Error logging trade")


@router.get("/trades", response_model=list)
async def get_trades():
    """Return all logged trades sorted by timestamp descending."""
    return await db.get_all_trades()


@router.get("/stats", response_model=TradingStats)
async def get_stats():
    """Compute and return aggregated trading statistics (win rate, P&L, streaks)."""
    stats = await db.calculate_stats()
    return stats
