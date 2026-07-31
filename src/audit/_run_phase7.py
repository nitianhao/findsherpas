import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv(override=True)
import json, logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', stream=sys.stdout)
for n in ('urllib3','httpx','anthropic'): logging.getLogger(n).setLevel(logging.WARNING)
from datetime import datetime
from src.models import SiteContext, QueryJudgment
from src.report_generator import generate_report
from src.html_renderer import save_html_report

slug='huckberry_com'
outdir=f'reports/{slug}'
ctx=SiteContext.model_validate_json(open('reports/_checkpoint_phase1.json').read())
judgments=[QueryJudgment.model_validate(j) for j in json.load(open('reports/_checkpoint_phase6_huckberry.json'))]

print(f'Generating report for {ctx.site_name} ({len(judgments)} judgments)...', flush=True)
report=generate_report(ctx, judgments)

ts=datetime.now().strftime('%Y%m%d_%H%M%S')
base=f'{outdir}/{slug}_{ts}'
open(f'{base}_report.md','w',encoding='utf-8').write(report.deep_dive_narrative or '')
json.dump(report.model_dump(), open(f'{base}_data.json','w'), default=str, indent=2)
html_path=save_html_report(report, f'{base}_report.html', screenshot_path=f'{outdir}/{slug}_cover.png')

print('=== REPORT SAVED ===', flush=True)
print('md  :', f'{base}_report.md')
print('json:', f'{base}_data.json')
print('html:', html_path)
# capability pass summary
from src.report_generator import compute_aggregate_stats
stats=compute_aggregate_stats(judgments)
print('pass_rate:', stats.get('pass_rate') or stats.get('pct_pass'))
print('zero_result_count:', stats.get('zero_result_count'))
