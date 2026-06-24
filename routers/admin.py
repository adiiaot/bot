from fastapi import APIRouter
from firestore.client import firestore_client
from app.firebase_manager import FirebaseManager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Admin"],
    prefix="/api/admin"
)

db = FirebaseManager()

SAMPLE_SIGNAL = {
    "id": "signal_init_placeholder",
    "timestamp": None,
    "trend": "UP",
    "entries": [
        {"price": 2040.50, "tp": 2043.20, "tp_pips": 20, "auto_close": True},
        {"price": 2038.10, "tp": 2041.80, "tp_pips": 40, "auto_close": False},
        {"price": 2035.70, "tp": 2039.50, "tp_pips": 60, "auto_close": False},
        {"price": 2033.30, "tp": 2037.10, "tp_pips": 80, "auto_close": False},
    ],
    "support_level": 2033.30,
    "resistance_level": 2043.20,
    "pullback_detected": True,
    "entry_confirmation": True,
    "valid_until": None,
    "confidence": 0.75,
    "executed": False,
}

SAMPLE_TRADE = {
    "entry_price": 2040.50,
    "exit_price": 2043.20,
    "quantity": 0.01,
    "pnl": 2.70,
    "pnl_percent": 0.13,
    "result": "win",
    "status": "closed",
    "hold_time_seconds": 180,
}


@router.post("/init-firestore")
async def init_firestore():
    """Initialize Firestore with required collections and sample documents.

    Creates the collections needed by the project:
    - signals, trades, journal, analytics, econCalendar, bot_logs

    Each collection gets one sample document so they appear in the Firebase console.
    Safe to call multiple times — uses 'init_placeholder' IDs.
    """
    try:
        if not db._ensure_initialized():
            return {"success": False, "message": "Firebase not configured"}

        results = {}

        collections = {
            "signals": SAMPLE_SIGNAL,
            "trades": SAMPLE_TRADE,
            "journal": {"notes": "Sample journal entry", "source": "dashboard", "sentiment": "neutral"},
            "analytics": {"total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0, "total_pnl": 0},
            "econCalendar": {"event": "Sample event", "impact": "low", "goldRelated": True},
            "bot_logs": {"command": "/help", "status": "success", "timestamp": None},
        }

        for coll_name, sample in collections.items():
            try:
                doc_id = f"init_placeholder_{coll_name}"
                db.db.collection(coll_name).document(doc_id).set(sample)
                results[coll_name] = "created"
            except Exception as e:
                results[coll_name] = f"error: {str(e)}"

        return {
            "success": True,
            "message": "Firestore initialized with sample documents",
            "collections": results,
            "next_steps": [
                "1. Go to Firebase Console → Firestore → Indexes",
                "2. Create composite indexes for: signals (userId, timestamp DESC), trades (userId, timestamp DESC)",
                "3. Update Firestore security rules from documentation",
                "4. Run the Telegram bot and test /signal command",
            ],
        }
    except Exception as e:
        logger.error(f"Firestore init error: {str(e)}")
        return {"success": False, "message": str(e)}
