import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables.

    Attributes:
        TELEGRAM_BOT_TOKEN: Bot token for Telegram API authentication.
        TELEGRAM_CHAT_ID: Default chat ID for broadcasting signals.
        TRADINGVIEW_API_KEY: RapidAPI key for TradingView data access.
        TRADINGVIEW_API_HOST: RapidAPI host header value.
        TRADINGVIEW_BASE_URL: Base URL for TradingView API endpoints.
        FIREBASE_PROJECT_ID: Firebase project identifier.
        FIREBASE_PRIVATE_KEY: Firebase service account private key.
        FIREBASE_CLIENT_EMAIL: Firebase service account email.
        FIREBASE_DATABASE_URL: Auto-derived Firestore database URL.
        BOT_ENV: Deployment environment (development/production).
        DEBUG: Enable debug mode and auto-reload.
        LOG_LEVEL: Logging verbosity (DEBUG/INFO/WARNING/ERROR).
        TRADING_PAIR: TradingView symbol for XAU/USD.
        SIGNAL_VALIDITY_HOURS: How long a signal remains valid.
        LOT_SIZE: Default trading lot size (0.01 = micro lot).
        MAX_HOLD_TIME_MINUTES: Maximum position hold time for scalping.
        TRADINGVIEW_REQUESTS_LIMIT: Monthly API request cap.
        TRADINGVIEW_REQUESTS_PER_DAY: Approximate daily limit.
        NVIDIA_MODEL_PROCESSOR: Nvidia model for data processing.
        NVIDIA_MODEL_VISION: Nvidia vision model for chart analysis.
        NVIDIA_MODEL_STRATEGIST: Nvidia model for strategic analysis.
        NVIDIA_NIM_API_URL: Base URL for Nvidia NIM API.
        NVIDIA_NIM_API_KEY: API key for Nvidia NIM.
        MAX_SCREENSHOT_SIZE_MB: Max uploaded screenshot file size.
        SCREENSHOT_CACHE_MINUTES: TTL for screenshot analysis cache.
        VERIFICATION_THRESHOLD_SCORE: Minimum score for signal verification.
        CONFIDENCE_BOOST_HIGH: Confidence boost for high alignment.
        CONFIDENCE_BOOST_MEDIUM: Confidence boost for medium alignment.
        CONFIDENCE_PENALTY: Confidence penalty for low alignment.
    """
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    TRADINGVIEW_API_KEY = os.getenv('TRADINGVIEW_API_KEY')
    TRADINGVIEW_API_HOST = os.getenv('TRADINGVIEW_API_HOST')
    TRADINGVIEW_BASE_URL = 'https://tradingview-data1.p.rapidapi.com'

    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
    FIREBASE_PRIVATE_KEY = os.getenv('FIREBASE_PRIVATE_KEY')
    FIREBASE_CLIENT_EMAIL = os.getenv('FIREBASE_CLIENT_EMAIL')
    FIREBASE_DATABASE_URL = f'https://{FIREBASE_PROJECT_ID}.firebaseio.com'

    BOT_ENV = os.getenv('BOT_ENV', 'development')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', './logs')

    TRADING_PAIR = 'FOREXCOM:XAUUSD'
    SIGNAL_VALIDITY_HOURS = 3
    LOT_SIZE = 0.01
    MAX_HOLD_TIME_MINUTES = 5

    TRADINGVIEW_REQUESTS_LIMIT = 150
    TRADINGVIEW_REQUESTS_PER_DAY = 5

    DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'https://analyzer-dashboard-kohl.vercel.app')

    NVIDIA_MODEL_PROCESSOR = os.getenv('NVIDIA_MODEL_PROCESSOR', 'meta/llama-3.1-8b-instruct')
    NVIDIA_MODEL_VISION = os.getenv('NVIDIA_MODEL_VISION', 'meta/llama-3.2-11b-vision-instruct')
    NVIDIA_MODEL_STRATEGIST = os.getenv('NVIDIA_MODEL_STRATEGIST', 'meta/llama-3.3-70b-instruct')
    NVIDIA_NIM_API_URL = os.getenv('NVIDIA_NIM_API_URL', 'https://integrate.api.nvidia.com/v1')
    NVIDIA_NIM_API_KEY = os.getenv('NVIDIA_NIM_API_KEY')

    MAX_SCREENSHOT_SIZE_MB = int(os.getenv('MAX_SCREENSHOT_SIZE_MB', '10'))
    SCREENSHOT_CACHE_MINUTES = int(os.getenv('SCREENSHOT_CACHE_MINUTES', '5'))
    VERIFICATION_THRESHOLD_SCORE = int(os.getenv('VERIFICATION_THRESHOLD_SCORE', '60'))
    CONFIDENCE_BOOST_HIGH = int(os.getenv('CONFIDENCE_BOOST_HIGH', '15'))
    CONFIDENCE_BOOST_MEDIUM = int(os.getenv('CONFIDENCE_BOOST_MEDIUM', '5'))
    CONFIDENCE_PENALTY = int(os.getenv('CONFIDENCE_PENALTY', '10'))
