"""
Batch processing for running scans on multiple domains.

Supports:
- CSV input with domain, vertical, country columns
- Resumable processing (skips already-scanned domains)
- Progress tracking
- Aggregated output for benchmark data
"""

from __future__ import annotations

import csv
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import ScanResult, ProbeScore, BatchStatus
from .scanner import Scanner

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch scanning."""
    input_csv: str
    output_dir: str = "scanner_output"
    results_file: str = "batch_results.json"
    take_screenshots: bool = True
    headed: bool = True
    delay_between_scans: float = 2.0  # seconds
    resume: bool = True


@dataclass
class BatchResults:
    """Aggregated results from a batch scan."""
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    total_domains: int = 0
    completed: int = 0
    failed: int = 0
    blocked: int = 0
    total_llm_cost_usd: float = 0.0
    results: list[dict] = field(default_factory=list)
    
    def add_result(self, result: ScanResult):
        """Add a scan result to the batch."""
        self.results.append(result.model_dump())
        self.total_llm_cost_usd += result.llm_cost_usd
        
        if result.blocked:
            self.blocked += 1
        elif result.overall_score == ProbeScore.ERROR:
            self.failed += 1
        else:
            self.completed += 1


def load_domains_csv(csv_path: str) -> list[dict]:
    """
    Load domains from CSV file.
    
    Expected columns:
    - domain (required): The domain to scan (e.g., example.com or https://example.com)
    - vertical (optional): Industry vertical (e.g., fashion, outdoor, electronics)
    - country (optional): Country code (e.g., US, UK, DE)
    
    Returns list of dicts with domain, vertical, country keys.
    """
    domains = []
    
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Normalize column names
        for row in reader:
            # Handle different column name variations
            domain = (
                row.get('domain') or 
                row.get('Domain') or 
                row.get('url') or 
                row.get('URL') or 
                row.get('site') or
                row.get('Site') or
                ''
            ).strip()
            
            if not domain:
                continue
            
            # Ensure domain has protocol
            if not domain.startswith(('http://', 'https://')):
                domain = f"https://{domain}"
            
            vertical = (
                row.get('vertical') or 
                row.get('Vertical') or 
                row.get('industry') or
                row.get('Industry') or
                ''
            ).strip() or None
            
            country = (
                row.get('country') or 
                row.get('Country') or 
                row.get('market') or
                row.get('Market') or
                ''
            ).strip() or None
            
            domains.append({
                'domain': domain,
                'vertical': vertical,
                'country': country,
            })
    
    return domains


def create_sample_csv(output_path: str = "domains_template.csv"):
    """Create a sample CSV template with example domains."""
    sample_data = [
        {'domain': 'example-store.com', 'vertical': 'fashion', 'country': 'UK'},
        {'domain': 'example-outdoor.com', 'vertical': 'outdoor', 'country': 'US'},
        {'domain': 'example-electronics.de', 'vertical': 'electronics', 'country': 'DE'},
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['domain', 'vertical', 'country'])
        writer.writeheader()
        writer.writerows(sample_data)
    
    return output_path


def run_batch(config: BatchConfig) -> BatchResults:
    """
    Run batch scanning on domains from CSV.
    
    Args:
        config: Batch configuration
    
    Returns:
        BatchResults with all scan results
    """
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_path = output_dir / config.results_file
    
    # Load existing results if resuming
    batch = BatchResults()
    completed_domains = set()
    
    if config.resume and results_path.exists():
        try:
            with open(results_path) as f:
                existing = json.load(f)
                batch = BatchResults(**existing)
                completed_domains = {r['site']['domain'] for r in batch.results}
                logger.info("Resuming batch: %d domains already completed", len(completed_domains))
        except Exception as e:
            logger.warning("Could not load existing results: %s", e)
    
    # Load domains
    domains = load_domains_csv(config.input_csv)
    batch.total_domains = len(domains)
    
    logger.info("Loaded %d domains from %s", len(domains), config.input_csv)
    
    # Filter out already-completed domains
    if config.resume:
        domains = [d for d in domains if d['domain'].replace('https://', '').replace('http://', '').replace('www.', '') not in completed_domains]
        logger.info("%d domains remaining to scan", len(domains))
    
    if not domains:
        logger.info("No domains to scan")
        return batch
    
    # Run scans
    with Scanner(
        output_dir=str(output_dir),
        take_screenshots=config.take_screenshots,
        headed=config.headed,
    ) as scanner:
        for i, domain_info in enumerate(domains, 1):
            domain = domain_info['domain']
            logger.info("[%d/%d] Scanning: %s", i, len(domains), domain)
            
            try:
                result = scanner.scan(
                    domain,
                    vertical=domain_info.get('vertical'),
                    country=domain_info.get('country'),
                )
                
                batch.add_result(result)
                scanner.save_result(result)
                
                logger.info(
                    "  Result: %s (cost: $%.4f, time: %dms)",
                    result.overall_score.value,
                    result.llm_cost_usd,
                    result.execution_time_ms,
                )
                
            except Exception as e:
                logger.error("  Failed: %s", e)
                batch.failed += 1
            
            # Save progress after each scan
            _save_batch_results(batch, results_path)
            
            # Delay between scans to avoid rate limiting
            if i < len(domains):
                time.sleep(config.delay_between_scans)
    
    batch.completed_at = datetime.utcnow().isoformat()
    _save_batch_results(batch, results_path)
    
    return batch


def _save_batch_results(batch: BatchResults, path: Path):
    """Save batch results to JSON file."""
    with open(path, 'w') as f:
        json.dump({
            'started_at': batch.started_at,
            'completed_at': batch.completed_at,
            'total_domains': batch.total_domains,
            'completed': batch.completed,
            'failed': batch.failed,
            'blocked': batch.blocked,
            'total_llm_cost_usd': batch.total_llm_cost_usd,
            'results': batch.results,
        }, f, indent=2, default=str)


def export_for_benchmark(
    results_path: str,
    output_path: Optional[str] = None,
) -> str:
    """
    Export batch results in a format suitable for the benchmark page.
    
    Anonymizes store names and aggregates by vertical/country.
    """
    with open(results_path) as f:
        batch = json.load(f)
    
    benchmark_data = {
        'generated_at': datetime.utcnow().isoformat(),
        'total_stores': len(batch['results']),
        'capability_distribution': {},
        'proof_cards': [],
        'by_vertical': {},
        'by_country': {},
    }
    
    # Aggregate capability scores
    capability_scores = {}
    
    for result in batch['results']:
        if result.get('blocked') or result.get('overall_score') == 'error':
            continue
        
        vertical = result['site'].get('vertical') or 'unknown'
        country = result['site'].get('country') or 'unknown'
        
        # Initialize aggregation buckets
        if vertical not in benchmark_data['by_vertical']:
            benchmark_data['by_vertical'][vertical] = {'count': 0, 'capabilities': {}}
        benchmark_data['by_vertical'][vertical]['count'] += 1
        
        if country not in benchmark_data['by_country']:
            benchmark_data['by_country'][country] = {'count': 0, 'capabilities': {}}
        benchmark_data['by_country'][country]['count'] += 1
        
        # Aggregate capability scores
        for cap in result.get('capabilities', []):
            cap_name = cap['capability']
            score = cap['score']
            
            if cap_name not in capability_scores:
                capability_scores[cap_name] = {'pass': 0, 'partial': 0, 'fail': 0}
            capability_scores[cap_name][score] = capability_scores[cap_name].get(score, 0) + 1
            
            # Also aggregate by vertical
            if cap_name not in benchmark_data['by_vertical'][vertical]['capabilities']:
                benchmark_data['by_vertical'][vertical]['capabilities'][cap_name] = {'pass': 0, 'partial': 0, 'fail': 0}
            benchmark_data['by_vertical'][vertical]['capabilities'][cap_name][score] = \
                benchmark_data['by_vertical'][vertical]['capabilities'][cap_name].get(score, 0) + 1
        
        # Extract proof cards (failed probes with control comparison)
        for scored_probe in result.get('probes', []):
            probe = scored_probe['probe']
            score = scored_probe['score']
            
            if score == 'fail' and probe.get('control_count') and probe['control_count'] > 0:
                benchmark_data['proof_cards'].append({
                    'vertical': vertical,
                    'country': country,
                    'probe_type': probe['probe_type'],
                    'query': probe['query'],
                    'result_count': probe['result_count'],
                    'control_query': probe.get('control_query'),
                    'control_count': probe.get('control_count'),
                    'score_reason': scored_probe['score_reason'],
                })
    
    benchmark_data['capability_distribution'] = capability_scores
    
    # Limit proof cards to most interesting ones
    benchmark_data['proof_cards'] = sorted(
        benchmark_data['proof_cards'],
        key=lambda x: (x['control_count'] or 0) - x['result_count'],
        reverse=True,
    )[:50]
    
    # Save
    if output_path is None:
        output_path = results_path.replace('.json', '_benchmark.json')
    
    with open(output_path, 'w') as f:
        json.dump(benchmark_data, f, indent=2)
    
    return output_path


def main():
    """CLI entry point for batch scanning."""
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Batch scan multiple sites")
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Run batch scan')
    scan_parser.add_argument('input_csv', help='CSV file with domains')
    scan_parser.add_argument('--output-dir', default='scanner_output', help='Output directory')
    scan_parser.add_argument('--no-screenshots', action='store_true', help='Disable screenshots')
    scan_parser.add_argument('--headless', action='store_true', help='Run headless')
    scan_parser.add_argument('--no-resume', action='store_true', help='Start fresh, ignore previous results')
    scan_parser.add_argument('--delay', type=float, default=2.0, help='Delay between scans (seconds)')
    
    # Template command
    template_parser = subparsers.add_parser('template', help='Create sample CSV template')
    template_parser.add_argument('--output', default='domains_template.csv', help='Output path')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export results for benchmark')
    export_parser.add_argument('results_file', help='Batch results JSON file')
    export_parser.add_argument('--output', help='Output path for benchmark data')
    
    args = parser.parse_args()
    
    if args.command == 'template':
        path = create_sample_csv(args.output)
        print(f"Created sample CSV template: {path}")
    
    elif args.command == 'scan':
        config = BatchConfig(
            input_csv=args.input_csv,
            output_dir=args.output_dir,
            take_screenshots=not args.no_screenshots,
            headed=not args.headless,
            resume=not args.no_resume,
            delay_between_scans=args.delay,
        )
        
        results = run_batch(config)
        
        print(f"\n{'='*60}")
        print("Batch Scan Complete")
        print(f"{'='*60}")
        print(f"Total Domains: {results.total_domains}")
        print(f"Completed: {results.completed}")
        print(f"Failed: {results.failed}")
        print(f"Blocked: {results.blocked}")
        print(f"Total LLM Cost: ${results.total_llm_cost_usd:.4f}")
        print(f"\nResults saved to: {config.output_dir}/{config.results_file}")
    
    elif args.command == 'export':
        output_path = export_for_benchmark(args.results_file, args.output)
        print(f"Exported benchmark data to: {output_path}")


if __name__ == "__main__":
    main()
