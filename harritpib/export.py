import json
import csv
import logging
from pathlib import Path

from . import config
from .database import get_connection, get_discovery_methods

log = logging.getLogger("harritpib.export")


def export_all(fmt: str = "all"):
    config.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM releases WHERE status='valid' ORDER BY publication_date, prid"
    ).fetchall()
    conn.close()

    log.info(f"Exporting {len(rows)} valid releases...")

    if fmt in ("xlsx", "all"):
        export_xlsx(rows)
    if fmt in ("json", "all"):
        export_json(rows)
    if fmt in ("csv", "all"):
        export_csv(rows)


def export_json(rows):
    path = config.EXPORTS_DIR / "PIB_2026.json"
    data = []
    for r in rows:
        methods = get_discovery_methods(r["prid"])
        data.append({
            "PRID": r["prid"],
            "Publication Date": r["publication_date"],
            "Publication Time": r["publication_time"],
            "Ministry": r["ministry"],
            "Title": r["title"],
            "Location": r["location"],
            "URL": r["canonical_url"],
            "Full Text": r["full_text"],
            "Content Hash": r["content_hash"],
            "Discovery Methods": methods,
            "Validation Status": r["status"],
        })
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"JSON export: {path}")


def export_csv(rows):
    path = config.EXPORTS_DIR / "PIB_2026.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "PRID", "Publication Date", "Publication Time", "Ministry",
            "Title", "Location", "URL", "Content Hash", "Discovery Methods", "Status"
        ])
        for r in rows:
            methods = get_discovery_methods(r["prid"])
            writer.writerow([
                r["prid"], r["publication_date"], r["publication_time"],
                r["ministry"], r["title"], r["location"], r["canonical_url"],
                r["content_hash"], ";".join(methods), r["status"],
            ])
    log.info(f"CSV export: {path}")


def export_xlsx(rows):
    path = config.EXPORTS_DIR / "PIB_2026.xlsx"
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "PIB Releases"
        headers = [
            "PRID", "Publication Date", "Publication Time", "Ministry",
            "Title", "Location", "URL", "Content Hash", "Discovery Methods", "Status"
        ]
        ws.append(headers)
        for r in rows:
            methods = get_discovery_methods(r["prid"])
            text = r["full_text"] or ""
            ws.append([
                r["prid"], r["publication_date"], r["publication_time"],
                r["ministry"], r["title"][:200], r["location"], r["canonical_url"],
                r["content_hash"], ";".join(methods), r["status"],
            ])
        wb.save(str(path))
        log.info(f"XLSX export: {path}")
    except ImportError:
        log.warning("openpyxl not installed, skipping XLSX export. Install with: pip install openpyxl")
