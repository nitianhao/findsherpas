from pathlib import Path
from src.fetcher import fetch_all_outcomes
from src.candidates.runner import save,stamp
p=Path('reports/imerco_dk/ordinary_20261104');history={}
def emit(o):
 history[o.query]={'observed_at':stamp(),'outcome':o.model_dump(mode='json')};save(p/'rechecks.json',history)
fetch_all_outcomes(['stegepande','pande til stegning','vandglas','drikkeglas','vase','kaffekop'],'https://www.imerco.dk/search?query={}',max_results=10,evidence_dir=str(p/'evidence/recheck'),on_outcome=emit,light=True)
