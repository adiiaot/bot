import base64
import hashlib
import json
import logging
from typing import Optional, Dict
import httpx
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)


class NvidiaVisionAnalyzer:
    """Analyse XAU/USD chart screenshots using the Nvidia NIM Llama 3.2 Vision model.

    Caches results in-memory by MD5 hash with a configurable TTL to reduce
    redundant API calls for identical screenshots.
    """

    def __init__(self):
        self.api_url = Config.NVIDIA_NIM_API_URL
        self.api_key = Config.NVIDIA_NIM_API_KEY
        self.model = Config.NVIDIA_MODEL_VISION
        self.cache = {}
        self.cache_ttl = Config.SCREENSHOT_CACHE_MINUTES * 60

    async def analyze_screenshot(self, image_base64: str) -> Dict:
        """Send a base64-encoded screenshot to Nvidia Vision API and return parsed analysis.

        Args:
            image_base64: PNG chart screenshot encoded as base64 string.

        Returns:
            Dict with keys: current_price, support_levels, resistance_levels,
            trend, pattern, rsi, volume_trend, observations, confidence, timestamp.
        """
        cache_key = self._generate_cache_key(image_base64)
        if cache_key in self.cache:
            cached_result, cached_time = self.cache[cache_key]
            if (datetime.utcnow() - cached_time).total_seconds() < self.cache_ttl:
                logger.debug(f"Using cached vision analysis for {cache_key}")
                return cached_result

        try:
            prompt = """Analyze this XAU/USD (Gold) trading chart screenshot and extract the following technical data in JSON format:

{
    "current_price": <current price as float>,
    "support_levels": [<list of support levels as floats>],
    "resistance_levels": [<list of resistance levels as floats>],
    "trend": "<UP or DOWN or NEUTRAL>",
    "pattern": "<identified candlestick pattern like 'pin bar', 'engulfing', 'consolidation', 'breakout'>",
    "rsi": <RSI value 0-100 if visible, otherwise null>,
    "volume_trend": "<increasing or decreasing or stable>",
    "observations": [
        "<observation 1>",
        "<observation 2>",
        "<observation 3>"
    ],
    "confidence": <confidence score 0-1 based on clarity of chart>
}

Focus on:
- Recent swing highs (resistance)
- Recent swing lows (support)
- Current price position relative to levels
- Trend direction (higher highs/lows or lower highs/lows)
- Any visible patterns
- Volume changes

Be precise with price levels. Return ONLY valid JSON, no other text."""

            logger.info("Sending chart to Nvidia Vision Model for analysis")

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{image_base64}"
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": prompt
                                    }
                                ]
                            }
                        ],
                        "temperature": 0.3,
                        "top_p": 0.7,
                        "max_tokens": 500
                    }
                )

            if response.status_code == 200:
                data = response.json()
                analysis_text = data['choices'][0]['message']['content']

                analysis = json.loads(analysis_text)
                analysis['timestamp'] = datetime.utcnow().isoformat()

                self.cache[cache_key] = (analysis, datetime.utcnow())

                logger.info(f"Vision analysis complete. Confidence: {analysis.get('confidence', 0)}")
                return analysis
            else:
                logger.error(f"Nvidia Vision API error: {response.status_code}")
                return self._fallback_response()

        except Exception as e:
            logger.error(f"Error analyzing screenshot: {str(e)}")
            return self._fallback_response()

    def _generate_cache_key(self, image_base64: str) -> str:
        """Generate an MD5 hash of the image for cache keying."""
        return hashlib.md5(image_base64.encode()).hexdigest()

    def _fallback_response(self) -> Dict:
        """Return a neutral analysis response when API calls fail."""
        return {
            'current_price': None,
            'support_levels': [],
            'resistance_levels': [],
            'trend': 'NEUTRAL',
            'pattern': 'unknown',
            'rsi': None,
            'volume_trend': 'stable',
            'observations': ['Unable to analyze screenshot'],
            'confidence': 0,
            'timestamp': datetime.utcnow().isoformat()
        }

    def clear_cache(self):
        """Evict expired cache entries based on configured TTL."""
        now = datetime.utcnow()
        expired = [
            k for k, (_, t) in self.cache.items()
            if (now - t).total_seconds() > self.cache_ttl
        ]
        for k in expired:
            del self.cache[k]
        logger.debug(f"Cleared {len(expired)} expired cache entries")
