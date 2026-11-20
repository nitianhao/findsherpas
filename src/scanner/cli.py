"""Local-only scanner CLI. No database writes or emails."""
import argparse
import logging
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', nargs='?')
    parser.add_argument('--batch', metavar='CSV')
    parser.add_argument('--vertical')
    parser.add_argument('--country')
    parser.add_argument('--env-file', help='Read API keys from this dotenv file')
    parser.add_argument('--output-dir', default='scanner_output')
    parser.add_argument('--no-screenshots', action='store_true')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--headed', action='store_true', help='Default')
    mode.add_argument('--headless', action='store_true')
    args = parser.parse_args()
    if bool(args.url) == bool(args.batch):
        parser.error('Provide either a URL or --batch CSV')
    if args.env_file:
        load_dotenv(args.env_file, override=False)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if args.batch:
        from .batch import BatchConfig, run_batch
        result = run_batch(BatchConfig(input_csv=args.batch, output_dir=args.output_dir,
                           headed=not args.headless, take_screenshots=not args.no_screenshots))
        print(f'Completed: {result.completed}; blocked: {result.blocked}; errors: {result.failed}')
    else:
        from .scanner import Scanner
        with Scanner(args.output_dir, headed=not args.headless,
                     take_screenshots=not args.no_screenshots) as scanner:
            result = scanner.scan(args.url, vertical=args.vertical, country=args.country)
            path = scanner.save_result(result)
            print(f'{result.site.domain}: {result.overall_score.value}; '
                  f'${result.llm_cost_usd:.6f}; {result.execution_time_ms / 1000:.1f}s; {path}')


if __name__ == '__main__':
    main()
