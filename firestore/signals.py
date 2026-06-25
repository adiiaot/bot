from firestore.client import firestore_client
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SignalsDB:
    def __init__(self):
        self.db = firestore_client.get_db()
        self.collection_name = 'signals'

    async def save_signal(self, user_id: str, signal) -> str:
        try:
            signal_doc = {
                'userId': user_id,
                'timestamp': datetime.utcnow(),
                'trend': signal.trend.value,
                'entries': [
                    {
                        'entryNumber': entry.entry_number,
                        'price': entry.price,
                        'tp': entry.tp,
                        'tpPips': entry.tp_pips,
                        'autoClose': entry.auto_close,
                    }
                    for entry in signal.entries
                ],
                'supportLevel': signal.support_level,
                'resistanceLevel': signal.resistance_level,
                'pullbackDetected': signal.pullback_detected,
                'entryConfirmation': signal.entry_confirmation,
                'validUntil': signal.valid_until,
                'confidence': signal.confidence,
                'status': 'active',
                'deliveredVia': 'telegram',
                'deliveredAt': datetime.utcnow(),
                'acknowledged': False,
            }
            self.db.collection(self.collection_name).document(signal.id).set(signal_doc)
            logger.info(f"Signal {signal.id} saved for user {user_id}")
            return signal.id
        except Exception as e:
            logger.error(f"Error saving signal: {str(e)}")
            raise

    async def get_latest_signals(self, user_id: str, limit: int = 5) -> list:
        try:
            from firebase_admin import firestore as fs
            query = (self.db.collection(self.collection_name)
                     .where(filter=('userId', '==', user_id))
                     .order_by('timestamp', direction=fs.Query.DESCENDING)
                     .limit(limit))
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error fetching signals: {str(e)}")
            return []

    async def update_signal_status(self, signal_id: str, status: str) -> bool:
        try:
            self.db.collection(self.collection_name).document(signal_id).update({
                'status': status,
                'updatedAt': datetime.utcnow(),
            })
            logger.info(f"Signal {signal_id} -> {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating signal: {str(e)}")
            return False


signals_db = SignalsDB()
