"""
Search Scanner for Find Sherpas Lead Generation

A lightweight, standardized scanner that runs deterministic probes
against ecommerce site search to generate benchmark data.
"""

from .models import ProbeType, ProbeResult
from .scorer import score_probe_result, ScanScore

__all__ = ["Scanner", "ProbeType", "ProbeResult", "score_probe_result", "ScanScore"]


def __getattr__(name):
    if name == "Scanner":
        from .scanner import Scanner
        return Scanner
    raise AttributeError(name)
