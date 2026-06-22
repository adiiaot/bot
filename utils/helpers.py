from datetime import datetime
from typing import Optional


def generate_id(prefix: str = 'signal') -> str:
    """Generate a unique ID with the given prefix and current UTC timestamp."""
    return f"{prefix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"


def generate_trade_id() -> str:
    """Shorthand for generate_id('trade')."""
    return generate_id('trade')


def round_price(value: float, decimals: int = 2) -> float:
    """Round a price value to the specified number of decimals."""
    return round(value, decimals)


def calculate_pnl(entry: float, exit_: float, result: str) -> float:
    """Calculate absolute P&L. If loss, returns absolute value."""
    pnl = exit_ - entry
    return abs(pnl) if result == 'loss' else pnl


def calculate_pnl_percent(entry: float, pnl: float) -> float:
    """Calculate P&L as a percentage of the entry price."""
    if entry == 0:
        return 0.0
    return (pnl / entry) * 100
