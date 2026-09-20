# Naukri Azure Data Engineer Auto-Apply

A separate local Playwright worker for Naukri applications.

## Safety / operating rules

- Uses a visible Chromium browser and your own logged-in Naukri session.
- Never stores your Naukri password in the repository.
- Never bypasses CAPTCHA, OTP, login checks, anti-bot controls, or other access controls. If one appears, the run pauses.
- Only applies to jobs matching the configured Azure Data Engineer profile.
- Skips jobs with unanswered/unknown screening questions rather than guessing.
- Keeps a local application log and daily cap.
- Start with DRY_RUN=true and inspect the queue before enabling submission.

## Run

```bash
cd naukri-autoapply
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python naukri_agent.py --login
python naukri_agent.py --dry-run
python naukri_agent.py
```

The first login opens a visible browser. Log in yourself; the session is stored under `./naukri-profile`.

## Configuration

Edit `config.json` for locations, keywords, minimum score, maximum applications per run/day, and dry-run mode.

The worker targets Azure Data Engineer / Databricks / PySpark / ADF / ADLS / Synapse roles and your 5.2 YOE profile.

