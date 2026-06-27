import logging
import math
from typing import List, Tuple, Optional, Dict
from datetime import datetime, timedelta
import pandas as pd
from app.models import Signal, SignalEntry, TrendEnum, CandleData
from app.tradingview_client import TradingViewClient
from config import Config

logger = logging.getLogger(__name__)

PIP_VALUE = 0.10
SWING_LOOKBACK = 2
LEVELS_LOOKBACK = 3
SIGNAL_THRESHOLD = 0.55
WEIGHTS = [0.20, 0.15, 0.20, 0.20, 0.10, 0.15]
COMPONENTS = ['rejection', 'internal_region', 'structure', 'sr_bias', 'breakout', 'bob']


class SignalGenerator:
    """Core signal generation engine implementing the 4-timeframe Mr PFX framework.

    Pipeline:
        1. 1H/4H — Trend determination via swing point HH/HL/LH/LL detection
        2. 15M  — Support/Resistance level identification via clustered swing points
        3. 15M  — Mr. PFX 6-component scoring (hard gate: >= 0.55)
        4. 5M   — ATR-based pullback detection (hard gate)
        5. 1M   — Entry confirmation via reversal / structure break / momentum (hard gate)
    """

    def __init__(self, tv_client: TradingViewClient):
        self.tv_client = tv_client
        self.symbol = Config.TRADING_PAIR

    # ─── Swing Point Detection ───────────────────────────────────────────────

    def _find_swing_highs(self, df: pd.DataFrame, n: int = SWING_LOOKBACK) -> List[int]:
        indices = []
        for i in range(n, len(df) - n):
            left = all(df['high'].iloc[i] > df['high'].iloc[i - j] for j in range(1, n + 1))
            right = all(df['high'].iloc[i] > df['high'].iloc[i + j] for j in range(1, n + 1))
            if left and right:
                indices.append(i)
        return indices

    def _find_swing_lows(self, df: pd.DataFrame, n: int = SWING_LOOKBACK) -> List[int]:
        indices = []
        for i in range(n, len(df) - n):
            left = all(df['low'].iloc[i] < df['low'].iloc[i - j] for j in range(1, n + 1))
            right = all(df['low'].iloc[i] < df['low'].iloc[i + j] for j in range(1, n + 1))
            if left and right:
                indices.append(i)
        return indices

    # ─── ATR Calculation ─────────────────────────────────────────────────────

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(period, min_periods=period).mean()
        if pd.isna(atr.iloc[-1]):
            return true_range.tail(period).mean() if len(true_range) >= period else true_range.mean()
        return atr.iloc[-1]

    # ─── Trend & Structure Analysis ──────────────────────────────────────────

    async def _analyze_trend(self, df_1h: pd.DataFrame, df_4h: pd.DataFrame) -> Tuple[TrendEnum, float]:
        try:
            sh_1h = self._find_swing_highs(df_1h)
            sl_1h = self._find_swing_lows(df_1h)
            sh_4h = self._find_swing_highs(df_4h)
            sl_4h = self._find_swing_lows(df_4h)

            def classify(swing_highs, swing_lows):
                if len(swing_highs) < 2 or len(swing_lows) < 2:
                    return TrendEnum.NEUTRAL, 0.0
                sh_prices = [df_1h['high'].iloc[i] for i in swing_highs[-3:]]
                sl_prices = [df_1h['low'].iloc[i] for i in swing_lows[-3:]]
                if len(sh_prices) >= 2 and sh_prices[-1] > sh_prices[-2] and \
                   len(sl_prices) >= 2 and sl_prices[-1] > sl_prices[-2]:
                    swings = min(len(swing_highs), len(swing_lows))
                    score = 1.0 if swings >= 4 else (0.80 if swings >= 2 else 0.0)
                    return TrendEnum.UP, score
                if len(sh_prices) >= 2 and sh_prices[-1] < sh_prices[-2] and \
                   len(sl_prices) >= 2 and sl_prices[-1] < sl_prices[-2]:
                    swings = min(len(swing_highs), len(swing_lows))
                    score = 1.0 if swings >= 4 else (0.80 if swings >= 2 else 0.0)
                    return TrendEnum.DOWN, score
                return TrendEnum.NEUTRAL, 0.0

            trend_1h, score_1h = classify(sh_1h, sl_1h)
            trend_4h, score_4h = classify(sh_4h, sl_4h)

            logger.info(f"[TREND] 1H: {trend_1h} ({len(sh_1h)} SH, {len(sl_1h)} SL) | "
                       f"4H: {trend_4h} ({len(sh_4h)} SH, {len(sl_4h)} SL)")

            if trend_1h == trend_4h and trend_1h != TrendEnum.NEUTRAL:
                confidence = max(score_1h, score_4h)
                logger.info(f"[TREND] Both agree → {trend_1h} (confidence: {confidence:.2f})")
                return trend_1h, confidence

            best_trend = TrendEnum.NEUTRAL
            best_score = 0.0
            if score_1h > 0.4 and trend_1h != TrendEnum.NEUTRAL:
                best_trend, best_score = trend_1h, score_1h * 0.75
            if score_4h > best_score and score_4h > 0.4 and trend_4h != TrendEnum.NEUTRAL:
                best_trend, best_score = trend_4h, score_4h * 0.75

            if best_trend != TrendEnum.NEUTRAL:
                logger.info(f"[TREND] Single TF fallback → {best_trend} ({best_score:.2f})")
                return best_trend, best_score

            logger.info("[TREND] No clear structure on 1H/4H → NEUTRAL")
            return TrendEnum.NEUTRAL, 0.0

        except Exception as e:
            logger.error(f"Error in trend analysis: {e}")
            return TrendEnum.NEUTRAL, 0.0

    # ─── S/R Level Identification ────────────────────────────────────────────

    async def _find_levels(self, df_15m: pd.DataFrame, current_price: float) -> Tuple[Optional[float], Optional[float]]:
        try:
            swing_highs = self._find_swing_highs(df_15m, n=LEVELS_LOOKBACK)
            swing_lows = self._find_swing_lows(df_15m, n=LEVELS_LOOKBACK)

            if len(swing_highs) < 2 or len(swing_lows) < 2:
                logger.info("[LEVELS] Insufficient swing points for S/R")
                return None, None

            high_prices = sorted([df_15m['high'].iloc[i] for i in swing_highs])
            low_prices = sorted([df_15m['low'].iloc[i] for i in swing_lows])

            cluster_threshold = current_price * 0.0015

            def cluster(prices: List[float]) -> List[float]:
                if not prices:
                    return []
                clustered = []
                group = [prices[0]]
                for p in prices[1:]:
                    if abs(p - group[-1]) <= cluster_threshold:
                        group.append(p)
                    else:
                        clustered.append(round(sum(group) / len(group), 2))
                        group = [p]
                clustered.append(round(sum(group) / len(group), 2))
                return clustered

            clustered_highs = cluster(high_prices)
            clustered_lows = cluster(low_prices)

            resistance_candidates = [h for h in clustered_highs if h > current_price]
            support_candidates = [l for l in clustered_lows if l < current_price]

            if not resistance_candidates or not support_candidates:
                logger.info("[LEVELS] No valid levels above/below current price")
                return None, None

            resistance = min(resistance_candidates)
            support = max(support_candidates)

            level_range = resistance - support
            min_range = current_price * 0.003

            if level_range < min_range:
                logger.info(f"[LEVELS] Range ${level_range:.2f} too tight (min ${min_range:.2f})")
                return None, None

            logger.info(f"[LEVELS] Support: {support} | Resistance: {resistance} | Range: ${level_range:.2f}")
            return support, resistance

        except Exception as e:
            logger.error(f"Error finding levels: {e}")
            return None, None

    # ─── Mr. PFX Component Scoring ──────────────────────────────────────────

    async def _score_mrpfx_components(
        self, df_15m: pd.DataFrame, df_1h: pd.DataFrame,
        trend: TrendEnum, support: float, resistance: float
    ) -> Dict[str, float]:
        scores = {}
        current_price = df_15m['close'].iloc[-1]
        atr_15m = self._calculate_atr(df_15m, 10)

        # Component 1: Levels of Rejection
        rejection_score = 0.0
        last_5 = df_15m.tail(5)
        for _, candle in last_5.iterrows():
            if trend == TrendEnum.UP:
                low = candle['low']
                if low <= support:
                    body_top = max(candle['open'], candle['close'])
                    if body_top > support:
                        rejection_score = max(rejection_score, 1.0)
                    elif abs(low - support) <= current_price * 0.002:
                        rejection_score = max(rejection_score, 0.5)
                    else:
                        rejection_score = max(rejection_score, 0.0)
            else:
                high = candle['high']
                if high >= resistance:
                    body_bottom = min(candle['open'], candle['close'])
                    if body_bottom < resistance:
                        rejection_score = max(rejection_score, 1.0)
                    elif abs(high - resistance) <= current_price * 0.002:
                        rejection_score = max(rejection_score, 0.5)
                    else:
                        rejection_score = max(rejection_score, 0.0)
        scores['rejection'] = rejection_score

        # Component 2: Internal Regions (consolidation)
        consol_score = 0.0
        atr_threshold = atr_15m * 0.4
        consol_count = 0
        for _, candle in df_15m.tail(10).iterrows():
            if (candle['high'] - candle['low']) < atr_threshold:
                consol_count += 1
            else:
                if consol_count >= 3:
                    break
                consol_count = 0
        if consol_count >= 3:
            consol_score = 1.0
        elif consol_count >= 2:
            consol_score = 0.5
        scores['internal_region'] = consol_score

        # Component 3: Build-up of Structure
        structure_score = 0.0
        sh_1h = self._find_swing_highs(df_1h)
        sl_1h = self._find_swing_lows(df_1h)
        if trend == TrendEnum.UP:
            ascending = sum(1 for i in range(1, len(sh_1h)) if df_1h['high'].iloc[sh_1h[i]] > df_1h['high'].iloc[sh_1h[i-1]])
            if ascending >= 3:
                structure_score = 1.0
            elif ascending >= 2:
                structure_score = 0.5
        else:
            descending = sum(1 for i in range(1, len(sh_1h)) if df_1h['high'].iloc[sh_1h[i]] < df_1h['high'].iloc[sh_1h[i-1]])
            if descending >= 3:
                structure_score = 1.0
            elif descending >= 2:
                structure_score = 0.5
        scores['structure'] = structure_score

        # Component 4: S/R with Directional Bias
        bias_ratio = (current_price - support) / (resistance - support) if (resistance - support) > 0 else 0.5
        if trend == TrendEnum.UP:
            if bias_ratio < 0.35:
                sr_bias_score = 1.0
            elif bias_ratio < 0.5:
                sr_bias_score = 0.5
            else:
                sr_bias_score = 0.0
        else:
            if bias_ratio > 0.65:
                sr_bias_score = 1.0
            elif bias_ratio > 0.5:
                sr_bias_score = 0.5
            else:
                sr_bias_score = 0.0
        scores['sr_bias'] = sr_bias_score

        # Component 5: Standard Breakout
        breakout_score = 0.0
        all_sh = sorted(self._find_swing_highs(df_15m))
        all_sl = sorted(self._find_swing_lows(df_15m))
        for _, candle in df_15m.tail(5).iterrows():
            close = candle['close']
            for idx in all_sh:
                level = df_15m['high'].iloc[idx]
                if close > level:
                    for _, later in df_15m.tail(3).iterrows():
                        if abs(later['close'] - level) <= current_price * 0.002:
                            breakout_score = max(breakout_score, 1.0)
                            break
                    else:
                        breakout_score = max(breakout_score, 0.5)
            for idx in all_sl:
                level = df_15m['low'].iloc[idx]
                if close < level:
                    for _, later in df_15m.tail(3).iterrows():
                        if abs(later['close'] - level) <= current_price * 0.002:
                            breakout_score = max(breakout_score, 1.0)
                            break
                    else:
                        breakout_score = max(breakout_score, 0.5)
        scores['breakout'] = breakout_score

        # Component 6: BOB Confirmation
        bob_score = 0.0
        avg_body = abs(df_15m['close'] - df_15m['open']).tail(10).mean()
        threshold_body = avg_body * 1.5
        significant_candles = []
        for i, (_, candle) in enumerate(df_15m.tail(20).iterrows()):
            body = abs(candle['close'] - candle['open'])
            if body > threshold_body:
                significant_candles.append(i)
        for idx in significant_candles:
            if idx + 1 < len(df_15m):
                sig_candle = df_15m.iloc[idx]
                next_candle = df_15m.iloc[idx + 1]
                block_high = max(sig_candle['open'], sig_candle['close'])
                block_low = min(sig_candle['open'], sig_candle['close'])
                if trend == TrendEnum.UP and next_candle['close'] > block_high:
                    bob_score = 1.0
                    break
                elif trend == TrendEnum.DOWN and next_candle['close'] < block_low:
                    bob_score = 1.0
                    break
        if bob_score == 0.0 and significant_candles:
            bob_score = 0.5
        scores['bob'] = bob_score

        return scores

    def _calculate_weighted_score(self, scores: Dict[str, float]) -> float:
        return sum(scores[comp] * WEIGHTS[i] for i, comp in enumerate(COMPONENTS))

    # ─── Pullback Detection ──────────────────────────────────────────────────

    async def _detect_pullback(
        self, df_5m: pd.DataFrame, support: float, resistance: float, trend: TrendEnum
    ) -> Tuple[bool, float]:
        try:
            current_price = df_5m['close'].iloc[-1]
            atr_5m = self._calculate_atr(df_5m, 14)
            pullback_zone = atr_5m * 1.5

            if trend == TrendEnum.UP:
                if support < current_price <= support + pullback_zone:
                    logger.info(f"[PULLBACK] ATR-14(5M): ${atr_5m:.2f} | Zone: ${pullback_zone:.2f} | "
                               f"Price: {current_price:.2f} | Dist to support: ${current_price - support:.2f} ✓")
                    return True, atr_5m
                elif current_price <= support:
                    logger.info(f"[PULLBACK] Price {current_price:.2f} below support {support:.2f} — breakdown, not pullback")
                    return False, atr_5m
                else:
                    logger.info(f"[PULLBACK] Price {current_price:.2f} above pullback zone (support+zone=${support + pullback_zone:.2f})")
                    return False, atr_5m

            else:
                if resistance - pullback_zone <= current_price < resistance:
                    logger.info(f"[PULLBACK] ATR-14(5M): ${atr_5m:.2f} | Zone: ${pullback_zone:.2f} | "
                               f"Price: {current_price:.2f} | Dist to resistance: ${resistance - current_price:.2f} ✓")
                    return True, atr_5m
                elif current_price >= resistance:
                    logger.info(f"[PULLBACK] Price {current_price:.2f} above resistance {resistance:.2f} — breakout, not pullback")
                    return False, atr_5m
                else:
                    logger.info(f"[PULLBACK] Price {current_price:.2f} below pullback zone (resistance-zone=${resistance - pullback_zone:.2f})")
                    return False, atr_5m

        except Exception as e:
            logger.error(f"Error detecting pullback: {e}")
            return False, 0.0

    # ─── Entry Confirmation ──────────────────────────────────────────────────

    async def _confirm_entry(
        self, df_1m: pd.DataFrame, support: float, resistance: float, trend: TrendEnum, atr_5m: float
    ) -> Tuple[Optional[float], bool]:
        try:
            if len(df_1m) < 5:
                return None, False

            current_candle = df_1m.iloc[-1]
            entry_price = round(current_candle['close'], 2)

            # Primary: Reversal candle
            pattern = self._detect_reversal_candle(df_1m, trend)
            if pattern:
                logger.info(f"[ENTRY] Pattern: {pattern} | Entry: {entry_price} ✓")
                return entry_price, True

            # Secondary: Structure break on 1M
            sh_1m = self._find_swing_highs(df_1m, n=1)
            sl_1m = self._find_swing_lows(df_1m, n=1)
            if trend == TrendEnum.UP and len(sl_1m) >= 1:
                last_swing_low = df_1m['low'].iloc[sl_1m[-1]]
                if current_candle['close'] > last_swing_low and \
                   any(df_1m['close'].iloc[i] > last_swing_low for i in range(-4, -1)):
                    logger.info(f"[ENTRY] Structure break UP — broke swing low {last_swing_low:.2f} | Entry: {entry_price} ✓")
                    return entry_price, True
            elif trend == TrendEnum.DOWN and len(sh_1m) >= 1:
                last_swing_high = df_1m['high'].iloc[sh_1m[-1]]
                if current_candle['close'] < last_swing_high and \
                   any(df_1m['close'].iloc[i] < last_swing_high for i in range(-4, -1)):
                    logger.info(f"[ENTRY] Structure break DOWN — broke swing high {last_swing_high:.2f} | Entry: {entry_price} ✓")
                    return entry_price, True

            # Tertiary: Momentum confirmation
            atr_1m = self._calculate_atr(df_1m, 14)
            min_body = atr_1m * 0.3
            last_3 = df_1m.tail(3)
            if trend == TrendEnum.UP:
                if all(last_3['close'].iloc[i] > last_3['close'].iloc[i-1] for i in range(1, 3)):
                    if all(abs(c['close'] - c['open']) >= min_body for _, c in last_3.iterrows()):
                        logger.info(f"[ENTRY] Momentum UP — 3 rising closes | Entry: {entry_price} ✓")
                        return entry_price, True
            else:
                if all(last_3['close'].iloc[i] < last_3['close'].iloc[i-1] for i in range(1, 3)):
                    if all(abs(c['close'] - c['open']) >= min_body for _, c in last_3.iterrows()):
                        logger.info(f"[ENTRY] Momentum DOWN — 3 falling closes | Entry: {entry_price} ✓")
                        return entry_price, True

            logger.info("[ENTRY] No confirmation pattern found on 1M ✗")
            return None, False

        except Exception as e:
            logger.error(f"Error confirming entry: {e}")
            return None, False

    def _detect_reversal_candle(self, df: pd.DataFrame, trend: TrendEnum) -> Optional[str]:
        if len(df) < 3:
            return None

        current = df.iloc[-1]
        prev = df.iloc[-2]
        body = abs(current['close'] - current['open'])
        total_range = current['high'] - current['low']

        if total_range == 0:
            return None

        atr = self._calculate_atr(df, 10)
        min_body = atr * 0.5

        # Pin bar
        body_ratio = body / total_range
        if body_ratio < 0.25:
            upper_wick = current['high'] - max(current['open'], current['close'])
            lower_wick = min(current['open'], current['close']) - current['low']
            if trend == TrendEnum.UP and lower_wick > total_range * 0.6:
                return 'bullish_pin_bar'
            elif trend == TrendEnum.DOWN and upper_wick > total_range * 0.6:
                return 'bearish_pin_bar'
            elif lower_wick > total_range * 0.6 and upper_wick > total_range * 0.6:
                return 'doji'

        # Engulfing
        prev_body = abs(prev['close'] - prev['open'])
        if prev_body >= min_body and body >= min_body:
            if trend == TrendEnum.UP:
                if current['close'] > prev['open'] and current['open'] < prev['close'] and \
                   current['close'] > prev['high']:
                    return 'bullish_engulfing'
            else:
                if current['close'] < prev['open'] and current['open'] > prev['close'] and \
                   current['close'] < prev['low']:
                    return 'bearish_engulfing'

        # Morning/Evening star (3-candle pattern)
        if len(df) >= 3:
            c1 = df.iloc[-3]
            c2 = df.iloc[-2]
            c3 = current
            if trend == TrendEnum.UP:
                if c1['close'] < c1['open'] and abs(c3['close'] - c3['open']) >= min_body and \
                   c3['close'] > c1['close'] and abs(c2['close'] - c2['open']) < atr * 0.3:
                    return 'morning_star'
            else:
                if c1['close'] > c1['open'] and abs(c3['close'] - c3['open']) >= min_body and \
                   c3['close'] < c1['close'] and abs(c2['close'] - c2['open']) < atr * 0.3:
                    return 'evening_star'

        return None

    # ─── Signal Building ─────────────────────────────────────────────────────

    def _build_signal(
        self, trend: TrendEnum, entry_price: float,
        support: float, resistance: float,
        atr_5m: float, confidence: float
    ) -> Signal:
        s_range = abs(resistance - support)
        entry_spacing = max(round(atr_5m * 2, 1), 5.0)

        entries = []

        if trend == TrendEnum.UP:
            tp1 = round((entry_price + resistance) / 2, 2)
            tp2 = round(resistance, 2)
            tp3 = round(resistance + s_range * 0.5, 2)
            tp4 = round(resistance + s_range, 2)

            offsets = [0, -entry_spacing, -(entry_spacing * 2), -(entry_spacing * 3)]
            tps = [tp1, tp2, tp3, tp4]
            auto_closes = [True, False, False, False]
        else:
            tp1 = round((entry_price + support) / 2, 2)
            tp2 = round(support, 2)
            tp3 = round(support - s_range * 0.5, 2)
            tp4 = round(support - s_range, 2)

            offsets = [0, entry_spacing, entry_spacing * 2, entry_spacing * 3]
            tps = [tp1, tp2, tp3, tp4]
            auto_closes = [True, False, False, False]

        for idx in range(4):
            price = round(entry_price + offsets[idx], 2)
            tp = tps[idx]
            tp_pips = int(abs(tp - price) / PIP_VALUE)

            entries.append(SignalEntry(
                entry_number=idx + 1,
                price=price,
                tp=tp,
                tp_pips=tp_pips,
                auto_close=auto_closes[idx],
            ))

        # Calculate stop loss
        if trend == TrendEnum.UP:
            sl_price = round(support - atr_5m * 0.5, 2)
        else:
            sl_price = round(resistance + atr_5m * 0.5, 2)

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
            confidence=round(confidence, 2),
        )

        logger.info(f"[SIGNAL] ID: {signal_id} | Entries: {[e.price for e in entries]} | "
                   f"TPs: {[e.tp for e in entries]} | SL: ~{sl_price} | Confidence: {confidence:.2f}")

        return signal

    # ─── Main Entry Point ────────────────────────────────────────────────────

    async def generate_signal(self) -> Tuple[Optional[Signal], str]:
        try:
            candles_1h = await self.tv_client.get_candles('1h', 20)
            candles_4h = await self.tv_client.get_candles('4h', 15)
            candles_15m = await self.tv_client.get_candles('15m', 60)
            candles_5m = await self.tv_client.get_candles('5m', 30)
            candles_1m = await self.tv_client.get_candles('1m', 20)

            if not all([candles_1h, candles_4h, candles_15m, candles_5m, candles_1m]):
                return None, "Failed to fetch market data for one or more timeframes."

            df_1h = pd.DataFrame([c.model_dump() for c in candles_1h])
            df_4h = pd.DataFrame([c.model_dump() for c in candles_4h])
            df_15m = pd.DataFrame([c.model_dump() for c in candles_15m])
            df_5m = pd.DataFrame([c.model_dump() for c in candles_5m])
            df_1m = pd.DataFrame([c.model_dump() for c in candles_1m])

            current_price = df_1m['close'].iloc[-1]

            # Stage 1 — Trend
            trend, trend_confidence = await self._analyze_trend(df_1h, df_4h)
            if trend == TrendEnum.NEUTRAL:
                return None, "No clear market structure on 1H/4H. No signal."

            # Stage 2 — S/R Levels
            support, resistance = await self._find_levels(df_15m, current_price)
            if not support or not resistance:
                return None, "No valid S/R levels found on 15M. No signal."

            # Stage 3 — Mr. PFX Scoring
            component_scores = await self._score_mrpfx_components(df_15m, df_1h, trend, support, resistance)
            weighted_score = self._calculate_weighted_score(component_scores)
            score_str = " | ".join(f"{k}={v:.2f}" for k, v in component_scores.items())
            logger.info(f"[MRPFX] {score_str}")
            logger.info(f"[MRPFX] Weighted score: {weighted_score:.2f} (threshold: {SIGNAL_THRESHOLD}) {'✓' if weighted_score >= SIGNAL_THRESHOLD else '✗'}")
            if weighted_score < SIGNAL_THRESHOLD:
                return None, f"Mr. PFX score {weighted_score:.2f} below threshold ({SIGNAL_THRESHOLD}). No signal."

            # Stage 4 — Pullback
            pullback_detected, atr_5m = await self._detect_pullback(df_5m, support, resistance, trend)
            if not pullback_detected:
                return None, "No valid pullback to key level on 5M. No signal."

            # Stage 5 — Entry Confirmation
            entry_price, entry_confirmed = await self._confirm_entry(df_1m, support, resistance, trend, atr_5m)
            if not entry_confirmed:
                return None, "No entry confirmation pattern on 1M. No signal."

            signal = self._build_signal(
                trend=trend,
                entry_price=entry_price,
                support=support,
                resistance=resistance,
                atr_5m=atr_5m,
                confidence=weighted_score,
            )

            logger.info(f"[SIGNAL] Generated: {signal.id} | Confidence: {weighted_score:.2f}")
            return signal, "Signal generated successfully."

        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None, f"Error: {e}"
