"""FastAPI application exposing the inventory features for the new SPA."""

from __future__ import annotations

import importlib.util

from dotenv import load_dotenv

if importlib.util.find_spec("fastapi") is None:  # pragma: no cover - guard for runtime failures
    raise ModuleNotFoundError(
        "FastAPI is required to run the inventory API. Install dependencies with "
        "`pip install -r requirements.txt` before starting the server."
    )

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure environment variables from a local .env file are available before
# importing modules that resolve the database configuration at import time.
load_dotenv()

from data_repository import (  # re-exported for backwards compatibility in tests
    count_active_admins,
    create_category_record,
    create_client_record,
    create_order_record,
    create_procurement_record,
    create_supplier_record,
    create_user_record,
    delete_category_record,
    delete_client_record,
    delete_supplier_record,
    delete_user_record,
    fetch_user_by_id,
    fetch_user_by_username,
    list_categories,
    list_clients,
    list_orders as repository_list_orders,
    list_procurements,
    list_suppliers,
    list_users as repository_list_users,
    query_df,
    update_category_record,
    update_client_record,
    update_order_record,
    update_procurement_record,
    update_supplier_record,
    update_user_record,
)
from domain import (
    InvalidBarcodeError,
    ProductNotFoundError,
    fetch_products as _fetch_products,
    get_saved_views_service,
    load_active_products_map as _load_active_products_map,
    process_sale_transaction,
    update_catalog_entry,
)

from .api import api_router
from .api.stock_external import router as stock_external_router
from .api.pos import _prepare_checkout_payload
from .settings import APISettings, get_settings
from .security import (
    create_access_token,
    get_current_active_user,
    get_current_user,
    get_password_hash,
    public_user,
    require_admin,
    require_catalog_editor,
    require_catalog_manager,
    require_partner_access,
    token_bearer,
    verify_password,
)


def create_app(settings: APISettings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    cfg = settings or get_settings()
    app = FastAPI(title="Inventaire Epicerie API", version="1.0.0")

    allow_origins = ["*"] if cfg.allow_all_origins else cfg.allowed_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=not cfg.allow_all_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.include_router(stock_external_router)

    return app


app = create_app()
