"""OpenTelemetry tracing helper — sends spans to LangSmith via OTLP.

Usage in any script:
    from app.utils.tracing import configure_tracing, get_tracer

    configure_tracing()  # call once at script start
    tracer = get_tracer(__name__)

    with tracer.start_as_current_span("my-operation") as span:
        span.set_attribute("date", "2026-04-26")
        ...

Decorator usage on API client methods:
    from app.utils.tracing import traced, set_span_io

    @traced("intervals.icu · fetch wellness", kind="tool")
    async def get_wellness(self, date: str) -> dict:
        result = ...
        set_span_io(input={"date": date}, output=f"RHR={result.get('restingHR')} HRV={result.get('hrv')}")
        return result

No-ops silently when CLAUDE_CODE_ENABLE_TELEMETRY is not set.
"""
from __future__ import annotations

import asyncio
import functools
import json
import os
from contextlib import contextmanager
from typing import Any, Callable, Generator

_configured = False


def _telemetry_enabled() -> bool:
    return bool(os.getenv("CLAUDE_CODE_ENABLE_TELEMETRY"))


def configure_tracing() -> None:
    """Initialize TracerProvider + OTLP exporter + httpx auto-instrumentation.

    Idempotent — safe to call multiple times.
    """
    global _configured
    if _configured:
        return
    if not _telemetry_enabled():
        _configured = True
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_RESOURCE_ATTRIBUTES", "coach-trainer")
            .replace("service.name=", "")
            .split(",")[0]
            .split("=")[-1],
        }
    )
    provider = TracerProvider(resource=resource)

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    headers_raw = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")
    headers: dict[str, str] = {}
    for pair in headers_raw.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            headers[k.strip()] = v.strip()

    if endpoint:
        exporter = OTLPSpanExporter(
            endpoint=f"{endpoint.rstrip('/')}/v1/traces",
            headers=headers,
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    # httpx auto-instrumentation is optional — gracefully skip if not installed.
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except ImportError:
        pass

    _configured = True


def get_tracer(name: str):
    """Return an OpenTelemetry tracer. configure_tracing() must be called first."""
    from opentelemetry import trace

    return trace.get_tracer(name)


# ─── Helper API for human-readable spans ────────────────────────────────────

def _serialize(value: Any, truncate: int) -> str:
    """Render any input/output as a compact string, truncated with ellipsis."""
    if isinstance(value, str):
        s = value
    else:
        try:
            s = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            s = str(value)
    if len(s) > truncate:
        return s[: truncate - 1] + "…"
    return s


def _current_span():
    if not _telemetry_enabled():
        return None
    from opentelemetry import trace

    span = trace.get_current_span()
    if not span or not span.get_span_context().is_valid:
        return None
    return span


def set_span_name(name: str) -> None:
    """Set LangSmith run name (overrides span name in the LangSmith UI)."""
    span = _current_span()
    if span is None:
        return
    span.set_attribute("langsmith.trace.name", name)


def set_span_io(
    *,
    input: Any = None,
    output: Any = None,
    truncate: int = 500,
) -> None:
    """Set human-readable input/output on the current span.

    LangSmith picks these up as `input.value` / `output.value`.
    Both fields are optional; pass only what you have.
    """
    span = _current_span()
    if span is None:
        return
    if input is not None:
        span.set_attribute("input.value", _serialize(input, truncate))
    if output is not None:
        span.set_attribute("output.value", _serialize(output, truncate))


def set_span_metadata(**kwargs: Any) -> None:
    """Set `langsmith.metadata.{key}` attributes on the current span."""
    span = _current_span()
    if span is None:
        return
    for key, value in kwargs.items():
        if value is None:
            continue
        if isinstance(value, (str, bool, int, float)):
            span.set_attribute(f"langsmith.metadata.{key}", value)
        else:
            span.set_attribute(f"langsmith.metadata.{key}", _serialize(value, 500))


def set_span_kind(kind: str) -> None:
    """Set LangSmith run type: chain | tool | llm | retriever | embedding | prompt | parser."""
    span = _current_span()
    if span is None:
        return
    span.set_attribute("langsmith.span.kind", kind)


def traced(name: str, *, kind: str = "chain") -> Callable:
    """Decorator that wraps a sync or async function in a named span.

    The function body can call set_span_io / set_span_metadata to enrich the span.
    No-op when telemetry is disabled.
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                if not _telemetry_enabled():
                    return await func(*args, **kwargs)
                tracer = get_tracer(func.__module__)
                with tracer.start_as_current_span(name) as span:
                    span.set_attribute("langsmith.trace.name", name)
                    span.set_attribute("langsmith.span.kind", kind)
                    try:
                        return await func(*args, **kwargs)
                    except Exception as exc:
                        from opentelemetry.trace import StatusCode

                        span.set_status(StatusCode.ERROR, str(exc))
                        raise

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _telemetry_enabled():
                return func(*args, **kwargs)
            tracer = get_tracer(func.__module__)
            with tracer.start_as_current_span(name) as span:
                span.set_attribute("langsmith.trace.name", name)
                span.set_attribute("langsmith.span.kind", kind)
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    from opentelemetry.trace import StatusCode

                    span.set_status(StatusCode.ERROR, str(exc))
                    raise

        return sync_wrapper

    return decorator


@contextmanager
def script_span(script_name: str, *, display_name: str | None = None, **attrs: str | int | float) -> Generator:
    """Context manager that wraps a whole script execution in a root span.

    `display_name` (optional) overrides the LangSmith run name — pass a sprechende
    English description like "Load coach context — 2026-04-26".
    """
    configure_tracing()
    tracer = get_tracer(script_name)
    with tracer.start_as_current_span(script_name) as span:
        if display_name:
            span.set_attribute("langsmith.trace.name", display_name)
        span.set_attribute("langsmith.span.kind", "chain")
        for k, v in attrs.items():
            span.set_attribute(k, v)
        try:
            yield span
        except Exception as exc:
            from opentelemetry.trace import StatusCode

            span.set_status(StatusCode.ERROR, str(exc))
            raise
