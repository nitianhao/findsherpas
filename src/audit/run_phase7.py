import sys, json, glob, os
from datetime import datetime
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)
from src.discovery import SiteContext
from src.judge import QueryJudgment
from src.report_generator import generate_report
from src.html_renderer import save_html_report

DOMAIN_SLUG = 'bergzeit_de'
out_dir = f'reports/{DOMAIN_SLUG}'
os.makedirs(out_dir, exist_ok=True)

ctx = SiteContext.model_validate_json(open('reports/_checkpoint_phase1.json').read())
judgments = [QueryJudgment.model_validate(j) for j in json.load(open('reports/_checkpoint_phase6.json'))]

report = generate_report(ctx, judgments)

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
slug = f'{DOMAIN_SLUG}_{ts}'

# screenshot
shots = glob.glob(f'{out_dir}/*.png') + glob.glob(f'{out_dir}/*.jpg') + glob.glob(f'{out_dir}/*.jpeg')
screenshot = shots[0] if shots else None
print('screenshot:', screenshot, flush=True)

md_path = f'{out_dir}/{slug}_report.md'
data_path = f'{out_dir}/{slug}_data.json'
html_path = f'{out_dir}/{slug}_report.html'

open(md_path, 'w', encoding='utf-8').write(report.deep_dive_narrative or '')
json.dump(report.model_dump(), open(data_path, 'w'), ensure_ascii=False, default=str)
saved = save_html_report(report, html_path, screenshot_path=screenshot)

# Capability summary
print('SLUG:', slug, flush=True)
print('MD :', md_path, flush=True)
print('JSON:', data_path, flush=True)
print('HTML:', saved, flush=True)
print(flush=True)
caps = getattr(report, 'capabilities', None) or getattr(report, 'capability_scores', None)
print('overall_score:', getattr(report, 'overall_score', None), flush=True)
print('pass_rate:', getattr(report, 'pass_rate', None), flush=True)
if caps:
    for c in caps:
        name = getattr(c, 'name', getattr(c, 'capability', '?'))
        score = getattr(c, 'score', getattr(c, 'pass_rate', '?'))
        sev = getattr(c, 'severity', '')
        print(f'  CAP {name}: score={score} {sev}', flush=True)
