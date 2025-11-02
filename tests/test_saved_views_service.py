from __future__ import annotations

from sqlalchemy import create_engine, text

from services.preferences import SavedViewsService


def test_saved_views_service_persist_and_fetch(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)
    monkeypatch.setattr("services.preferences.instrument_sqlalchemy_engine", lambda engine: None)
    service = SavedViewsService(lambda: engine)

    initial = service.fetch_views(user_id=42)
    assert initial == {}

    payload = {
        "home": [
            {"id": "low-stock", "label": "Stock faible", "to": "/catalogue"},
            {"id": "promo", "label": "Promotions", "badge": {"label": "Promo"}},
        ]
    }

    service.persist_views(user_id=42, slots=payload)

    stored = service.fetch_views(user_id=42)
    assert stored == payload

    # Ensure data updated on subsequent persist
    updated = {"home": payload["home"][:1], "dashboard": [{"id": "alerts", "label": "Alertes"}]}
    service.persist_views(user_id=42, slots=updated)

    result = service.fetch_views(user_id=42)
    assert result == updated

    with engine.begin() as conn:
        row = conn.execute(text("SELECT COUNT(*) FROM user_saved_views")).scalar()
        assert row == 1
