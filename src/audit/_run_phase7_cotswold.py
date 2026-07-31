import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv(override=True)
import json, time
from src.discovery import SiteContext
from src.models import QueryJudgment
from src.report_generator import generate_report
from src.html_renderer import save_html_report, find_cover_screenshot

SLUG = 'cotswoldoutdoor_com'
OUTDIR = f'reports/{SLUG}'

sc = SiteContext.model_validate_json(open('reports/_checkpoint_phase1.json').read())

# Reconstruct judgments, preserving phase-3 query order
p6 = json.load(open('reports/_checkpoint_phase6.json'))
order = [q['query'] for q in json.load(open('reports/_checkpoint_phase3.json'))]
judgments = []
for q in order:
    if q in p6:
        judgments.append(QueryJudgment.model_validate(p6[q]))
print(f"Reconstructed {len(judgments)} judgments", flush=True)

report = generate_report(sc, judgments)

ts = time.strftime('%Y%m%d_%H%M%S')
slug = f'{SLUG}_{ts}'

# Markdown body
open(f'{OUTDIR}/{slug}_report.md', 'w', encoding='utf-8').write(report.deep_dive_narrative or '')
# Data JSON
json.dump(report.model_dump(), open(f'{OUTDIR}/{slug}_data.json', 'w'), default=str, indent=2)
# HTML (auto-detects screenshot in folder, but pass explicitly to be safe)
shot = find_cover_screenshot(OUTDIR)
print(f"cover screenshot: {shot}", flush=True)
html_path = save_html_report(report, f'{OUTDIR}/{slug}_report.html', screenshot_path=shot)

print("\nFILES:", flush=True)
print(f"  {OUTDIR}/{slug}_report.md", flush=True)
print(f"  {OUTDIR}/{slug}_data.json", flush=True)
print(f"  {html_path}", flush=True)

# Capability summary
print("\nCAPABILITY SCORES:", flush=True)
try:
    for c in report.capability_scores:
        sev = c.severity.value if hasattr(c.severity, 'value') else c.severity
        print(f"  {str(sev).split(' ')[0]:9s} {c.capability}", flush=True)
except Exception as e:
    print("  (capability_scores attr differs:", e, ")", flush=True)
