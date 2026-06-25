import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import logging
from typing import Optional, List, Dict
from datetime import datetime
from app.models import Signal, TradeLog, ResultEnum
from config import Config

logger = logging.getLogger(__name__)


def _get_service_account_path() -> Optional[str]:
    """Find the Firebase service account JSON file in the project.

    Checks in order:
    1. SERVICE_ACCOUNT_PATH env var (explicit path)
    2. ../aot-analyzer-bot-firebase-adminsdk-fbsvc-*.json (project root)
    3. ./aot-analyzer-bot-firebase-adminsdk-fbsvc-*.json (bot dir)
    """
    explicit = os.getenv('SERVICE_ACCOUNT_PATH')
    if explicit and os.path.exists(explicit):
        return explicit

    search_paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'aot-analyzer-bot-firebase-adminsdk-fbsvc-96f7cb0ea5.json'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'aot-analyzer-bot-firebase-adminsdk-fbsvc-96f7cb0ea5.json'),
    ]
    for p in search_paths:
        normalized = os.path.normpath(p)
        if os.path.exists(normalized):
            return normalized
    return None


class FirebaseManager:
    """Singleton manager for Firestore database operations.

    Handles persistence for signals, trade logs, and aggregated statistics.
    Initialises Firebase Admin SDK lazily on first operation using the
    downloaded service-account JSON file.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseManager, cls).__new__(cls)
        return cls._instance

    def _ensure_initialized(self):
        """Lazy init: connect to Firebase on first use."""
        if self._initialized:
            return True
        try:
            if not firebase_admin._apps:
                service_account_path = _get_service_account_path()
                if service_account_path and os.path.exists(service_account_path):
                    creds = credentials.Certificate(service_account_path)
                    logger.info(f"Using service account: {service_account_path}")
                elif Config.FIREBASE_PROJECT_ID and Config.FIREBASE_PRIVATE_KEY:
                    creds = credentials.Certificate({
                        'project_id': Config.FIREBASE_PROJECT_ID,
                        'private_key': Config.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
                        'client_email': Config.FIREBASE_CLIENT_EMAIL,
                    })
                else:
                    logger.warning("Firebase credentials not configured")
                    return False

                firebase_admin.initialize_app(creds)

            self.db = firestore.client()
            self._initialized = True
            logger.info("Firebase initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Firebase initialization error: {str(e)}")
            return False

    async def save_signal(self, signal: Signal) -> bool:
        if not self._ensure_initialized():
            return False
        try:
            self.db.collection('signals').document(signal.id).set({
                'signalId': signal.id,
                'timestamp': signal.timestamp,
                'trend': signal.trend.value,
                'entries': [
                    {
                        'entryNumber': entry.entry_number,
                        'price': entry.price,
                        'tp': entry.tp,
                        'tpPips': entry.tp_pips,
                        'autoClose': entry.auto_close
                    }
                    for entry in signal.entries
                ],
                'supportLevel': signal.support_level,
                'resistanceLevel': signal.resistance_level,
                'pullbackDetected': signal.pullback_detected,
                'entryConfirmation': signal.entry_confirmation,
                'validUntil': signal.valid_until,
                'confidence': signal.confidence,
                'status': 'active'
            })
            logger.info(f"Signal {signal.id} saved to Firestore")
            return True
        except Exception as e:
            logger.error(f"Error saving signal: {str(e)}")
            return False

    async def get_signal(self, signal_id: str) -> Optional[Dict]:
        if not self._ensure_initialized():
            return None
        try:
            doc = self.db.collection('signals').document(signal_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"Error retrieving signal: {str(e)}")
            return None

    async def log_trade(self, trade: TradeLog, signal_id: Optional[str] = None, direction: str = "LONG") -> Dict:
        if not self._ensure_initialized():
            return {}
        try:
            trade_id = f"trade_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"

            raw_pnl = trade.exit_price - trade.entry_price
            if direction.upper() == "SHORT":
                raw_pnl = -raw_pnl
            pnl = raw_pnl

            pnl_percent = (pnl / trade.entry_price) * 100 if trade.entry_price else 0

            trade_data = {
                'tradeId': trade_id,
                'timestamp': datetime.utcnow(),
                'entryPrice': trade.entry_price,
                'exitPrice': trade.exit_price,
                'entrySize': trade.quantity,
                'pnl': round(pnl, 2),
                'pnlPercent': round(pnl_percent, 2),
                'result': trade.result.value,
                'signalId': signal_id,
                'status': 'closed',
                'trend': 'UP',
                'supportLevel': 0,
                'resistanceLevel': 0,
                'stopLoss': 0,
                'takeProfit': 0,
                'riskRewardRatio': 0,
                'journalNotes': trade.notes or '',
                'tradingConditions': '',
                'holdTimeSeconds': trade.hold_time_seconds
            }

            self.db.collection('trades').document(trade_id).set(trade_data)
            logger.info(f"Trade {trade_id} logged successfully")

            return {
                'id': trade_id,
                'pnl': round(pnl, 2),
                'pnl_percent': round(pnl_percent, 2)
            }
        except Exception as e:
            logger.error(f"Error logging trade: {str(e)}")
            return {}

    async def get_all_trades(self) -> List[Dict]:
        if not self._ensure_initialized():
            return []
        try:
            docs = self.db.collection('trades').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error retrieving trades: {str(e)}")
            return []

    async def calculate_stats(self) -> Dict:
        trades = await self.get_all_trades()

        if not trades:
            return {
                'total_trades': 0, 'wins': 0, 'losses': 0,
                'win_rate': 0.0, 'total_pnl': 0.0, 'profit_factor': 0.0,
                'avg_win': 0.0, 'avg_loss': 0.0,
                'consecutive_wins': 0, 'consecutive_losses': 0
            }

        wins = [t for t in trades if t['result'] == 'win']
        losses = [t for t in trades if t['result'] == 'loss']

        total_pnl = sum(t['pnl'] for t in trades)
        win_pnl = sum(t['pnl'] for t in wins) if wins else 0
        loss_pnl = sum(abs(t['pnl']) for t in losses) if losses else 0
        profit_factor = win_pnl / loss_pnl if loss_pnl > 0 else 0

        consecutive_wins = 0
        consecutive_losses = 0
        current_streak = 0
        streak_type = None

        for t in trades:
            if t['result'] == 'win':
                if streak_type == 'win':
                    current_streak += 1
                else:
                    streak_type = 'win'
                    current_streak = 1
                consecutive_wins = max(consecutive_wins, current_streak)
            elif t['result'] == 'loss':
                if streak_type == 'loss':
                    current_streak += 1
                else:
                    streak_type = 'loss'
                    current_streak = 1
                consecutive_losses = max(consecutive_losses, current_streak)
            else:
                current_streak = 0
                streak_type = None

        return {
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(trades) if trades else 0,
            'total_pnl': round(total_pnl, 2),
            'profit_factor': round(profit_factor, 2),
            'avg_win': round(win_pnl / len(wins), 2) if wins else 0,
            'avg_loss': round(loss_pnl / len(losses), 2) if losses else 0,
            'consecutive_wins': consecutive_wins,
            'consecutive_losses': consecutive_losses
        }
