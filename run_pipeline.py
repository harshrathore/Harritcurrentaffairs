# =========================================================
# RUN PIPELINE (LOCAL PYTHON)
# Replaces Google Apps Script runPIBPosterSystem()
# Merges PIB + GKToday + Vision IAS + Insights IAS + Drishti IAS
# Dedups locally, filters by age, sends to Telegram
# =========================================================

import sys
import os
import json
import re
import time
from datetime import datetime, timedelta

try:
    from current_affairs_scraper import (
        scrape_gktoday,
        scrape_visionias,
        scrape_insightsonindia,
        scrape_drishtiias,
        load_database as load_ca_database,
    )
except Exception as e:
    print("WARN: could not import current_affairs_scraper functions:", e)
    scrape_gktoday = scrape_visionias = scrape_insightsonindia = scrape_drishtiias = None
    load_ca_database = None

import telegram_sender

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "pipeline_config.json")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def log(msg, config):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(config.get("log_path", ""), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ---------------------------------------------------------
# Categorization (replaces Apps Script analysis)
# ---------------------------------------------------------

DOMAIN_KEYWORDS = {
    "DEFENCE": ["defence", "defense", "military", "army", "navy", "air force", "missile", "border", "security", "armed"],
    "ECONOMY": ["economy", "gdp", "inflation", "rbi", "budget", "tax", "fiscal", "bank", "trade", "export", "investment"],
    "ENVIRONMENT": ["environment", "climate", "forest", "wildlife", "pollution", "biodiversity", "conservation", "ecology", "wetland"],
    "SCIENCE": ["science", "technology", "isro", "space", "research", "ai", "innovation", "satellite", "quantum", "biotech"],
    "POLITY": ["constitution", "parliament", "supreme court", "bill", "act", "ministry", "government", "scheme", "policy", "cabinet"],
    "INTERNATIONAL": ["international", "un ", "bilateral", "treaty", "foreign", "summit", "multilateral", "diplomacy"],
    "SOCIAL": ["education", "health", "welfare", "scheme", "women", "child", "rural", "poverty", "sanitation", "nutrition"],
    "AGRICULTURE": ["agriculture", "farm", "crop", "farmer", "food", "fishery", "livestock", "msme"],
}

EXAM_KEYWORDS = {
    "UPSC": ["upsc", "ias", "civil services", "prelims", "mains"],
    "RAS": ["ras", "rpsc", "rajasthan"],
    "SSC": ["ssc", "cgl", "chsl"],
    "REET": ["reet", "teacher eligibility"],
}


def categorize(text):
    text_l = (text or "").lower()
    domain = "GENERAL"
    best = 0
    for dom, kws in DOMAIN_KEYWORDS.items():
        score = sum(1 for k in kws if k in text_l)
        if score > best:
            best = score
            domain = dom
    exams = []
    for ex, kws in EXAM_KEYWORDS.items():
        if any(k in text_l for k in kws):
            exams.append(ex)
    if not exams:
        exams = ["GENERAL"]
    return domain, exams


def normalize_pib(db):
    out = []
    for prid, item in db.items():
        content = item.get("content", "") or ""
        out.append({
            "id": "PIB_" + str(prid),
            "source": "PIB",
            "title": item.get("title", ""),
            "description": content,
            "link": item.get("article_url") or item.get("url") or "",
            "date": item.get("date", ""),
            "ministry": item.get("ministry", ""),
        })
    return out


def normalize_ca(db):
    out = []
    for aid, item in db.items():
        out.append({
            "id": str(aid),
            "source": item.get("source", "Unknown"),
            "title": item.get("title", ""),
            "description": item.get("content") or item.get("description") or "",
            "link": item.get("link") or item.get("url") or "",
            "date": item.get("date", ""),
            "ministry": "",
        })
    return out


def parse_date(d):
    """Parse dates from any source format robustly.
    Handles ISO, PIB (YYYY-MM-DD), GKToday/Insights text dates,
    RSS RFC-822, and falls back to regex extraction."""
    if not d:
        return None
    d = d.strip()

    formats = [
        # ISO variants
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y/%m/%d",
        # Text dates
        "%d %B %Y",          # 28 August 2026
        "%d %b %Y",          # 28 Aug 2026
        "%B %d, %Y",         # August 28, 2026
        "%b %d, %Y",         # Aug 28, 2026
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%B-%Y",
        # RSS / RFC-822
        "%a, %d %b %Y %H:%M:%S %z",   # Mon, 28 Aug 2026 00:00:00 +0000
        "%a, %d %b %Y %H:%M:%S",      # Mon, 28 Aug 2026 00:00:00
        "%a, %d %b %Y",               # Mon, 28 Aug 2026
        # with time
        "%d %B %Y %H:%M:%S",
        "%d %b %Y %H:%M",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(d, fmt)
        except Exception:
            continue

    # ---- Regex fallbacks for embedded / unusual formats ----
    # ISO date (optionally with time)
    m = re.search(r"(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}(?::\d{2})?))?", d)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d")
        except Exception:
            pass

    # 28 August 2026 / 28 Aug 2026
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", d)
    if m:
        for f in ("%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", f)
            except Exception:
                pass

    # August 28, 2026 / Aug 28, 2026
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", d)
    if m:
        for f in ("%B %d %Y", "%b %d %Y"):
            try:
                return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", f)
            except Exception:
                pass

    # DD/MM/YYYY or MM/DD/YYYY
    m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", d)
    if m:
        for f in ("%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(f"{m.group(1)}/{m.group(2)}/{m.group(3)}", f)
            except Exception:
                pass

    return None


def extract_key_points(text, n=3):
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text.replace("\n", " ").strip())
    points = []
    for s in sentences:
        s = s.strip()
        if len(s) > 20 and len(s) < 250:
            points.append(s)
        if len(points) >= n:
            break
    return points


def load_dedup(config):
    path = config.get("dedup_store_path", "")
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_dedup(store, config):
    path = config.get("dedup_store_path", "")
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("DEDUP SAVE ERROR:", e)


def main():
    config = load_config()
    log("==========================================", config)
    log("LOCAL PIPELINE STARTED (dry_run=%s)" % config.get("dry_run", True), config)

    # 1. Load PIB
    pib = []
    try:
        with open(config["pib_database_path"], encoding="utf-8") as f:
            pib = normalize_pib(json.load(f))
        log("PIB loaded: %d articles" % len(pib), config)
    except Exception as e:
        log("PIB LOAD ERROR: %s" % e, config)

    # 2. Load / scrape current affairs
    ca = []
    if config.get("re_scrape") and load_ca_database:
        log("Re-scraping current affairs sources...", config)
        for fn in (scrape_gktoday, scrape_visionias, scrape_insightsonindia, scrape_drishtiias):
            if fn is None:
                continue
            try:
                ca.extend(fn())
                time.sleep(1)
            except Exception as e:
                log("SCRAPE ERROR: %s" % e, config)
    else:
        try:
            with open(config["ca_database_path"], encoding="utf-8") as f:
                ca = normalize_ca(json.load(f))
            log("Current affairs loaded: %d articles" % len(ca), config)
        except Exception as e:
            log("CA LOAD ERROR: %s" % e, config)

    # 3. Merge
    all_articles = pib + ca
    log("Total merged: %d articles" % len(all_articles), config)

    # 4. Dedup + age filter
    dedup = load_dedup(config)
    cutoff = datetime.now() - timedelta(hours=config.get("max_article_age_hours", 336))
    now = datetime.now()

    per_source = {}
    max_per_source = config.get("max_articles_per_source", 0)
    max_total = config.get("max_articles_total", 0)

    sent = 0
    skipped_dedup = 0
    skipped_stale = 0
    failed = 0

    for art in all_articles:
        if max_total and sent >= max_total:
            break
        aid = art.get("id", "")
        # Dedup
        if aid in dedup:
            skipped_dedup += 1
            continue
        # Age
        dt = parse_date(art.get("date", ""))
        if dt is None:
            dt = now
        if dt < cutoff:
            skipped_stale += 1
            continue
        # Per-source cap (0 = unlimited)
        src = art.get("source", "Unknown")
        per_source[src] = per_source.get(src, 0)
        if max_per_source and per_source[src] >= max_per_source:
            continue

        domain, exams = categorize(art.get("title", "") + " " + (art.get("ministry", "")))
        analysis = {
            "exams": exams,
            "source": src,
            "domain": domain,
            "link": art.get("link", ""),
        }
        key_points = extract_key_points(art.get("description", ""), 3)

        per_source[src] += 1

        if config.get("dry_run", True):
            log("[DRY] WOULD SEND | %s | %s | %s" % (src, domain, art.get("title", "")[:60]), config)
            sent += 1
            continue

        result = telegram_sender.send_text_to_telegram(
            art.get("title", ""), art.get("description", ""), analysis, key_points, config
        )
        if result["success"]:
            log("SENT | %s | %s | %s" % (src, domain, art.get("title", "")[:60]), config)
            dedup[aid] = now.strftime("%Y-%m-%d %H:%M:%S")
            save_dedup(dedup, config)  # incremental save -> resumable across runs
            sent += 1
        else:
            log("FAILED | %s | %s" % (art.get("title", "")[:60], result["message"]), config)
            failed += 1
        time.sleep(1)

    save_dedup(dedup, config)
    log("==========================================", config)
    log("RUN COMPLETED", config)
    log("SENT: %d | SKIPPED_DEDUP: %d | SKIPPED_STALE: %d | FAILED: %d" % (
        sent, skipped_dedup, skipped_stale, failed), config)
    log("==========================================", config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nPIPELINE STOPPED BY USER.")
    except Exception as e:
        print("\nFATAL ERROR:", e)
