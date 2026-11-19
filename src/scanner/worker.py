"""
Teardown worker command for processing audit requests.

Run locally on macOS to:
1. Poll for new audit requests from InstantDB
2. Run the scanner on each request's store URL
3. Push results back to InstantDB
4. Generate a report slug for the private report page

Usage:
    python -m scanner.worker [--once] [--interval 60]

Options:
    --once       Process pending requests once and exit
    --interval   Polling interval in seconds (default: 60)
    --dry-run    Run scanner but don't update database
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scanner.scanner import Scanner
from src.scanner.db import InstantDBClient, export_to_json
from src.scanner.models import ProbeScore

load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_report_slug(store_url: str, request_id: str) -> str:
    """Generate a unique, URL-safe slug for the teardown report."""
    # Create a hash from store URL and request ID
    data = f"{store_url}:{request_id}:{datetime.utcnow().isoformat()}"
    hash_str = hashlib.sha256(data.encode()).hexdigest()[:12]
    
    # Extract domain for readability
    try:
        from urllib.parse import urlparse
        domain = urlparse(store_url).netloc.replace("www.", "")
        # Sanitize for URL
        domain = domain.replace(".", "-").replace(":", "-")[:30]
    except:
        domain = "store"
    
    return f"{domain}-{hash_str}"


def process_request(
    db: InstantDBClient,
    scanner: Scanner,
    request: dict,
    dry_run: bool = False,
) -> bool:
    """
    Process a single audit request.
    
    Returns True if successful, False otherwise.
    """
    request_id = request["id"]
    store_url = request["store_url"]
    
    logger.info("Processing request %s for %s", request_id, store_url)
    
    # Update status to scanning
    if not dry_run:
        db.update_audit_request_status(request_id, "scanning")
    
    try:
        # Run the scanner
        result = scanner.scan(store_url)
        
        # Save local copy
        scanner.save_result(result)
        
        if dry_run:
            logger.info("DRY RUN: Would push results for %s", store_url)
            logger.info("  Overall score: %s", result.overall_score.value)
            logger.info("  LLM cost: $%.4f", result.llm_cost_usd)
            return True
        
        # Push results to InstantDB
        db.push_teardown_scan(result, request_id)
        
        # Generate report slug
        report_slug = generate_report_slug(store_url, request_id)
        
        # Update the request with the report slug
        db._transact([
            ["update", "auditRequests", request_id, {
                "report_slug": report_slug,
                "updated_at": datetime.utcnow().isoformat(),
            }],
        ])
        
        logger.info(
            "Completed request %s: score=%s, slug=%s",
            request_id, result.overall_score.value, report_slug
        )
        
        return True
        
    except Exception as e:
        logger.error("Failed to process request %s: %s", request_id, e)
        
        if not dry_run:
            # Update status to indicate error
            db._transact([
                ["update", "auditRequests", request_id, {
                    "status": "new",  # Reset to new so it can be retried
                    "notes": f"Scan failed: {str(e)}",
                    "updated_at": datetime.utcnow().isoformat(),
                }],
            ])
        
        return False


def run_worker(
    poll_interval: int = 60,
    run_once: bool = False,
    dry_run: bool = False,
    output_dir: str = "scanner_output",
    headed: bool = True,
):
    """
    Run the teardown worker.
    
    Args:
        poll_interval: Seconds between polling for new requests
        run_once: Process pending requests and exit
        dry_run: Run scanner but don't update database
        output_dir: Directory for scanner output
        headed: Run browser in headed mode
    """
    logger.info("Starting teardown worker")
    logger.info("  Poll interval: %ds", poll_interval)
    logger.info("  Run once: %s", run_once)
    logger.info("  Dry run: %s", dry_run)
    logger.info("  Output dir: %s", output_dir)
    logger.info("  Headed browser: %s", headed)
    
    try:
        db = InstantDBClient()
    except ValueError as e:
        logger.error("InstantDB not configured: %s", e)
        logger.error("Set NEXT_PUBLIC_INSTANT_APP_ID and INSTANT_APP_ADMIN_TOKEN")
        sys.exit(1)
    
    scanner = Scanner(
        output_dir=output_dir,
        take_screenshots=True,
        headed=headed,
    )
    
    processed = 0
    failed = 0
    
    try:
        while True:
            # Get pending requests
            requests = db.get_pending_audit_requests()
            
            if requests:
                logger.info("Found %d pending requests", len(requests))
                
                for request in requests:
                    success = process_request(db, scanner, request, dry_run)
                    if success:
                        processed += 1
                    else:
                        failed += 1
            else:
                logger.debug("No pending requests")
            
            if run_once:
                break
            
            logger.debug("Sleeping for %ds", poll_interval)
            time.sleep(poll_interval)
            
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    finally:
        db.close()
    
    logger.info("Worker finished: %d processed, %d failed", processed, failed)
    return processed, failed


def main():
    parser = argparse.ArgumentParser(
        description="Teardown worker for processing audit requests"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process pending requests once and exit",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Polling interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run scanner but don't update database",
    )
    parser.add_argument(
        "--output-dir",
        default="scanner_output",
        help="Output directory for scanner results",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (default: headed)",
    )
    
    args = parser.parse_args()
    
    run_worker(
        poll_interval=args.interval,
        run_once=args.once,
        dry_run=args.dry_run,
        output_dir=args.output_dir,
        headed=not args.headless,
    )


if __name__ == "__main__":
    main()
