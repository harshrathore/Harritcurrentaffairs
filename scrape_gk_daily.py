"""scrape_gk_daily.py - backfill GKToday articles from daily archive pages.
Usage: python scrape_gk_daily.py 2026-10-02 2026-10-26
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
DATA_DIR = Path(os.environ.get("HARRIT_DATA_DIR") or
                (Path(__file__).resolve().parent.parent / "data" / "PIB"))
DB = DATA_DIR / "current_affairs_database.json"


def log(m):
    print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


def parse_day(day):
    url = f"https://www.gktoday.in/{day.year}/{day.month:02d}/{day.day:02d}/"
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for item in soup.select(".home-post-item"):
        a = item.select_one("h3 a")
        if not a:
            continue
        title, link = a.get_text(strip=True), a.get("href", "")
        cat_tag = item.select_one(".home-post-data-meta a")
        cat = cat_tag.get_text(strip=True) if cat_tag else ""
        out.append((title, link, cat))
    return out


def fetch_content(link):
    try:
        r = requests.get(link, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return ""
        s = BeautifulSoup(r.text, "html.parser")
        div = s.select_one(".content-area")
        if not div:
            return ""
        for t in div.select("script, style, .related-articles, .social-share, "
                            ".adsbygoogle, .breadcrumb, .post-meta, "
                            ".gktoday-share-box, .a2a_kit"):
            t.decompose()
        return div.get_text(separator=" ", strip=True)[:50000]
    except Exception as e:
        log(f"  content fail {link}: {e}")
        return ""


def main():
    start = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    end = datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
    db = json.load(open(DB, encoding="utf-8"))
    log(f"DB has {len(db)} articles")
    added = skipped = 0
    day = start
    while day <= end:
        daystr = day.isoformat()
        have = sum(1 for v in db.values() if (v.get("date") or "")[:10] == daystr)
        if have >= 5:
            log(f"{daystr}: already {have} articles, skip")
            day += timedelta(days=1)
            continue
        items = parse_day(day)
        log(f"{daystr}: archive lists {len(items)} posts (DB had {have})")
        for title, link, cat in items:
            aid = "GKT_" + (link.rstrip('/').split('/')[-1])
            if aid in db:
                skipped += 1
                continue
            content = fetch_content(link)
            time.sleep(0.25)
            db[aid] = {
                "id": aid,
                "source": "GKToday",
                "title": title,
                "url": link,
                "date": f"{daystr}T00:00:00",
                "category": cat,
                "content": content,
                "collected_at": datetime.now().isoformat(),
            }
            added += 1
        json.dump(db, open(DB, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        day += timedelta(days=1)
        time.sleep(0.5)
    log(f"DONE added={added} skipped={skipped} total={len(db)}")
    json.dump(db, open(DB, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
