import logging
from typing import Optional, Dict, Tuple
import httpx
from datetime import datetime
from app.signal_generator import SignalGenerator
from app.services.nvidia_vision_analyzer import NvidiaVisionAnalyzer
from config import Config

logger = logging.getLogger(__name__)


class MultiModelPipeline:
    """Coordinates API-based and vision-based signal generation into a single pipeline.

    Supports two modes:
    - API-only: generates a signal from TradingView data with no visual verification.
    - API + Screenshot: runs both the TV API and Nvidia Vision model, then computes
      an alignment score and adjusts confidence accordingly.
    """

    def __init__(self, signal_generator: SignalGenerator):
        self.signal_gen = signal_generator
        self.vision_analyzer = NvidiaVisionAnalyzer()
        self.api_url = Config.NVIDIA_NIM_API_URL
        self.api_key = Config.NVIDIA_NIM_API_KEY
        self.processor_model = Config.NVIDIA_MODEL_PROCESSOR
        self.strategist_model = Config.NVIDIA_MODEL_STRATEGIST

    async def process_api_only(self, api_data: Dict) -> Dict:
        """Generate a signal using TradingView API data alone (no screenshot)."""

        try:
            signal, message = await self.signal_gen.generate_signal()

            if signal:
                return {
                    'success': True,
                    'signal': signal,
                    'mode': 'api_only',
                    'verification': {
                        'verified': False,
                        'score': 0,
                        'confidence_boost': 0,
                        'data_source': 'TradingView API Only'
                    },
                    'message': message
                }
            else:
                return {
                    'success': False,
                    'mode': 'api_only',
                    'message': message
                }

        except Exception as e:
            logger.error(f"Error in API-only processing: {str(e)}")
            return {
                'success': False,
                'mode': 'api_only',
                'message': f'Error: {str(e)}'
            }

    async def process_with_screenshot(
        self,
        api_data: Dict,
        screenshot_base64: str
    ) -> Dict:
        """Run API signal + vision analysis, then compute an alignment score.

        Returns unified result with verification details, discrepancies, and
        a confidence-adjusted final score. Falls back to API-only on error.
        """

        try:
            api_signal, api_message = await self.signal_gen.generate_signal()
            if not api_signal:
                return {
                    'success': False,
                    'message': f'API analysis failed: {api_message}'
                }

            vision_analysis = await self.vision_analyzer.analyze_screenshot(screenshot_base64)

            verification_score, discrepancies, confidence_boost = self._verify_alignment(
                api_signal=api_signal,
                vision_data=vision_analysis
            )

            final_confidence = api_signal.confidence
            if verification_score >= 80:
                final_confidence += Config.CONFIDENCE_BOOST_HIGH / 100
                confidence_boost_text = f"+{Config.CONFIDENCE_BOOST_HIGH}% (High alignment)"
            elif verification_score >= 60:
                final_confidence += Config.CONFIDENCE_BOOST_MEDIUM / 100
                confidence_boost_text = f"+{Config.CONFIDENCE_BOOST_MEDIUM}% (Medium alignment)"
            elif verification_score < 40:
                final_confidence -= Config.CONFIDENCE_PENALTY / 100
                confidence_boost_text = f"-{Config.CONFIDENCE_PENALTY}% (Low alignment)"
            else:
                confidence_boost_text = "No adjustment"

            final_confidence = min(final_confidence, 1.0)

            logger.info(
                f"Verification complete. Score: {verification_score}/100, "
                f"Confidence: {final_confidence:.2f}"
            )

            return {
                'success': True,
                'signal': api_signal,
                'mode': 'api_with_screenshot',
                'final_confidence': final_confidence,
                'verification': {
                    'verified': True,
                    'score': verification_score,
                    'confidence_boost': confidence_boost_text,
                    'data_source': 'TradingView API + Chart Screenshot',
                    'discrepancies': discrepancies,
                    'vision_confidence': vision_analysis.get('confidence', 0)
                },
                'message': api_message
            }

        except Exception as e:
            logger.error(f"Error in screenshot processing: {str(e)}")
            return await self.process_api_only(api_data)

    def _verify_alignment(
        self,
        api_signal: object,
        vision_data: Dict
    ) -> Tuple[int, list, float]:
        """Compare API signal values against vision-derived data.

        Calculates a penalty-based score (0-100) by checking:
        - Support / resistance level proximity (up to -15 each)
        - Trend direction match (up to -20 or +10)
        - Chart pattern presence (informational only)
        - Screenshot confidence threshold (-20 if < 50%)
        """
        score = 100
        discrepancies = []

        api_support = api_signal.support_level
        vision_support = vision_data.get('support_levels', [])

        if vision_support:
            closest_support = min(
                vision_support,
                key=lambda x: abs(x - api_support)
            )
            diff_pct = abs(closest_support - api_support) / api_support * 100

            if diff_pct > 0.5:
                score -= 15
                discrepancies.append(
                    f"Support mismatch: API={api_support}, Chart={closest_support} ({diff_pct:.2f}%)"
                )

        api_resistance = api_signal.resistance_level
        vision_resistance = vision_data.get('resistance_levels', [])

        if vision_resistance:
            closest_resistance = min(
                vision_resistance,
                key=lambda x: abs(x - api_resistance)
            )
            diff_pct = abs(closest_resistance - api_resistance) / api_resistance * 100

            if diff_pct > 0.5:
                score -= 15
                discrepancies.append(
                    f"Resistance mismatch: API={api_resistance}, Chart={closest_resistance} ({diff_pct:.2f}%)"
                )

        api_trend = api_signal.trend.value
        vision_trend = vision_data.get('trend', 'NEUTRAL')

        if api_trend != vision_trend:
            score -= 20
            discrepancies.append(f"Trend mismatch: API={api_trend}, Chart={vision_trend}")
        else:
            score += 10

        vision_pattern = vision_data.get('pattern', 'unknown')
        if vision_pattern and vision_pattern != 'unknown':
            discrepancies.append(f"Chart pattern detected: {vision_pattern}")

        vision_conf = vision_data.get('confidence', 0)
        if vision_conf < 0.5:
            score -= 20
            discrepancies.append(f"Low screenshot confidence: {vision_conf:.1%}")

        score = max(0, min(100, score))

        logger.debug(f"Verification score: {score}/100, Discrepancies: {len(discrepancies)}")

        return score, discrepancies, 0
