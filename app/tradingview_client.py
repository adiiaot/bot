import aiohttp
import logging
from typing import List, Optional
from datetime import datetime
from app.models import CandleData
from config import Config

logger = logging.getLogger(__name__)

YAHOO_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/XAUUSD=X'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

TIMEFRAME_MAP = {
    '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
    '1h': '60m', '1H': '60m', '4h': '60m', '4H': '60m',
    '1d': '1d', 'D': '1d',
}

RANGE_MAP = {
    '1m': '5d', '5m': '5d', '15m': '1mo', '30m': '1mo',
    '1h': '3mo', '1H': '3mo', '4h': '3mo', '4H': '3mo',
    '1d': '1y', 'D': '1y',
}

AGGREGATE_TFS = {'4h', '4H'}


def _aggregate_candles(candles: List[CandleData], group_size: int) -> List[CandleData]:
    result = []
    for i in range(0, len(candles), group_size):
        group = candles[i:i + group_size]
        if len(group) < group_size:
            continue
        result.append(CandleData(
            time=group[0].time,
            open=round(group[0].open, 2),
            high=round(max(c.high for c in group), 2),
            low=round(min(c.low for c in group), 2),
            close=round(group[-1].close, 2),
            volume=sum(c.volume for c in group),
        ))
    return result


def _parse_yahoo_candles(data: dict, timeframe: str) -> Optional[List[CandleData]]:
    result = data.get('chart', {}).get('result', [None])[0]
    if not result:
        return None
    timestamps = result.get('timestamp', [])
    quotes = result.get('indicators', {}).get('quote', [None])[0]
    if not timestamps or not quotes:
        return None

    candles = []
    for i in range(len(timestamps)):
        ts, o, h, l_, c, v = (
            timestamps[i], quotes['open'][i], quotes['high'][i],
            quotes['low'][i], quotes['close'][i], quotes['volume'][i],
        )
        if ts is None or o is None or h is None or l_ is None or c is None:
            continue
        candles.append(CandleData(
            time=int(ts), open=round(float(o), 2), high=round(float(h), 2),
            low=round(float(l_), 2), close=round(float(c), 2),
            volume=float(v or 0),
        ))

    if not candles:
        return None

    if timeframe in AGGREGATE_TFS:
        candles = _aggregate_candles(candles, 4)

    logger.info(f"Yahoo Finance: {len(candles)} candles for {timeframe}")
    return candles


def _parse_rapidapi_candles(bars: list) -> List[CandleData]:
    candles = []
    for bar in bars:
        try:
            candles.append(CandleData(
                time=int(bar.get('time', 0)),
                open=float(bar.get('open', 0)),
                high=float(bar.get('max', 0)),
                low=float(bar.get('min', 0)),
                close=float(bar.get('close', 0)),
                volume=float(bar.get('volume', 0) or 0),
            ))
        except (ValueError, TypeError):
            continue
    return candles


class TradingViewClient:
    """XAU/USD price client with Yahoo Finance (primary) + RapidAPI (fallback).

    No simulated data — returns None if both sources are unreachable.
    """

    def __init__(self):
        self.symbol = Config.TRADING_PAIR
        self._rapidapi_key = Config.TRADINGVIEW_API_KEY
        self._rapidapi_host = Config.TRADINGVIEW_API_HOST
        self._rapidapi_url = Config.TRADINGVIEW_BASE_URL
        self.request_count = 0
        self.last_error: Optional[str] = None

    async def _fetch_yahoo(self, timeframe: str) -> Optional[List[CandleData]]:
        interval = TIMEFRAME_MAP.get(timeframe, '60m')
        rng = RANGE_MAP.get(timeframe, '1mo')
        url = f'{YAHOO_URL}?interval={interval}&range={rng}'

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers={'User-Agent': USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    if resp.status != 200:
                        self.last_error = f'Yahoo HTTP {resp.status}'
                        logger.warning(f'Yahoo returned {resp.status}')
                        return None
                    data = await resp.json()
                    self.request_count += 1
                    return _parse_yahoo_candles(data, timeframe)
        except Exception as e:
            self.last_error = f'Yahoo error: {e}'
            logger.warning(f'Yahoo Finance unreachable: {e}')
            return None

    async def _fetch_rapidapi(self, timeframe: str, limit: int) -> Optional[List[CandleData]]:
        if not self._rapidapi_key or self._rapidapi_key == 'your_rapidapi_key':
            return None

        url = f'{self._rapidapi_url}/api/price/{self.symbol}'
        params = {'timeframe': timeframe, 'range': limit}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params,
                    headers={'x-rapidapi-host': self._rapidapi_host, 'x-rapidapi-key': self._rapidapi_key},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status != 200:
                        self.last_error = f'RapidAPI HTTP {resp.status}'
                        logger.warning(f'RapidAPI returned {resp.status}')
                        return None
                    data = await resp.json()
                    self.request_count += 1
                    bars = data.get('data', {}).get('history', [])
                    if bars:
                        candles = _parse_rapidapi_candles(bars)
                        logger.info(f'RapidAPI: {len(candles)} candles for {timeframe}')
                        return candles
                    self.last_error = 'RapidAPI empty response'
                    return None
        except Exception as e:
            self.last_error = f'RapidAPI error: {e}'
            logger.warning(f'RapidAPI unreachable: {e}')
            return None

    async def get_candles(self, timeframe: str, limit: int) -> Optional[List[CandleData]]:
        candles = await self._fetch_yahoo(timeframe)

        if candles is not None:
            return candles[-limit:] if len(candles) > limit else candles

        candles = await self._fetch_rapidapi(timeframe, limit)
        if candles is not None:
            return candles[-limit:] if len(candles) > limit else candles

        logger.error(f'All data sources failed for {timeframe} — no price data available')
        return None

    async def get_current_price(self) -> Optional[float]:
        candles = await self.get_candles('1m', 1)
        return candles[-1].close if candles else None

    def get_request_count(self) -> dict:
        return {
            'used': self.request_count,
            'limit': Config.TRADINGVIEW_REQUESTS_LIMIT,
            'remaining': Config.TRADINGVIEW_REQUESTS_LIMIT - self.request_count,
            'fallback_active': False,
            'last_error': self.last_error,
        }
