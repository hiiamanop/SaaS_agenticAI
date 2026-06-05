# services/inventory-service/app/dependencies.py
from app.database import get_db

__all__ = ["get_db"]
