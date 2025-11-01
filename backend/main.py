"""FastAPI application exposing the inventory features for the new SPA."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from inventory_service import get_saved_views_service, process_sale_transaction
from product_service import InvalidBarcodeError, ProductNotFoundError, update_catalog_entry

from .api import api_router
from .api.products import fetch_products as _fetch_products, load_active_products_map as _load_active_products_map
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

    return app


app = create_app()
