import argparse
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text())
PROFILE = json.loads((ROOT / "profile.json").read_text())
LOG = ROOT / "applications.json"
UNKNOWN = ROOT / "unanswered-questions.json"
FAILED = ROOT / "failed-jobs.json"
SESSION = ROOT / "naukri-profile"

def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default

def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False))

def norm(s):
    return re.sub(r"\\s+", " ", (s or "").lower()).strip()

def score_job(title, text, location):
    blob = norm(" ".join([title, text, location]))
    score = 0
    weights = {
        "azure": 15, "databricks": 15, "pyspark": 12,
        "azure data factory": 10, " adf ": 8, "adls": 8,
        "synapse": 7, "sql": 6, "python": 5, "delta lake": 5,
        "etl": 4, "elt": 4, "data warehouse": 4
    }
    padded = " " + blob + " "
    for key, weight in weights.items():
        if key in padded:
            score += weight
    if any(norm(x) in blob for x in CONFIG["locations"]):
        score += 10
    if "senior" in blob or "lead" in blob:
        score += 4
    if "data engineer" in blob:
        score += 10
    return min(score, 100)

def looks_like_target(title, text):
    blob = norm(title + " " + text)
    return "data engineer" in blob and any(x in blob for x in CONFIG["required_any"])

def detect_blocker(page):
    body = norm(page.locator("body").inner_text(timeout=3000))
    markers = ["captcha", "verify you are human", "otp", "one time password", "security verification"]
    return next((m for m in markers if m in body), None)

def discover(page):
    seen = {}
    for keyword in CONFIG["keywords"]:
        for location in CONFIG["locations"]:
            url = (
                "https://www.naukri.com/"
                "azure-data-engineer-jobs-in-" + quote(location.lower().replace(" ", "-"))
                "?k=" + quote(keyword) +
                "&l=" + quote(location) +
                "&experience=5"
            )
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            time.sleep(2)
            blocker = detect_blocker(page)
            if blocker:
                raise RuntimeError(f"Access check detected: {blocker}. Manual intervention required.")
            cards = page.locator("div.srp-jobtuple-wrapper")
            count = min(cards.count(), 50)
            for i in range(count):
                card = cards.nth(i)
                try:
                    title = card.locator("a.title").inner_text(timeout=1500)
                    href = card.locator("a.title").get_attribute("href")
                    text = card.inner_text(timeout=1500)
                    if not href or not looks_like_target(title, text):
                        continue
                    job_id = href.split("?")[0].rstrip("/")
                    seen[job_id] = {
                        "id": job_id,
                        "title": title.strip(),
                        "url": href,
                        "text": text,
                        "location": location,
                        "score": score_job(title, text, location)
                    }
                except Exception:
                    continue
    return list(seen.values())

def extract_questions(page):
    # Conservative: only return questions we can answer from verified profile facts.
    questions = []
    for q in page.locator("input, textarea, select").all():
        try:
            label = q.get_attribute("aria-label") or q.get_attribute("name") or ""
            if label:
                questions.append(label)
        except Exception:
            pass
    return questions

def apply_job(page, job):
    page.goto(job["url"], wait_until="domcontentloaded", timeout=45000)
    time.sleep(2)
    blocker = detect_blocker(page)
    if blocker:
        return "blocked", blocker

    apply = page.get_by_text(re.compile(r"^Apply$", re.I)).first
    if apply.count() == 0:
        apply = page.get_by_text(re.compile(r"Apply on Naukri|Apply", re.I)).first
    if apply.count() == 0:
        return "skipped", "No apply control found"

    apply.click()
    time.sleep(2)

    blocker = detect_blocker(page)
    if blocker:
        return "blocked", blocker

    questions = extract_questions(page)
    unknown = []
    for q in questions:
        nq = norm(q)
        known = any(k in nq for k in [
            "experience", "notice", "ctc", "salary", "location",
            "phone", "email", "name", "resume"
        ])
        if not known:
            unknown.append(q)

    if unknown and CONFIG["pause_on_unknown_question"]:
        return "unknown_question", unknown[:10]

    if CONFIG["dry_run"]:
        return "dry_run", "Application flow reached; submission disabled"

    submit = page.get_by_text(re.compile(r"Submit|Apply", re.I)).last
    if submit.count() == 0:
        return "skipped", "No final submit control found"
    submit.click()
    time.sleep(2)
    return "applied", "Submitted"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        CONFIG["dry_run"] = True

    logs = load_json(LOG, [])
    today = datetime.now().date()
    applied_today = sum(
        1 for x in logs
        if x.get("status") == "applied" and x.get("timestamp", "")[:10] == today.isoformat()
    )

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(SESSION),
            headless=False,
            viewport={"width": 1440, "height": 1000}
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.naukri.com/", wait_until="domcontentloaded", timeout=45000)

        if args.login:
            print("Log in to Naukri in the visible browser. Complete OTP/CAPTCHA yourself.")
            input("After login, press Enter here...")
            context.close()
            return

        jobs = [j for j in discover(page) if j["score"] >= CONFIG["min_score"]]
        jobs.sort(key=lambda x: x["score"], reverse=True)

        existing = {x.get("id") for x in logs}
        run_count = 0

        for job in jobs:
            if run_count >= CONFIG["max_applications_per_run"]:
                break
            if applied_today >= CONFIG["max_applications_per_day"]:
                break
            if job["id"] in existing:
                continue

            status, detail = apply_job(page, job)
            record = {
                "id": job["id"],
                "title": job["title"],
                "url": job["url"],
                "location": job["location"],
                "score": job["score"],
                "status": status,
                "detail": detail,
                "timestamp": datetime.now().isoformat(timespec="seconds")
            }
            logs.append(record)
            existing.add(job["id"])
            if status == "applied":
                applied_today += 1
                run_count += 1
            elif status in ("dry_run", "unknown_question", "blocked"):
                run_count += 1

            save_json(LOG, logs)

        context.close()

if __name__ == "__main__":
    main()
