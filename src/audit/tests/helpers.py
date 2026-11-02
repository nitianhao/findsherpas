"""Shared offline fixtures for the audit test suite. Nothing here touches the network."""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from types import SimpleNamespace

from src.models import AuditReport

AUDIT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = AUDIT_ROOT / "reports"

# Keys must never be needed by tests; make any accidental real client fail fast.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-offline")
os.environ.setdefault("VOYAGE_API_KEY", "test-key-offline")


def historical_reports() -> dict[str, AuditReport]:
    """Every historical *_data.json that still validates, keyed by site folder."""
    out: dict[str, AuditReport] = {}
    for path in sorted(glob.glob(str(REPORTS_DIR / "*" / "*_data.json"))):
        try:
            out[Path(path).parent.name] = AuditReport.model_validate(json.loads(Path(path).read_text()))
        except Exception:
            continue  # e.g. ahlens uses retired categories (USE_CASE)
    return out


def all_judgments(report: AuditReport):
    return [j for cs in report.capability_scores for j in cs.judgments]


class FakeResponse(SimpleNamespace):
    pass


def fake_text_response(text: str, stop_reason: str = "end_turn"):
    return FakeResponse(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0,
                              cache_creation_input_tokens=0),
    )


class FakeMessages:
    """Stands in for client.messages; returns queued responses and records calls."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def _next(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("FakeMessages: no more queued responses")
        r = self._responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    create = _next
    parse = _next


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)
