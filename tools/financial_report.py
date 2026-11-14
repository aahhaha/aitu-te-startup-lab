from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from finance import *
r={'base':calculate(Assumptions()),'churn_sensitivity':[calculate(Assumptions(monthly_churn=c)) for c in [.02,.05,.10]],'synthetic_funnel_example':funnel(100,20,8)}
Path('reports').mkdir(exist_ok=True);Path('reports/financial-scenarios.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
