"""High-level domain services shared across API and UI clients."""

from .catalogue import (
    InvalidBarcodeError,
    ProductNotFoundError,
    delete_product_by_barcode,
    fetch_products,
    load_active_products_map,
    update_catalog_entry,
)
from .analytics import (
    compute_stock_diagnostics_dataframe,
    count_table_rows_dataframe,
    fetch_customer_catalog_dataframe,
    fetch_duplicate_barcodes_dataframe,
    fetch_movement_timeseries,
    fetch_recent_movements,
    fetch_recent_suppliers_dataframe,
    fetch_stock_kpis,
    fetch_top_sales_products,
    fetch_top_stock_value_products,
    fetch_products_list_dataframe,
    lookup_product_name_by_barcode,
    preview_table_dataframe,
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
    "compute_stock_diagnostics_dataframe",
    "count_table_rows_dataframe",
    "fetch_customer_catalog_dataframe",
    "fetch_duplicate_barcodes_dataframe",
    "fetch_movement_timeseries",
    "fetch_recent_movements",
    "fetch_recent_suppliers_dataframe",
    "fetch_stock_kpis",
    "fetch_top_sales_products",
    "fetch_top_stock_value_products",
    "fetch_products_list_dataframe",
    "lookup_product_name_by_barcode",
    "preview_table_dataframe",
]
