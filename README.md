# ClearQuestion startup and MVP laboratory

**Subject:** Technological Entrepreneurship  
**Portfolio owner:** Aibyn Samat

This repository contains an executable demonstration, design or research artifacts, automated
checks and reproducible execution reports. It was prepared as new portfolio work in November 2026.

## Run

```sh
python -m venv .venv
# Activate .venv using your platform's normal command.
python -m pip install -r requirements-dev.txt
python app.py
python tools/evidence.py
```

Reports: [execution record](reports/execution.json), [test output](reports/test-output.txt).
[GitHub Actions](https://github.com/aahhaha/aitu-te-startup-lab/actions) runs the independent Linux checks.
The report records timestamps, environment, test counts and source hashes.

## Read the portfolio

[research/interview-findings.md](research/interview-findings.md)  [docs/business-plan.md](docs/business-plan.md)  [docs/HADI.md](docs/HADI.md)  [docs/pitch.md](docs/pitch.md)

[Preparation and attribution](PROVENANCE.md). Do not publish private keys, real student records or raw interview recordings.

## Preserved CI evidence

[Successful verification run](https://github.com/aahhaha/aitu-te-startup-lab/actions/runs/43629521740) tested source commit `5884b7831ee744047b4e7b0f04cd54d3feeaaed5`.
[Preserved reports](evidence/43629521740) include machine-readable results and generated artifacts.
The later evidence-only commit does not change the tested implementation.
