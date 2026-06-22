from fastapi import APIRouter, HTTPException
from app.signal_generator import SignalGenerator
from app.tradingview_client import TradingViewClient
from app.firebase_manager import FirebaseManager
from app.models import SignalResponse, Signal

router = APIRouter(
    tags=["Signals"],
    prefix="/api"
)

tv_client = TradingViewClient()
signal_gen = SignalGenerator(tv_client)
db = FirebaseManager()


@router.post("/signal", response_model=SignalResponse)
async def generate_signal():
    """Generate a new XAU/USD trading signal from TradingView API data.

    Persists the signal to Firestore before returning.
    """
    signal, message = await signal_gen.generate_signal()

    if signal:
        await db.save_signal(signal)
        return SignalResponse(success=True, signal=signal, message=message)
    else:
        return SignalResponse(success=False, message=message)


@router.get("/signal/{signal_id}")
async def get_signal(signal_id: str):
    """Retrieve a previously generated signal by its ID."""
    signal = await db.get_signal(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal


@router.get("/api-stats")
async def api_stats():
    """Return TradingView API request count and rate limit status."""
    return tv_client.get_request_count()
