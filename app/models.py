from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TrendEnum(str, Enum):
    """Market trend direction detected by signal analysis."""
    UP = "UP"
    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"


class ResultEnum(str, Enum):
    """Outcome of a completed trade."""
    WIN = "win"
    LOSS = "loss"
    PENDING = "pending"


class CandleData(BaseModel):
    """Single OHLCV candlestick from TradingView."""
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class SignalEntry(BaseModel):
    """One entry leg of a trading signal with take-profit target."""
    price: float = Field(..., description="Entry price")
    tp: float = Field(..., description="Take profit price")
    tp_pips: int = Field(..., description="TP in pips")
    auto_close: bool = False


class Signal(BaseModel):
    """Complete trading signal with 4 stacked entries and market context."""
    id: str
    timestamp: datetime
    trend: TrendEnum
    entries: List[SignalEntry]
    support_level: float
    resistance_level: float
    pullback_detected: bool
    entry_confirmation: bool
    valid_until: datetime
    confidence: float


class SignalResponse(BaseModel):
    """Response wrapper for signal generation requests."""
    success: bool
    signal: Optional[Signal] = None
    message: str


class TradeLog(BaseModel):
    """Payload for logging a completed trade."""
    entry_price: float
    exit_price: float
    quantity: float = 0.01
    result: ResultEnum
    signal_id: Optional[str] = None
    notes: Optional[str] = None
    hold_time_seconds: Optional[int] = None


class TradeLogResponse(BaseModel):
    """Response returned after a trade is logged, includes calculated PnL."""
    id: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_percent: float
    result: ResultEnum
    timestamp: datetime
    message: str


class TradingStats(BaseModel):
    """Aggregated trading performance statistics."""
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    consecutive_wins: int
    consecutive_losses: int


class TelegramMessage(BaseModel):
    """Incoming Telegram message data."""
    message: str
    user_id: str
    timestamp: datetime
