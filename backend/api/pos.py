"""Point of sale endpoints."""

from __future__ import annotations

import base64
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from domain.catalogue import load_active_products_map
from domain.sales import process_sale_transaction

from ..security import get_current_active_user
from .schemas import CheckoutRequest, CheckoutResponse, POSCartLine
from .utils import as_decimal, quantize_currency

router = APIRouter(prefix="/pos", tags=["pos"])


def _prepare_checkout_payload(cart: list[POSCartLine]) -> tuple[list[dict[str, object]], Decimal, Decimal]:
    if not cart:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le panier est vide.")

    product_ids = {line.id for line in cart}
    product_map = load_active_products_map(product_ids)
    missing = sorted(pid for pid in product_ids if pid not in product_map)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Produits introuvables ou inactifs: {', '.join(map(str, missing))}",
        )

    sanitized: list[dict[str, object]] = []
    total_ht = Decimal("0")
    total_ttc = Decimal("0")

    for line in cart:
        qty = as_decimal(line.qty)
        if qty <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Quantité invalide pour le produit {line.id}",
            )

        product_data = product_map[line.id]
        unit_price = as_decimal(product_data.get("prix_vente"))
        tva_rate = as_decimal(product_data.get("tva"))

        sanitized.append(
            {
                "id": line.id,
                "nom": product_data.get("nom") or f"Produit {line.id}",
                "prix_vente": float(unit_price),
                "tva": float(tva_rate),
                "qty": float(qty),
            }
        )

        line_ht = qty * unit_price
        total_ht += line_ht
        total_ttc += line_ht * (Decimal("1") + tva_rate / Decimal("100"))

    return sanitized, total_ht, total_ttc


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(payload: CheckoutRequest, current_user: dict = Depends(get_current_active_user)) -> CheckoutResponse:
    sanitized_cart, total_ht, total_ttc = _prepare_checkout_payload(payload.cart)
    success, message, receipt = process_sale_transaction(
        sanitized_cart,
        current_user.get("username") or "api_user",
    )

    total_ht_value = float(quantize_currency(total_ht))
    total_ttc_value = float(quantize_currency(total_ttc))

    if not success:
        return CheckoutResponse(
            success=False,
            message=message,
            total_ht=total_ht_value,
            total_ttc=total_ttc_value,
        )

    receipt_filename = None
    receipt_base64 = None
    if receipt:
        receipt_filename = receipt.get("filename")
        raw_content = receipt.get("content")
        if isinstance(raw_content, bytes):
            receipt_base64 = base64.b64encode(raw_content).decode("ascii")

    return CheckoutResponse(
        success=True,
        message=message,
        receipt_filename=receipt_filename,
        receipt_base64=receipt_base64,
        total_ht=total_ht_value,
        total_ttc=total_ttc_value,
    )
