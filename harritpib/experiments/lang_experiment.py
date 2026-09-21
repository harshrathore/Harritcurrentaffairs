"""P2: Language URL Parameter Experiment.

Test 100 known PRIDs × 4 URL combinations to determine if lang param selects English.
Records: HTTP status, title, date, detected language, content length, canonical URL.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import time
import json
import csv
import re
import hashlib
from pathlib import Path
from datetime import date
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

BASE = "https://www.pib.gov.in"
PAGE_URL = f"{BASE}/PressReleasePage.aspx"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"

# Known PRIDs from our previous crawl (English + non-English mix)
KNOWN_PRIDS = [
    2270007, 2270009, 2270016, 2270017, 2270019, 2270024, 2270026,
    2270030, 2270032, 2270035, 2270036, 2270037, 2270038, 2270042,
    2270043, 2270044, 2270045, 2270046, 2270051, 2270054, 2270056,
    2270060, 2270063, 2270068, 2270070, 2270074, 2270081, 2270084,
    2270088, 2270091, 2270095, 2270100, 2270110, 2270120, 2270130,
    2270140, 2270150, 2270160, 2270170, 2270180, 2270185, 2270190,
    2270200, 2270210, 2270220, 2270230, 2270240, 2270250, 2270260,
    2270270, 2270280, 2270290, 2270300, 2270310, 2270320, 2270330,
    2270340, 2270350, 2270360, 2270370, 2270380, 2270390, 2270400,
    2270406, 2270004, 2270012, 2270039, 2270050,
]

# Test these URL combos for each PRID
LANG_COMBOS = [
    {"reg": 48, "lang": 1, "label": "reg48_lang1"},
    {"reg": 48, "lang": 2, "label": "reg48_lang2"},
    {"reg": 3,  "lang": 1, "label": "reg3_lang1"},
    {"reg": 3,  "lang": 2, "label": "reg3_lang2"},
]


def is_english_fast(text: str) -> bool:
    if not text:
        return False
    ascii_count = sum(1 for c in text if ord(c) < 128)
    return ascii_count / max(len(text), 1) > 0.7


def detect_language_from_text(text: str) -> str:
    if not text:
        return "empty"
    sample = text[:2000]
    latin = sum(1 for c in sample if 0x0041 <= ord(c) <= 0x007A or 0x0041 <= ord(c) <= 0x005A)
    devanagari = sum(1 for c in sample if 0x0900 <= ord(c) <= 0x097F)
    tamil = sum(1 for c in sample if 0x0B80 <= ord(c) <= 0x0BFF)
    total = max(len(sample), 1)
    if latin / total > 0.5:
        return "English"
    if devanagari / total > 0.3:
        return "Hindi"
    if tamil / total > 0.3:
        return "Tamil"
    return "Other"


def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    div = soup.select_one("div.event-heading-background")
    if div:
        return div.get_text(" ", strip=True)
    h2s = soup.select("div.innner-page-main-about-us-content-right-part h2")
    if len(h2s) >= 2:
        return h2s[1].get_text(" ", strip=True)
    return ""


def extract_date(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    date_div = soup.find(id="PrDateTime")
    if date_div:
        text = date_div.get_text(" ", strip=True)
        m = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", text)
        if m:
            return m.group(1)
    date_sub = soup.select_one("div.ReleaseDateSubHeaddateTime")
    if date_sub:
        text = date_sub.get_text(" ", strip=True)
        m = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", text)
        if m:
            return m.group(1)
    return ""


def run_experiment():
    output_dir = Path(__file__).parent / "data" / "PIB" / "harritpib"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "lang_experiment.csv"
    json_path = output_dir / "lang_experiment.json"

    session = requests.Session()
    session.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.pib.gov.in/",
    })

    results = []
    summary = defaultdict(lambda: {"total": 0, "english": 0, "found": 0, "empty": 0, "error": 0})
    lang_agreement = defaultdict(dict)  # prid -> {combo_label: lang_detected}

    total_requests = len(KNOWN_PRIDS) * len(LANG_COMBOS)
    print(f"Experiment: {len(KNOWN_PRIDS)} PRIDs x {len(LANG_COMBOS)} combos = {total_requests} requests")
    print(f"Starting at {time.strftime('%H:%M:%S')}...")

    start_time = time.time()

    for i, prid in enumerate(KNOWN_PRIDS):
        for combo in LANG_COMBOS:
            reg = combo["reg"]
            lang = combo["lang"]
            label = combo["label"]
            url = f"{PAGE_URL}?PRID={prid}&reg={reg}&lang={lang}"

            record = {
                "prid": prid,
                "reg": reg,
                "lang": lang,
                "label": label,
                "http_status": 0,
                "title": "",
                "date_raw": "",
                "detected_lang": "",
                "content_length": 0,
                "is_english": False,
                "error": "",
            }

            try:
                time.sleep(0.3)  # Rate limit
                resp = session.get(url, timeout=30)
                record["http_status"] = resp.status_code
                html = resp.text
                record["content_length"] = len(html)

                if resp.status_code == 200 and len(html) > 1000:
                    record["title"] = extract_title(html)
                    record["date_raw"] = extract_date(html)
                    body_text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
                    record["detected_lang"] = detect_language_from_text(body_text)
                    record["is_english"] = is_english_fast(record["title"] + " " + body_text[:500])
                else:
                    record["detected_lang"] = "empty/error"

                summary[label]["total"] += 1
                if record["is_english"]:
                    summary[label]["english"] += 1
                if record["http_status"] == 200 and record["content_length"] > 1000:
                    summary[label]["found"] += 1
                elif record["content_length"] < 100:
                    summary[label]["empty"] += 1
                if record["error"]:
                    summary[label]["error"] += 1

                lang_agreement[prid][label] = record["detected_lang"]

            except Exception as e:
                record["error"] = str(e)
                summary[label]["error"] += 1

            results.append(record)

        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) * len(LANG_COMBOS) / max(elapsed, 1)
            print(f"  Progress: {i+1}/{len(KNOWN_PRIDS)} PRIDs ({rate:.1f} req/s, {elapsed:.0f}s elapsed)")

    elapsed = time.time() - start_time
    print(f"\nCompleted in {elapsed:.0f}s ({total_requests/elapsed:.1f} req/s)")

    # Save CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"CSV: {csv_path}")

    # Save JSON
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"JSON: {json_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    for label, s in sorted(summary.items()):
        print(f"\n{label}:")
        print(f"  Total requests: {s['total']}")
        print(f"  Found (200 + >1KB): {s['found']}")
        print(f"  English detected: {s['english']}")
        print(f"  Empty/error: {s['empty']}")
        print(f"  Errors: {s['error']}")

    # Check lang=1 vs lang=2 consistency
    print(f"\n{'='*60}")
    print(f"LANGUAGE CONSISTENCY ANALYSIS")
    print(f"{'='*60}")

    agree_count = 0
    disagree_count = 0
    for prid, langs in lang_agreement.items():
        if "reg48_lang1" in langs and "reg48_lang2" in langs:
            l1 = langs["reg48_lang1"]
            l2 = langs["reg48_lang2"]
            if l1 == l2:
                agree_count += 1
            else:
                disagree_count += 1
                print(f"  PRID {prid}: lang1={l1}, lang2={l2}")

    print(f"\nreg48 lang1 vs lang2:")
    print(f"  Same language: {agree_count}")
    print(f"  Different language: {disagree_count}")

    # Check if lang=1 always produces English for known English PRIDs
    known_english = [2270007, 2270009, 2270016, 2270017, 2270019, 2270024, 2270026]
    print(f"\nKnown English PRIDs with lang=1:")
    for r in results:
        if r["prid"] in known_english and r["label"] == "reg48_lang1":
            status = "ENGLISH" if r["is_english"] else f"NOT ENGLISH ({r['detected_lang']})"
            print(f"  PRID {r['prid']}: {status} (title: {r['title'][:50]}...)")

    return results, summary


if __name__ == "__main__":
    run_experiment()
