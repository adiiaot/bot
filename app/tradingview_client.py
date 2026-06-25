import aiohttp
import logging
from typing import List, Optional
from app.models import CandleData
from config import Config

logger = logging.getLogger(__name__)


class TradingViewClient:
    """Wrapper for TradingView Data API via RapidAPI.

    Handles OHLCV candle data requests with built-in rate limiting.
    Tracks request count against the free-tier monthly cap.
    """

    def __init__(self):
        self.base_url = Config.TRADINGVIEW_BASE_URL
        self.api_key = Config.TRADINGVIEW_API_KEY
        self.api_host = Config.TRADINGVIEW_API_HOST
        self.symbol = Config.TRADING_PAIR
        self.request_count = 0
        self.rate_limit = Config.TRADINGVIEW_REQUESTS_LIMIT

    async def get_candles(self, timeframe: str, limit: int) -> Optional[List[CandleData]]:
        """Fetch OHLCV candles from TradingView API.

        Args:
            timeframe: '1m', '5m', '15m', '1h', '4h', or '1d'.
            limit: Number of candles to fetch (10-100).

        Returns:
            List of CandleData objects, or None on failure/rate-limit.
        """
        if self.request_count >= self.rate_limit:
            logger.warning(f"Rate limit reached ({self.request_count}/{self.rate_limit})")
            return None

        try:
            url = f"{self.base_url}/api/price/{self.symbol}"
            params = {'timeframe': timeframe, 'range': limit}
            headers = {
                'x-rapidapi-host': self.api_host,
                'x-rapidapi-key': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.request_count += 1
                        bars = data.get('data', {}).get('history', [])
                        logger.info(f"Fetched {len(bars)} candles for {self.symbol} {timeframe}")
                        return self._parse_candles(bars)
                    else:
                        logger.error(f"TradingView API error: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error fetching candles: {str(e)}")
            return None

    def _parse_candles(self, bars: list) -> List[CandleData]:
        """Parse TradingView API price history into CandleData objects.

        The /api/price endpoint returns history with fields:
        time, open, close, max (high), min (low), volume.
        """
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
        """Return TradingView API request statistics (used/limit/remaining)."""
        return {
            'used': self.request_count,
            'limit': self.rate_limit,
            'remaining': self.rate_limit - self.request_count
        }
