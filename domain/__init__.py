"""High-level domain services shared across API and UI clients."""

from .catalogue import (
    InvalidBarcodeError,
    ProductNotFoundError,
    delete_product_by_barcode,
    fetch_products,
    load_active_products_map,
    update_catalog_entry,
)
from .preferences import get_saved_views_service, set_saved_views_service
from .sales import get_sale_service, process_sale_transaction, set_sale_service

__all__ = [
    "InvalidBarcodeError",
    "ProductNotFoundError",
    "delete_product_by_barcode",
    "fetch_products",
    "get_sale_service",
    "get_saved_views_service",
    "load_active_products_map",
    "process_sale_transaction",
    "set_sale_service",
    "set_saved_views_service",
    "update_catalog_entry",
]
