from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Mapping

from sqlalchemy import text
from sqlalchemy.engine import Engine

from telemetry import get_tracer, instrument_sqlalchemy_engine


logger = logging.getLogger(__name__)


@dataclass
class SavedViewsService:
    """Service layer managing the persistence of saved view collections."""

    engine_factory: Callable[[], Engine]
    tracer_name: str = "services.saved_views"
    _tracer: object = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._tracer = get_tracer(self.tracer_name)

    def fetch_views(self, user_id: int) -> dict[str, list[dict]]:
        with self._tracer.start_as_current_span("saved_views.fetch") as span:
            span.set_attribute("saved_views.user_id", user_id)

            engine = self.engine_factory()
            instrument_sqlalchemy_engine(engine)

            with engine.begin() as conn:
                self._ensure_table(conn)
                row = conn.execute(
                    text(
                        "SELECT payload FROM user_saved_views WHERE user_id = :user_id"
                    ),
                    {"user_id": user_id},
                ).fetchone()

            if not row or not row[0]:
                span.set_attribute("saved_views.found", False)
                return {}

            try:
                payload = json.loads(row[0])
                span.set_attribute("saved_views.found", True)
                span.set_attribute("saved_views.slot_count", len(payload))
                return payload if isinstance(payload, dict) else {}
            except json.JSONDecodeError:
                logger.warning("Invalid saved views payload for user %s", user_id)
                span.set_attribute("saved_views.error", "invalid_json")
                return {}

    def persist_views(self, user_id: int, slots: Mapping[str, list[Mapping]]) -> None:
        with self._tracer.start_as_current_span("saved_views.persist") as span:
            span.set_attribute("saved_views.user_id", user_id)
            span.set_attribute("saved_views.slot_count", len(slots))

            payload = json.dumps(slots, default=str)

            engine = self.engine_factory()
            instrument_sqlalchemy_engine(engine)

            with engine.begin() as conn:
                self._ensure_table(conn)
                conn.execute(
                    text(
                        """
                        INSERT INTO user_saved_views (user_id, payload, updated_at)
                        VALUES (:user_id, :payload, :updated_at)
                        ON CONFLICT(user_id)
                        DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
                        """
                    ),
                    {
                        "user_id": user_id,
                        "payload": payload,
                        "updated_at": datetime.utcnow(),
                    },
                )

    def _ensure_table(self, connection) -> None:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_saved_views (
                    user_id INTEGER PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )


__all__ = ["SavedViewsService"]
