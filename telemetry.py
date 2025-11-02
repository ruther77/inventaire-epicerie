from __future__ import annotations

import logging
import os
from contextlib import nullcontext
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )
except ImportError:  # pragma: no cover - graceful fallback when otel is absent
    trace = None
    SQLAlchemyInstrumentor = None


class _NoOpSpan:
    def __enter__(self):  # pragma: no cover - trivial
        return self

    def __exit__(self, exc_type, exc, tb):  # pragma: no cover - trivial
        return False

    def set_attribute(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - trivial
        return None

    def record_exception(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - trivial
        return None


class _NoOpTracer:
    def start_as_current_span(self, *_args: Any, **_kwargs: Any):  # pragma: no cover - trivial
        return nullcontext(_NoOpSpan())


_NOOP_TRACER = _NoOpTracer()
_instrumented_engines: set[int] = set()


@lru_cache(maxsize=1)
def _ensure_tracer_provider() -> bool:
    if trace is None:
        logger.debug("OpenTelemetry not available, falling back to no-op tracer.")
        return False

    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        return True

    resource = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "inventaire-epicerie"),
    })
    provider = TracerProvider(resource=resource)

    exporter: Any
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "false").lower() in {"1", "true", "yes"},
        )
        processor = BatchSpanProcessor(exporter)
    else:
        exporter = ConsoleSpanExporter()
        processor = SimpleSpanProcessor(exporter)

    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    logger.info("OpenTelemetry tracing initialised with exporter %s", exporter.__class__.__name__)
    return True


def get_tracer(name: str):
    if not _ensure_tracer_provider():
        return _NOOP_TRACER
    return trace.get_tracer(name)


def instrument_sqlalchemy_engine(engine) -> None:
    if SQLAlchemyInstrumentor is None:
        return
    identifier = id(engine)
    if identifier in _instrumented_engines:
        return
    SQLAlchemyInstrumentor().instrument(engine=engine)
    _instrumented_engines.add(identifier)


__all__ = ["get_tracer", "instrument_sqlalchemy_engine"]
