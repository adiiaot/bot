from firestore.client import firestore_client
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BotsDB:
    def __init__(self):
        self.db = firestore_client.get_db()
        self.collection_name = 'bot_logs'

    async def log_command(self, user_id: str, command: str, status: str,
                         response: str = None, error: str = None,
                         processing_time_ms: int = None) -> bool:
        try:
            log_doc = {
                'timestamp': datetime.utcnow(),
                'userId': user_id,
                'command': command,
                'status': status,
                'response': response,
                'errorLog': error,
                'processingTimeMs': processing_time_ms,
            }
            self.db.collection(self.collection_name).add(log_doc)
            logger.info(f"[{command}] User {user_id} - Status: {status}")
            return True
        except Exception as e:
            logger.error(f"Error logging command: {str(e)}")
            return False


logs_db = BotsDB()
