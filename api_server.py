"""Legacy entrypoint that reuses the unified FastAPI application."""

from __future__ import annotations

from dotenv import load_dotenv

from backend.api.stock_external import (
    BulkStockUpdate,
    BulkUpdateResponse,
    MovementType,
    ProductDetail,
    ProductSummary,
    StockMovement,
    StockUpdate,
    StockUpdateResult,
    router as stock_external_router,
)
from backend.main import create_app

load_dotenv()

app = create_app()

__all__ = [
    "app",
    "BulkStockUpdate",
    "BulkUpdateResponse",
    "MovementType",
    "ProductDetail",
    "ProductSummary",
    "StockMovement",
    "StockUpdate",
    "StockUpdateResult",
    "stock_external_router",
]
