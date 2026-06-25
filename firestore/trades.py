from firestore.client import firestore_client
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TradesDB:
    def __init__(self):
        self.db = firestore_client.get_db()
        self.collection_name = 'trades'

    async def save_trade(self, trade_data: dict) -> str:
        try:
            trade_id = trade_data.get('id') or trade_data.get('tradeId') or f"trade_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            trade_data['timestamp'] = datetime.utcnow()
            self.db.collection(self.collection_name).document(trade_id).set(trade_data)
            logger.info(f"Trade {trade_id} saved")
            return trade_id
        except Exception as e:
            logger.error(f"Error saving trade: {str(e)}")
            raise

    async def get_all_trades(self) -> list:
        try:
            from firebase_admin import firestore as fs
            docs = self.db.collection(self.collection_name).order_by('timestamp', direction=fs.Query.DESCENDING).stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error fetching trades: {str(e)}")
            return []


trades_db = TradesDB()
