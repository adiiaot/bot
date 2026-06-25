from firestore.client import firestore_client
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class JournalDB:
    def __init__(self):
        self.db = firestore_client.get_db()
        self.collection_name = 'journal'

    async def save_journal_entry(self, user_id: str, entry_id: str, notes: str,
                                related_trade_id: str = None) -> bool:
        try:
            journal_doc = {
                'userId': user_id,
                'timestamp': datetime.utcnow(),
                'source': 'telegram',
                'notes': notes,
                'sentiment': 'neutral',
                'analysis': {
                    'theme': '',
                    'actionItems': [],
                    'relatedSignals': [],
                }
            }
            if related_trade_id:
                journal_doc['relatedTradeId'] = related_trade_id
            self.db.collection(self.collection_name).document(entry_id).set(journal_doc)
            logger.info(f"Journal entry {entry_id} saved")
            return True
        except Exception as e:
            logger.error(f"Error saving journal: {str(e)}")
            return False

    async def get_user_journal(self, user_id: str, limit: int = 20) -> list:
        try:
            from firebase_admin import firestore as fs
            query = (self.db.collection(self.collection_name)
                     .where(filter=('userId', '==', user_id))
                     .order_by('timestamp', direction=fs.Query.DESCENDING)
                     .limit(limit))
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error fetching journal: {str(e)}")
            return []


journal_db = JournalDB()
