import firebase_admin
from firebase_admin import credentials, firestore
import os
import logging

logger = logging.getLogger(__name__)


class FirestoreClient:
    _instance = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._db is None:
            try:
                cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', './firebase-credentials.json')
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                else:
                    cred = credentials.Certificate({
                        'type': 'service_account',
                        'project_id': os.getenv('FIREBASE_PROJECT_ID'),
                        'private_key': os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
                        'client_email': os.getenv('FIREBASE_CLIENT_EMAIL'),
                    })
                firebase_admin.initialize_app(cred, {
                    'projectId': os.getenv('FIREBASE_PROJECT_ID'),
                })
                self._db = firestore.client()
                logger.info(f"Firestore initialized. Project: {os.getenv('FIREBASE_PROJECT_ID')}")
            except Exception as e:
                logger.error(f"Failed to initialize Firestore: {str(e)}")
                raise

    def get_db(self):
        return self._db


firestore_client = FirestoreClient()
