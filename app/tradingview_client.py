import aiohttp
import logging
import random
import math
from typing import List, Optional
from datetime import datetime
from app.models import CandleData
from config import Config

logger = logging.getLogger(__name__)

TIMEFRAME_MULTIPLIERS = {
    "1m": 1, "5m": 5, "15m": 15, "30m": 30,
    "1h": 60, "2h": 120, "4h": 240, "1d": 1440,
}

BASE_XAU_PRICE = 4073.0


def _generate_simulated_candles(timeframe: str, limit: int, base_price: float = BASE_XAU_PRICE) -> List[CandleData]:
    """Generate realistic simulated XAU/USD OHLC candles when API is unavailable.

    Creates a slightly trending/bias series with realistic volatility per timeframe.
    """
    tf_minutes = TIMEFRAME_MULTIPLIERS.get(timeframe, 60)
    volatility = 0.0006 * math.sqrt(tf_minutes)
    trend_bias = random.uniform(-0.0003, 0.0003)
    now = int(datetime.utcnow().timestamp())
    interval_seconds = tf_minutes * 60
    candles = []
    price = base_price

    for i in range(limit):
        ts = now - (limit - i) * interval_seconds
        o = price
        drift = trend_bias + random.uniform(-volatility, volatility)
        c = o * (1 + drift)
        rng = abs(c - o) * random.uniform(0.3, 1.5) + 0.5
        h = max(o, c) + rng * random.uniform(0.1, 0.6)
        l_ = min(o, c) - rng * random.uniform(0.1, 0.6)
        vol = random.randint(100, 5000)

        candles.append(CandleData(
            time=ts,
            open=round(o, 2),
            high=round(h, 2),
            low=round(l_, 2),
            close=round(c, 2),
            volume=float(vol),
        ))
        price = c

    logger.info(f"Generated {len(candles)} simulated candles for {timeframe} (base: ${base_price:.0f})")
    return candles


class TradingViewClient:
    """Wrapper for TradingView Data API via RapidAPI with auto-fallback to simulated data.

    Primary: tries TradingView RapidAPI endpoint.
    Fallback: generates realistic simulated XAU/USD candle data when API is unavailable,
    rate-limited, or returns errors — ensuring the signal pipeline always has data.
    """

    def __init__(self):
        self.base_url = Config.TRADINGVIEW_BASE_URL
        self.api_key = Config.TRADINGVIEW_API_KEY
        self.api_host = Config.TRADINGVIEW_API_HOST
        self.symbol = Config.TRADING_PAIR
        self.request_count = 0
        self.rate_limit = Config.TRADINGVIEW_REQUESTS_LIMIT
        self._use_fallback = False

    async def _try_api_once(self, timeframe: str, limit: int) -> Optional[List[CandleData]]:
        """Attempt one real API call. Returns None if it fails (sets fallback mode for future calls)."""
        url = f"{self.base_url}/api/price/{self.symbol}"
        params = {'timeframe': timeframe, 'range': limit}
        headers = {
            'x-rapidapi-host': self.api_host,
            'x-rapidapi-key': self.api_key
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.request_count += 1
                        bars = data.get('data', {}).get('history', [])
                        if bars:
                            logger.info(f"Fetched {len(bars)} candles from TradingView API")
                            return self._parse_candles(bars)
                    else:
                        logger.warning(f"TradingView API returned {response.status}")
        except Exception as e:
            logger.warning(f"TradingView API unreachable: {str(e)}")
        return None

    async def get_candles(self, timeframe: str, limit: int) -> Optional[List[CandleData]]:
        """Fetch OHLCV candles from TradingView API or fallback simulation.

        First call tries the real API. If it succeeds, continues using it.
        On any failure (network, rate-limit, empty response), permanently
        switches to simulated data so all subsequent calls are instant.
        """
        if self._use_fallback:
            return _generate_simulated_candles(timeframe, limit)

        if not self.api_key or self.api_key == "your_rapidapi_key":
            logger.warning("TradingView API key not configured — using simulated data")
            self._use_fallback = True
            return _generate_simulated_candles(timeframe, limit)

        if self.request_count >= self.rate_limit:
            logger.warning("Rate limit reached — switching to simulated data")
            self._use_fallback = True
            return _generate_simulated_candles(timeframe, limit)

        result = await self._try_api_once(timeframe, limit)
        if result is not None:
            return result

        logger.info("Switching to simulated data for all future requests")
        self._use_fallback = True
        return _generate_simulated_candles(timeframe, limit)

    def _parse_candles(self, bars: list) -> List[CandleData]:
        candles = []
        for bar in bars:
            candle = CandleData(
                time=bar.get('time'),
                open=float(bar.get('open', 0)),
                high=float(bar.get('max', 0)),
                low=float(bar.get('min', 0)),
                close=float(bar.get('close', 0)),
                volume=float(bar.get('volume', 0) or 0)
            )
            candles.append(candle)
        return candles

    def get_request_count(self) -> dict:
        return {
            'used': self.request_count,
            'limit': self.rate_limit,
            'remaining': self.rate_limit - self.request_count,
            'fallback_active': self._use_fallback,
        }
