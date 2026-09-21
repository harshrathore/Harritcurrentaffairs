import logging
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from . import config
from .database import init_db, get_stats, get_valid_prids, count_by_date, get_discovery_methods
from .http_client import HttpClient
from .engines import DateEngine, MinistryEngine, PRIDEngine, ArchiveEngine, InternalEngine

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("harritpib")


def cmd_crawl(args):
    init_db()
    http = HttpClient()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    region = args.reg
    lang = args.lang

    log.info(f"PIB Historical Crawl: {start} -> {end} (reg={region}, lang={lang})")

    date_engine = DateEngine(http, region, lang)
    ministry_engine = MinistryEngine(http, region, lang)
    prid_engine = PRIDEngine(http, region, lang)

    log.info("=== Phase 1: PRID Range Probing ===")
    probe_start = config.PRID_RANGE_START
    probe_end = config.PRID_RANGE_END

    log.info(f"Probing PRID range {probe_start} to {probe_end}")
    prid_engine.probe_range(probe_start, probe_end, start, end)

    log.info("=== Phase 2: Validation ===")
    validate_all_pending(http, region, lang)

    log.info("=== Done ===")
    stats = get_stats()
    log.info(f"Results: {stats}")


def cmd_discover_dates(args):
    init_db()
    http = HttpClient()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    engine = DateEngine(http, args.reg, args.lang)
    results = engine.discover_range(start, end)
    for d, count in sorted(results.items()):
        log.info(f"{d}: {count} releases")


def cmd_discover_ministries(args):
    init_db()
    http = HttpClient()
    target = date.fromisoformat(args.start)
    engine = MinistryEngine(http, args.reg, args.lang)
    results = engine.discover_date(target, max_ministries=None)
    for name, count in sorted(results.items(), key=lambda x: -x[1]):
        if count > 0:
            log.info(f"{name}: {count}")


def cmd_discover_prids(args):
    init_db()
    http = HttpClient()
    start_prid = args.start_prid
    end_prid = args.end_prid
    start_date = date.fromisoformat(args.start_date) if args.start_date else None
    end_date = date.fromisoformat(args.end_date) if args.end_date else None
    engine = PRIDEngine(http, args.reg, args.lang)
    result = engine.probe_range(start_prid, end_prid, start_date, end_date)
    log.info(f"PRID probe: {result}")


def cmd_validate(args):
    init_db()
    http = HttpClient()
    validate_all_pending(http, args.reg, args.lang)


def validate_all_pending(http: HttpClient, region: int, lang: int):
    from .database import get_pending_releases, get_release, upsert_release, add_discovery
    from .parsers import parse_release_page
    pending = get_pending_releases(limit=10000)
    log.info(f"Validating {len(pending)} pending releases...")

    for i, prid in enumerate(pending):
        url = (
            f"{config.RELEASE_SHARE_URL}?PRID={prid}"
            f"&reg={region}&lang={lang}"
        )
        html = http.get(url, use_cache=False)
        if not html or len(html) < 500:
            upsert_release(prid, status="failed")
            continue

        body = html.lower()
        if "release id" not in body and "press release" not in body:
            upsert_release(prid, status="failed")
            continue

        parsed = parse_release_page(html, prid)
        upsert_release(
            prid,
            title=parsed.get("title", ""),
            publication_date=parsed.get("publication_date", ""),
            publication_time=parsed.get("publication_time", ""),
            ministry=parsed.get("ministry", ""),
            full_text=parsed.get("full_text", ""),
            location=parsed.get("location", ""),
            canonical_url=parsed.get("canonical_url", ""),
            successful_url=url,
            page_variant="Pressreleaseshare",
            status="valid",
        )
        add_discovery(prid, "direct_validation", source_url=url)

        if (i + 1) % 100 == 0:
            log.info(f"Validated {i + 1}/{len(pending)}")

    log.info(f"Validation complete: {len(pending)} processed")


def cmd_retry_failed(args):
    init_db()
    http = HttpClient()
    from .database import get_connection
    conn = get_connection()
    conn.execute("UPDATE releases SET status='pending' WHERE status='failed'")
    conn.commit()
    conn.close()
    validate_all_pending(http, args.reg, args.lang)


def cmd_reconcile(args):
    init_db()
    from .reconcile import run_reconciliation
    run_reconciliation()


def cmd_export(args):
    init_db()
    from .export import export_all
    export_all(args.format)


def cmd_report(args):
    init_db()
    from .report import generate_report
    generate_report()


def cmd_stats(args):
    init_db()
    stats = get_stats()
    by_date = count_by_date()
    print("\n=== PIB Historical Database Stats ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"\n  Date range: {min(by_date.keys()) if by_date else 'N/A'} to {max(by_date.keys()) if by_date else 'N/A'}")
    print(f"  Dates with releases: {len(by_date)}")
    if by_date:
        print("\n  Top 10 dates by article count:")
        for d, c in sorted(by_date.items(), key=lambda x: -x[1])[:10]:
            print(f"    {d}: {c}")


def cmd_fast(args):
    from .fast_crawl import run_fast_crawl
    run_fast_crawl(
        start_prid=args.start_prid,
        end_prid=args.end_prid,
        start_date_str=args.start_date,
        end_date_str=args.end_date,
        max_workers=args.workers,
    )


def main():
    parser = argparse.ArgumentParser(
        prog="harritpib",
        description="PIB Historical Archive Extraction System",
    )
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("crawl", help="Full crawl (legacy)")
    p.add_argument("--start", default="2026-06-01")
    p.add_argument("--end", default=date.today().isoformat())
    p.add_argument("--reg", type=int, default=48)
    p.add_argument("--lang", type=int, default=1)

    p = sub.add_parser("fast", help="Fast async crawl")
    p.add_argument("--start-prid", type=int, default=None)
    p.add_argument("--end-prid", type=int, default=None)
    p.add_argument("--start-date", default=None)
    p.add_argument("--end-date", default=None)
    p.add_argument("--workers", type=int, default=10)

    p = sub.add_parser("discover-dates", help="Date enumeration")
    p.add_argument("--start", default="2026-06-01")
    p.add_argument("--end", default=date.today().isoformat())
    p.add_argument("--reg", type=int, default=48)
    p.add_argument("--lang", type=int, default=1)

    p = sub.add_parser("discover-ministries", help="Ministry enumeration")
    p.add_argument("--start", default="2026-06-01")
    p.add_argument("--reg", type=int, default=48)
    p.add_argument("--lang", type=int, default=1)

    p = sub.add_parser("discover-prids", help="PRID range probing")
    p.add_argument("--start-prid", type=int, required=True)
    p.add_argument("--end-prid", type=int, required=True)
    p.add_argument("--start-date", default=None)
    p.add_argument("--end-date", default=None)
    p.add_argument("--reg", type=int, default=48)
    p.add_argument("--lang", type=int, default=1)

    p = sub.add_parser("validate", help="Validate pending releases")
    p.add_argument("--reg", type=int, default=48)
    p.add_argument("--lang", type=int, default=1)

    p = sub.add_parser("retry-failed", help="Retry failed releases")
    p.add_argument("--reg", type=int, default=48)
    p.add_argument("--lang", type=int, default=1)

    p = sub.add_parser("reconcile", help="Reconcile discovery")

    p = sub.add_parser("export", help="Export data")
    p.add_argument("--format", choices=["xlsx", "json", "csv", "all"], default="all")

    p = sub.add_parser("report", help="Generate report")
    p = sub.add_parser("stats", help="Show stats")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cmd_map = {
        "crawl": cmd_crawl,
        "fast": cmd_fast,
        "discover-dates": cmd_discover_dates,
        "discover-ministries": cmd_discover_ministries,
        "discover-prids": cmd_discover_prids,
        "validate": cmd_validate,
        "retry-failed": cmd_retry_failed,
        "reconcile": cmd_reconcile,
        "export": cmd_export,
        "report": cmd_report,
        "stats": cmd_stats,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
