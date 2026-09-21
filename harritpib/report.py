import logging
from datetime import date
from pathlib import Path
from collections import defaultdict

from . import config
from .database import get_connection, get_stats, count_by_date

log = logging.getLogger("harritpib.report")


def generate_report():
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stats = get_stats()
    by_date = count_by_date()
    conn = get_connection()

    method_counts = defaultdict(int)
    rows = conn.execute(
        "SELECT method, COUNT(*) as cnt FROM discovery GROUP BY method"
    ).fetchall()
    for r in rows:
        method_counts[r["method"]] = r["cnt"]

    ministry_counts = defaultdict(int)
    rows = conn.execute(
        "SELECT ministry, COUNT(*) as cnt FROM releases WHERE status='valid' "
        "AND ministry != '' GROUP BY ministry ORDER BY cnt DESC LIMIT 20"
    ).fetchall()
    for r in rows:
        ministry_counts[r["ministry"]] = r["cnt"]

    dates_with_releases = len(by_date)
    total_dates = 0
    if by_date:
        from datetime import datetime
        d1 = date.fromisoformat(min(by_date.keys()))
        d2 = date.fromisoformat(max(by_date.keys()))
        total_dates = (d2 - d1).days + 1

    report = f"""# PIB Historical Crawl Report

## Period
{min(by_date.keys()) if by_date else 'N/A'} to {max(by_date.keys()) if by_date else 'N/A'}

## Summary
| Metric | Value |
|--------|-------|
| Total PRIDs | {stats['total']} |
| Valid releases | {stats['valid']} |
| Pending | {stats['pending']} |
| Failed | {stats['failed']} |
| Dates with releases | {dates_with_releases} |
| Total calendar days | {total_dates} |

## Discovery Methods
| Method | Count |
|--------|-------|
"""
    for method, count in sorted(method_counts.items(), key=lambda x: -x[1]):
        report += f"| {method} | {count} |\n"

    report += "\n## Top Ministries\n| Ministry | Releases |\n|----------|----------|\n"
    for ministry, count in sorted(ministry_counts.items(), key=lambda x: -x[1]):
        report += f"| {ministry} | {count} |\n"

    report += "\n## Releases by Date\n| Date | Count |\n|------|-------|\n"
    for d, c in sorted(by_date.items()):
        report += f"| {d} | {c} |\n"

    path = config.REPORTS_DIR / "crawl_report.md"
    path.write_text(report, encoding="utf-8")
    log.info(f"Report generated: {path}")
    conn.close()
