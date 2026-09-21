import logging
from pathlib import Path
from datetime import date
from collections import defaultdict

from . import config
from .database import get_connection, count_by_date, get_discovery_methods

log = logging.getLogger("harritpib.reconcile")


def run_reconciliation():
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()

    all_dates = conn.execute(
        "SELECT DISTINCT publication_date FROM releases WHERE publication_date != '' ORDER BY publication_date"
    ).fetchall()

    rows = conn.execute(
        "SELECT publication_date, COUNT(*) as cnt FROM releases "
        "WHERE status='valid' AND publication_date != '' "
        "GROUP BY publication_date ORDER BY publication_date"
    ).fetchall()
    date_counts = {r["publication_date"]: r["cnt"] for r in rows}

    method_counts = defaultdict(lambda: defaultdict(int))
    discovery_rows = conn.execute(
        "SELECT r.publication_date, d.method, COUNT(*) as cnt "
        "FROM releases r JOIN discovery d ON r.prid = d.prid "
        "WHERE r.status='valid' AND r.publication_date != '' "
        "GROUP BY r.publication_date, d.method"
    ).fetchall()
    for r in discovery_rows:
        method_counts[r["publication_date"]][r["method"]] = r["cnt"]

    csv_path = config.REPORTS_DIR / "reconciliation.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("date,validated_count,methods,status\n")
        for row in all_dates:
            d = row["publication_date"]
            vc = date_counts.get(d, 0)
            methods = method_counts.get(d, {})
            method_str = "; ".join(f"{k}={v}" for k, v in sorted(methods.items()))
            status = "OK" if vc > 0 else "MISSING"
            f.write(f"{d},{vc},\"{method_str}\",{status}\n")

    log.info(f"Reconciliation report: {csv_path}")
    total_dates = len(all_dates)
    dates_with_releases = len([r for r in all_dates if date_counts.get(r["publication_date"], 0) > 0])
    log.info(f"Total dates: {total_dates}, with releases: {dates_with_releases}")
    conn.close()
