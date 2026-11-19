"""
InstantDB sync for pushing scanner results to the site database.

Pushes anonymized benchmark data for the /benchmark page and
individual scan results for teardown reports.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Optional

import httpx

from .models import ScanResult, ProbeScore

logger = logging.getLogger(__name__)


class InstantDBClient:
    """Client for syncing scanner results to InstantDB."""
    
    def __init__(
        self,
        app_id: Optional[str] = None,
        admin_token: Optional[str] = None,
    ):
        self.app_id = app_id or os.environ.get("NEXT_PUBLIC_INSTANT_APP_ID")
        self.admin_token = admin_token or os.environ.get("INSTANT_APP_ADMIN_TOKEN")
        
        if not self.app_id or not self.admin_token:
            raise ValueError(
                "InstantDB credentials required. Set NEXT_PUBLIC_INSTANT_APP_ID and "
                "INSTANT_APP_ADMIN_TOKEN environment variables."
            )
        
        self.base_url = "https://api.instantdb.com/admin"
        self._client = httpx.Client(timeout=30.0)
    
    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.admin_token}",
        }
    
    def _transact(self, ops: list[dict]) -> dict:
        """Execute a transaction against InstantDB."""
        response = self._client.post(
            f"{self.base_url}/transact",
            headers=self._headers(),
            json={
                "app-id": self.app_id,
                "tx-steps": ops,
            },
        )
        response.raise_for_status()
        return response.json()
    
    def _query(self, query: dict) -> dict:
        """Execute a query against InstantDB."""
        response = self._client.post(
            f"{self.base_url}/query",
            headers=self._headers(),
            json={
                "app-id": self.app_id,
                "query": query,
            },
        )
        response.raise_for_status()
        return response.json()
    
    def push_benchmark_scan(self, result: ScanResult) -> str:
        """
        Push a scan result to the benchmarkScans table for the /benchmark page.
        
        Stores anonymized data (vertical/country, no domain names).
        Returns the created record ID.
        """
        import uuid
        scan_id = str(uuid.uuid4())
        
        # Build capability scores summary
        capability_data = {}
        for cap in result.capabilities:
            capability_data[cap.capability] = {
                "score": cap.score.value,
                "summary": cap.summary,
                "probe_count": len(cap.probes),
            }
        
        # Build proof cards (failed probes with control comparison)
        proof_cards = []
        for scored_probe in result.probes:
            probe = scored_probe.probe
            if scored_probe.score == ProbeScore.FAIL and probe.control_count and probe.control_count > 0:
                proof_cards.append({
                    "probe_type": probe.probe_type.value,
                    "query": probe.query,
                    "result_count": probe.result_count,
                    "control_query": probe.control_query,
                    "control_count": probe.control_count,
                    "score_reason": scored_probe.score_reason,
                })
        
        # Create the benchmark scan record
        ops = [
            ["update", "benchmarkScans", scan_id, {
                "vertical": result.site.vertical or "unknown",
                "country": result.site.country or "unknown",
                "overall_score": result.overall_score.value,
                "capabilities": json.dumps(capability_data),
                "proof_cards": json.dumps(proof_cards[:10]),  # Limit to 10 best examples
                "probe_count": len(result.probes),
                "llm_cost_usd": result.llm_cost_usd,
                "execution_time_ms": result.execution_time_ms,
                "scanned_at": result.scanned_at,
                "created_at": datetime.utcnow().isoformat(),
            }],
        ]
        
        self._transact(ops)
        logger.info("Pushed benchmark scan: %s (vertical=%s, country=%s)", 
                    scan_id, result.site.vertical, result.site.country)
        return scan_id
    
    def push_teardown_scan(
        self,
        result: ScanResult,
        audit_request_id: str,
    ) -> str:
        """
        Push a scan result for a teardown request.
        
        Links to the auditRequests record and stores full scan data
        for the private teardown report.
        
        Returns the created record ID.
        """
        import uuid
        scan_id = str(uuid.uuid4())
        
        # Store full probe results for the report
        probe_data = []
        for scored_probe in result.probes:
            probe = scored_probe.probe
            probe_data.append({
                "probe_type": probe.probe_type.value,
                "query": probe.query,
                "control_query": probe.control_query,
                "status": probe.status.value,
                "result_count": probe.result_count,
                "control_count": probe.control_count,
                "results": [r.model_dump() for r in probe.results[:5]],
                "screenshot_path": probe.screenshot_path,
                "score": scored_probe.score.value,
                "score_reason": scored_probe.score_reason,
                "rationale": probe.rationale,
            })
        
        # Build capability scores
        capability_data = {}
        for cap in result.capabilities:
            capability_data[cap.capability] = {
                "score": cap.score.value,
                "summary": cap.summary,
            }
        
        ops = [
            # Create the teardown scan record
            ["update", "teardownScans", scan_id, {
                "domain": result.site.domain,
                "site_name": result.site.site_name,
                "vertical": result.site.vertical or "unknown",
                "country": result.site.country or "unknown",
                "overall_score": result.overall_score.value,
                "capabilities": json.dumps(capability_data),
                "probes": json.dumps(probe_data),
                "blocked": result.blocked,
                "llm_cost_usd": result.llm_cost_usd,
                "execution_time_ms": result.execution_time_ms,
                "scanned_at": result.scanned_at,
                "created_at": datetime.utcnow().isoformat(),
            }],
            # Link to the audit request
            ["link", "teardownScans", scan_id, {"auditRequest": audit_request_id}],
            # Update the audit request status
            ["update", "auditRequests", audit_request_id, {
                "status": "ready_for_review",
                "scanned_at": datetime.utcnow().isoformat(),
            }],
        ]
        
        self._transact(ops)
        logger.info("Pushed teardown scan: %s for request %s", scan_id, audit_request_id)
        return scan_id
    
    def get_pending_audit_requests(self) -> list[dict]:
        """Get audit requests that are ready to be scanned."""
        result = self._query({
            "auditRequests": {
                "$": {"where": {"status": "new"}},
            },
        })
        return result.get("auditRequests", [])
    
    def update_audit_request_status(self, request_id: str, status: str) -> None:
        """Update the status of an audit request."""
        ops = [
            ["update", "auditRequests", request_id, {
                "status": status,
                "updated_at": datetime.utcnow().isoformat(),
            }],
        ]
        self._transact(ops)
    
    def get_benchmark_data(self) -> dict:
        """
        Fetch aggregated benchmark data for the /benchmark page.
        
        Returns anonymized statistics across all scans.
        """
        result = self._query({
            "benchmarkScans": {},
        })
        
        scans = result.get("benchmarkScans", [])
        if not scans:
            return {
                "total_stores": 0,
                "capability_distribution": {},
                "proof_cards": [],
                "by_vertical": {},
                "by_country": {},
            }
        
        # Aggregate data
        capability_counts = {}
        proof_cards = []
        by_vertical = {}
        by_country = {}
        
        for scan in scans:
            vertical = scan.get("vertical", "unknown")
            country = scan.get("country", "unknown")
            
            # Count by vertical/country
            if vertical not in by_vertical:
                by_vertical[vertical] = {"count": 0, "scores": []}
            by_vertical[vertical]["count"] += 1
            by_vertical[vertical]["scores"].append(scan.get("overall_score"))
            
            if country not in by_country:
                by_country[country] = {"count": 0, "scores": []}
            by_country[country]["count"] += 1
            by_country[country]["scores"].append(scan.get("overall_score"))
            
            # Aggregate capability scores
            try:
                caps = json.loads(scan.get("capabilities", "{}"))
                for cap_name, cap_data in caps.items():
                    if cap_name not in capability_counts:
                        capability_counts[cap_name] = {"pass": 0, "partial": 0, "fail": 0}
                    score = cap_data.get("score", "error")
                    if score in capability_counts[cap_name]:
                        capability_counts[cap_name][score] += 1
            except json.JSONDecodeError:
                pass
            
            # Collect proof cards
            try:
                cards = json.loads(scan.get("proof_cards", "[]"))
                for card in cards:
                    card["vertical"] = vertical
                    card["country"] = country
                    proof_cards.append(card)
            except json.JSONDecodeError:
                pass
        
        # Sort proof cards by impact (control_count - result_count)
        proof_cards.sort(
            key=lambda x: (x.get("control_count", 0) or 0) - (x.get("result_count", 0) or 0),
            reverse=True,
        )
        
        return {
            "total_stores": len(scans),
            "capability_distribution": capability_counts,
            "proof_cards": proof_cards[:30],  # Top 30 most impactful failures
            "by_vertical": by_vertical,
            "by_country": by_country,
        }
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


def export_to_json(result: ScanResult, output_path: str) -> str:
    """
    Export a scan result to a JSON file that can be loaded by the site.
    
    This is an alternative to InstantDB for simpler deployments.
    """
    data = result.model_dump()
    
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    
    return output_path
