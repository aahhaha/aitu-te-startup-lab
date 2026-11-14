from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,platform,subprocess,sys,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1];reports=root/'reports';reports.mkdir(exist_ok=True)
r=subprocess.run([sys.executable,'-m','pytest','-q','-m','not browser and not external','--junitxml='+str(reports/'junit.xml')],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(reports/'test-output.txt').write_text(r.stdout,encoding='utf-8')
tree=ET.parse(reports/'junit.xml').getroot();suites=list(tree.iter('testsuite'))
stats={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
files={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.py') if '__pycache__' not in str(p)}
result={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),'platform':platform.platform(),'command':'python -m pytest -q -m "not browser and not external"','exit_code':r.returncode,'junit':stats,'source_sha256':files}
(reports/'execution.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(r.stdout);print(json.dumps(result,indent=2));sys.exit(r.returncode)
