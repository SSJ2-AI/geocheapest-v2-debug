"""
Firestore database connection for GeoCheapest v2
"""
import logging
import os
from typing import Optional
from google.cloud import firestore

logger = logging.getLogger(__name__)

_db_client: Optional[firestore.Client] = None


def _create_client() -> firestore.AsyncClient:
    project_id = os.getenv("GCP_PROJECT_ID")
    return firestore.AsyncClient(project=project_id or None)


_mock_db_data = {} # Global storage for the mock DB

class MockCollection:
    def __init__(self, name):
        self.name = name
        if name not in _mock_db_data:
            _mock_db_data[name] = {}
        self.filters = []
        self.limit_val = None
        self.offset_val = 0

    def document(self, doc_id=None):
        if not doc_id:
            import uuid
            doc_id = str(uuid.uuid4())
        return MockDocument(self.name, doc_id)

    def where(self, field, op, value):
        self.filters.append((field, op, value))
        return self

    def limit(self, n):
        self.limit_val = n
        return self

    def offset(self, n):
        self.offset_val = n
        return self

    def stream(self):
        return self

    async def __aiter__(self):
        for doc in self._get_docs():
            yield doc

    def _get_docs(self):
        docs = []
        if self.name not in _mock_db_data:
            return []
            
        for doc_id, data in _mock_db_data[self.name].items():
            match = True
            for field, op, value in self.filters:
                if op == "==":
                    if data.get(field) != value:
                        match = False
                        break
                elif op == ">=":
                    if not (data.get(field) and data.get(field) >= value):
                        match = False
                        break
                elif op == "<=":
                    if not (data.get(field) and data.get(field) <= value):
                        match = False
                        break
            if match:
                docs.append(MockSnapshot(True, doc_id, data, self.name))
        
        if hasattr(self, 'offset_val') and self.offset_val:
            docs = docs[self.offset_val:]
            
        if self.limit_val:
            docs = docs[:self.limit_val]
        return docs
        
    # For sync iteration support (if any)
    def __iter__(self):
        return iter(self._get_docs())

class MockDocument:
    def __init__(self, col_name, doc_id):
        self.col_name = col_name
        self.id = doc_id
        self.reference = self

    async def set(self, data):
        logger.info(f"MOCK DB: Set {self.col_name}/{self.id}")
        if self.col_name not in _mock_db_data:
            _mock_db_data[self.col_name] = {}
        _mock_db_data[self.col_name][self.id] = data

    async def update(self, data):
        logger.info(f"MOCK DB: Update {self.col_name}/{self.id}")
        if self.col_name not in _mock_db_data:
            _mock_db_data[self.col_name] = {}
        if self.id not in _mock_db_data[self.col_name]:
             _mock_db_data[self.col_name][self.id] = {}
        _mock_db_data[self.col_name][self.id].update(data)

    async def get(self):
        exists = False
        data = {}
        if self.col_name in _mock_db_data and self.id in _mock_db_data[self.col_name]:
            exists = True
            data = _mock_db_data[self.col_name][self.id]
        return MockSnapshot(exists, self.id, data, self.col_name)

class MockSnapshot:
    def __init__(self, exists, doc_id, data, col_name="unknown"):
        self.exists = exists
        self.id = doc_id
        self._data = data
        self.reference = MockDocument(col_name, doc_id)

    def to_dict(self):
        return self._data

class MockFirestoreClient:
    def collection(self, name):
        return MockCollection(name)

class FirestoreProxy:
    """Lazy Firestore client that avoids initialization at import time."""

    def _ensure_client(self) -> firestore.AsyncClient:
        global _db_client
        if _db_client is None:
            try:
                _db_client = _create_client()
                logger.info("Firestore AsyncClient initialized")
            except Exception as exc:
                logger.error(f"Firestore failed: {exc}")
                logger.warning("Using MockFirestoreClient due to connection failure")
                _db_client = MockFirestoreClient()
        
        return _db_client

    def __getattr__(self, name):
        client = self._ensure_client()
        return getattr(client, name)


db = FirestoreProxy()

# Collection names
STORES = "stores"
PRODUCTS = "products"
SHOPIFY_LISTINGS = "shopifyListings"
AFFILIATE_PRODUCTS = "affiliateProducts"
ORDERS = "orders"
ORDER_ITEMS = "orderItems"
SELLER_PAYOUTS = "sellerPayouts"
COMMISSION_RATES = "commissionRates"
VENDOR_COMMISSION_OVERRIDES = "vendorCommissionOverrides"
RETURN_REQUESTS = "returnRequests"
OAUTH_NONCES = "oauth_nonces"
USERS = "users"

