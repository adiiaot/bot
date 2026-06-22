import re
from typing import Optional


def validate_price(value: str) -> Optional[float]:
    """Parse a string as a positive float price. Returns None on failure."""
    try:
        price = float(value)
        if price <= 0:
            return None
        return price
    except (ValueError, TypeError):
        return None


def validate_trade_args(args: list) -> Optional[dict]:
    """Parse and validate Telegram /log_trade arguments.

    Expected format: entry:PRICE exit:PRICE result:win|loss
    Returns a dict with parsed values, or None if invalid.
    """
    parsed = {}
    for arg in args:
        if ':' not in arg:
            return None
        key, value = arg.split(':', 1)
        parsed[key.strip()] = value.strip()

    if 'entry' not in parsed or 'exit' not in parsed or 'result' not in parsed:
        return None

    entry = validate_price(parsed['entry'])
    exit_ = validate_price(parsed['exit'])

    if entry is None or exit_ is None:
        return None

    if parsed['result'] not in ('win', 'loss'):
        return None

    return {
        'entry': entry,
        'exit': exit_,
        'result': parsed['result']
    }
