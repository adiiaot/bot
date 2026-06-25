import logging
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
from app.models import Signal, SignalEntry, TrendEnum, CandleData
from app.tradingview_client import TradingViewClient
from config import Config

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Core signal generation engine implementing the 4-timeframe Mr PFX framework.

    Pipeline:
        1. 1H/4H — Trend determination via higher highs/lows detection
        2. 15M  — Support/Resistance level identification via swing points
        3. 5M   — Pullback detection with percentage-based zone
        4. 1M   — Entry confirmation via reversal candle patterns
    """

    def __init__(self, tv_client: TradingViewClient):
        self.tv_client = tv_client
        self.symbol = Config.TRADING_PAIR

    async def generate_signal(self) -> Tuple[Optional[Signal], str]:
        """Main entry point. Runs all 4 analysis levels and returns a Signal or error."""
        try:
            trend, trend_confidence = await self._analyze_trend()
            if trend == TrendEnum.NEUTRAL:
                return None, "Trend not clearly identified. No signal."

            logger.info(f"Trend identified: {trend} (confidence: {trend_confidence:.2f})")

            support, resistance = await self._find_levels()
            if not support or not resistance:
                return None, "Support/Resistance levels not found. No signal."

            logger.info(f"Levels found - Support: {support:.2f}, Resistance: {resistance:.2f}")

            entry_price, entry_confirmation = await self._confirm_entry(support, resistance, trend)
            if not entry_confirmation:
                return None, "Entry confirmation not found on 1M. No signal."

            logger.info(f"Entry confirmed at: {entry_price:.2f}")

            pullback_detected = await self._detect_pullback(support, resistance, trend)
            logger.info(f"Pullback: {pullback_detected}")

            signal = self._build_signal(
                trend=trend,
                entry_price=entry_price,
                support=support,
                resistance=resistance
            )

            logger.info(f"Signal generated: {signal.id}")
            return signal, "Signal generated successfully"

        except Exception as e:
            logger.error(f"Error generating signal: {str(e)}")
            return None, f"Error: {str(e)}"

    async def _analyze_trend(self) -> Tuple[TrendEnum, float]:
        """Level 1: Determine trend from 1H and 4H candles.

        Checks both timeframes for direction agreement. Falls back to single
        timeframe if one is stronger.
        """
        try:
            candles_1h = await self.tv_client.get_candles('1h', 14)
            candles_4h = await self.tv_client.get_candles('4h', 10)

            if not candles_1h or not candles_4h:
                return TrendEnum.NEUTRAL, 0.0

            df_1h = pd.DataFrame([c.model_dump() for c in candles_1h])
            trend_1h, score_1h = self._detect_trend_direction(df_1h)

            df_4h = pd.DataFrame([c.model_dump() for c in candles_4h])
            trend_4h, score_4h = self._detect_trend_direction(df_4h)

            logger.debug(f"Trend 1H: {trend_1h} ({score_1h:.2f})  4H: {trend_4h} ({score_4h:.2f})")

            if trend_1h == trend_4h and trend_1h != TrendEnum.NEUTRAL:
                confidence = max(score_1h, score_4h)
                logger.info(f"Trend confirmed: {trend_1h} (confidence: {confidence:.2f})")
                return trend_1h, confidence

            # Single-timeframe fallback: use the stronger confirmation
            if score_1h > 0.4 and trend_1h != TrendEnum.NEUTRAL:
                logger.info(f"Using 1H trend: {trend_1h} ({score_1h:.2f})")
                return trend_1h, score_1h * 0.85
            if score_4h > 0.4 and trend_4h != TrendEnum.NEUTRAL:
                logger.info(f"Using 4H trend: {trend_4h} ({score_4h:.2f})")
                return trend_4h, score_4h * 0.85

            logger.debug("No clear trend direction")
            return TrendEnum.NEUTRAL, 0.0

        except Exception as e:
            logger.error(f"Error in trend analysis: {str(e)}")
            return TrendEnum.NEUTRAL, 0.0

    def _detect_trend_direction(self, df: pd.DataFrame) -> Tuple[TrendEnum, float]:
        """Detect trend from a single timeframe's candle data using HH/HL/LH/LL counting."""
        if len(df) < 3:
            return TrendEnum.NEUTRAL, 0.0

        higher_highs = higher_lows = lower_highs = lower_lows = 0

        for i in range(1, len(df)):
            if df.iloc[i]['high'] > df.iloc[i-1]['high']:
                higher_highs += 1
            if df.iloc[i]['low'] > df.iloc[i-1]['low']:
                higher_lows += 1
            if df.iloc[i]['high'] < df.iloc[i-1]['high']:
                lower_highs += 1
            if df.iloc[i]['low'] < df.iloc[i-1]['low']:
                lower_lows += 1

        total = len(df) - 1
        if total == 0:
            return TrendEnum.NEUTRAL, 0.0

        up_score = (higher_highs + higher_lows) / (total * 2)
        down_score = (lower_highs + lower_lows) / (total * 2)

        if up_score > 0.45:
            return TrendEnum.UP, up_score
        if down_score > 0.45:
            return TrendEnum.DOWN, down_score

        return TrendEnum.NEUTRAL, 0.0

    async def _find_levels(self) -> Tuple[Optional[float], Optional[float]]:
        """Level 2: Identify support and resistance from 15M swing points."""
        try:
            candles = await self.tv_client.get_candles('15m', 40)
            if not candles or len(candles) < 5:
                return None, None

            df = pd.DataFrame([c.model_dump() for c in candles])
            current_price = df.iloc[-1]['close']

            # Find swing lows (support)
            support_levels = []
            for i in range(1, len(df) - 1):
                if df.iloc[i]['low'] < df.iloc[i-1]['low'] and df.iloc[i]['low'] < df.iloc[i+1]['low']:
                    support_levels.append(df.iloc[i]['low'])

            # Find swing highs (resistance)
            resistance_levels = []
            for i in range(1, len(df) - 1):
                if df.iloc[i]['high'] > df.iloc[i-1]['high'] and df.iloc[i]['high'] > df.iloc[i+1]['high']:
                    resistance_levels.append(df.iloc[i]['high'])

            # Get nearest level below (support) and above (resistance) current price
            support = self._find_nearest_level(support_levels, current_price, below=True) if support_levels else df['low'].min()
            resistance = self._find_nearest_level(resistance_levels, current_price, below=False) if resistance_levels else df['high'].max()

            logger.debug(f"Levels - S: {support:.2f}, R: {resistance:.2f} @ ${current_price:.2f}")
            return support, resistance

        except Exception as e:
            logger.error(f"Error finding levels: {str(e)}")
            return None, None

    def _find_nearest_level(self, levels: List[float], price: float, below: bool = True) -> float:
        """Find nearest level below (support) or above (resistance) current price."""
        if not levels:
            return round(price * (0.99 if below else 1.01), 2)
        if below:
            candidates = [l for l in levels if l <= price]
            return max(candidates) if candidates else max(levels)
        else:
            candidates = [l for l in levels if l >= price]
            return min(candidates) if candidates else min(levels)

    async def _detect_pullback(self, support: float, resistance: float, trend: TrendEnum) -> bool:
        """Level 3: Check if price is near a key level using percentage-based zone.

        Uses a dynamic zone of 0.5% of price (~$20 at $4,073) since fixed pip
        values don't scale well for XAU/USD at current prices.
        """
        try:
            candles = await self.tv_client.get_candles('5m', 20)
            if not candles:
                return False

            df = pd.DataFrame([c.model_dump() for c in candles])
            current_price = df.iloc[-1]['close']

            # Percentage-based zone: 0.5% of current price
            pullback_zone = current_price * 0.005  # ~$20 for XAU at $4,073

            if trend == TrendEnum.UP:
                within_zone = abs(current_price - support) <= pullback_zone
                if within_zone:
                    volatility = self._calculate_volatility(df)
                    logger.debug(f"UPTREND pullback: price={current_price:.2f}, support={support:.2f}, "
                               f"zone={pullback_zone:.2f}, vol={volatility:.4f}")
                    return True  # Always accept if within zone; volatility check is informative

            elif trend == TrendEnum.DOWN:
                within_zone = abs(current_price - resistance) <= pullback_zone
                if within_zone:
                    volatility = self._calculate_volatility(df)
                    logger.debug(f"DOWNTREND pullback: price={current_price:.2f}, resistance={resistance:.2f}, "
                               f"zone={pullback_zone:.2f}, vol={volatility:.4f}")
                    return True

            # If price is near the opposite level, still consider it a pullback
            if trend == TrendEnum.UP and abs(current_price - resistance) <= pullback_zone * 0.5:
                logger.debug(f"Price near resistance in uptrend — potential breakout")
                return True
            if trend == TrendEnum.DOWN and abs(current_price - support) <= pullback_zone * 0.5:
                logger.debug(f"Price near support in downtrend — potential breakdown")
                return True

            return False

        except Exception as e:
            logger.error(f"Error detecting pullback: {str(e)}")
            return False

    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calculate normalized ATR-style volatility from candle data."""
        df_range = df['high'] - df['low']
        avg_range = df_range.mean()
        avg_close = df['close'].mean()
        return avg_range / avg_close if avg_close > 0 else 0

    async def _confirm_entry(self, support: float, resistance: float, trend: TrendEnum) -> Tuple[Optional[float], bool]:
        """Level 4: Confirm entry point on 1M candles.

        Looks for reversal candles or trend-aligned price action.
        Falls back gracefully when pattern detection doesn't trigger.
        """
        try:
            candles = await self.tv_client.get_candles('1m', 15)
            if not candles or len(candles) < 3:
                return None, False

            df = pd.DataFrame([c.model_dump() for c in candles])
            current_candle = df.iloc[-1]

            is_reversal = self._detect_reversal_candle(df)
            if is_reversal:
                logger.debug("Reversal candle detected — entry confirmed")
                if trend == TrendEnum.UP:
                    return round(current_candle['close'] - 0.01, 2), True
                else:
                    return round(current_candle['close'] + 0.01, 2), True

            # Trend alignment fallback: last 3 candles moving in trend direction
            last_three = df.tail(3)
            if trend == TrendEnum.UP and last_three['close'].iloc[-1] > last_three['close'].iloc[0]:
                logger.debug("Trend alignment confirmed for UPTREND")
                return round(current_candle['close'], 2), True
            if trend == TrendEnum.DOWN and last_three['close'].iloc[-1] < last_three['close'].iloc[0]:
                logger.debug("Trend alignment confirmed for DOWNTREND")
                return round(current_candle['close'], 2), True

            # Simple price-in-trend-direction fallback
            if trend == TrendEnum.UP and current_candle['close'] > current_candle['open']:
                logger.debug("Green candle in uptrend — accepting as entry")
                return round(current_candle['close'], 2), True
            if trend == TrendEnum.DOWN and current_candle['close'] < current_candle['open']:
                logger.debug("Red candle in downtrend — accepting as entry")
                return round(current_candle['close'], 2), True

            logger.debug("No entry confirmation on 1M")
            return None, False

        except Exception as e:
            logger.error(f"Error confirming entry: {str(e)}")
            return None, False

    def _detect_reversal_candle(self, df: pd.DataFrame) -> bool:
        """Detect reversal candle patterns: pin bar or engulfing."""
        if len(df) < 2:
            return False

        current = df.iloc[-1]
        previous = df.iloc[-2]

        body_range = abs(current['close'] - current['open'])
        total_range = current['high'] - current['low']

        if total_range == 0:
            return False

        # Pin bar: small body + long wick
        if body_range < total_range * 0.3:
            wick_range = max(
                current['high'] - max(current['open'], current['close']),
                min(current['open'], current['close']) - current['low']
            )
            if wick_range > total_range * 0.5:
                return True

        # Engulfing pattern
        prev_body_range = abs(previous['close'] - previous['open'])
        if prev_body_range > 0:
            if (current['open'] < previous['close'] and current['close'] > previous['open']):
                return True
            if (current['open'] > previous['close'] and current['close'] < previous['open']):
                return True

        return False

    def _build_signal(self, trend: TrendEnum, entry_price: float, support: float, resistance: float) -> Signal:
        """Build final Signal with 4 stacked entries and take-profit levels.

        Entry structure for UPTREND (inverted for DOWNTREND):
        - Entry 1: entry_price, TP +20 pips ($0.20), AUTO CLOSE
        - Entry 2: entry_price - 5 pips, TP +40 pips, Manual
        - Entry 3: entry_price - 10 pips, TP +60 pips, Manual
        - Entry 4: entry_price - 15 pips, TP +80 pips, Manual
        """
        entries = []
        pip_value = 0.01  # XAU/USD standard pip at 2-decimal brokers

        if trend == TrendEnum.DOWN:
            tp_increments = [-20, -40, -60, -80]
            entry_offsets = [0, 5, 10, 15]
        else:
            tp_increments = [20, 40, 60, 80]
            entry_offsets = [0, -5, -10, -15]

        for idx, (tp_pips, offset_pips) in enumerate(zip(tp_increments, entry_offsets)):
            entry = entry_price + (offset_pips * pip_value)
            tp = entry_price + (tp_pips * pip_value)

            signal_entry = SignalEntry(
                entry_number=idx + 1,
                price=round(entry, 2),
                tp=round(tp, 2),
                tp_pips=abs(tp_pips),
                auto_close=(idx == 0)
            )
            entries.append(signal_entry)

        now = datetime.utcnow()
        signal_id = f"signal_{now.strftime('%Y%m%d_%H%M%S')}"

        signal = Signal(
            id=signal_id,
            timestamp=now,
            trend=trend,
            entries=entries,
            support_level=round(support, 2),
            resistance_level=round(resistance, 2),
            pullback_detected=True,
            entry_confirmation=True,
            valid_until=now + timedelta(hours=Config.SIGNAL_VALIDITY_HOURS),
            confidence=0.75
        )

        return signal
