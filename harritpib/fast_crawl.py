"""
HarritPIB Fast Crawler — Optimized single-pass async PRID crawler.

Architecture:
  producer → PRID candidates
  workers  → N concurrent httpx fetch + parse + local validate
  db_writer → single-thread SQLite writes
  stats    → real-time benchmark

Implements: P1, P7, P8, P9, P10, P11, P12, P13, P15
"""
import asyncio
import hashlib
import json
import logging
import re
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import httpx

from . import config

log = logging.getLogger("harritpib.fast")


@dataclass
class Release:
    prid: int = 0
    title: str = ""
    publication_date: str = ""
    publication_time: str = ""
    ministry: str = ""
    department: str = ""
    location: str = ""
    language: str = ""
    region: str = ""
    canonical_url: str = ""
    full_text: str = ""
    content_hash: str = ""
    page_variant: str = ""
    is_english: bool = False
    status: str = "pending"
    raw_html_path: str = ""
    http_status: int = 0
    content_length: int = 0
    error: str = ""


@dataclass
class CrawlStats:
    total_candidates: int = 0
    completed: int = 0
    english_found: int = 0
    non_english: int = 0
    empty_pages: int = 0
    http_errors: int = 0
    already_valid: int = 0
    requests_made: int = 0
    start_time: float = 0.0
    errors_by_type: dict = field(default_factory=lambda: defaultdict(int))

    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time if self.start_time else 0

    @property
    def requests_per_sec(self) -> float:
        return self.requests_made / max(self.elapsed, 0.001)

    @property
    def estimated_remaining(self) -> float:
        if self.requests_per_sec <= 0:
            return 0
        remaining = self.total_candidates - self.completed
        return remaining / self.requests_per_sec

    def report(self) -> str:
        elapsed_m = self.elapsed / 60
        remain_m = self.estimated_remaining / 60
        return (
            f"\n{'='*60}\n"
            f"PIB FAST CRAWL PERFORMANCE\n"
            f"{'='*60}\n"
            f"  Candidates:       {self.total_candidates:,}\n"
            f"  Completed:        {self.completed:,}\n"
            f"  English found:    {self.english_found:,}\n"
            f"  Non-English:      {self.non_english:,}\n"
            f"  Empty pages:      {self.empty_pages:,}\n"
            f"  HTTP errors:      {self.http_errors:,}\n"
            f"  Already valid:    {self.already_valid:,}\n"
            f"  Requests/sec:     {self.requests_per_sec:.1f}\n"
            f"  Elapsed:          {elapsed_m:.1f}m\n"
            f"  Est. remaining:   {remain_m:.1f}m\n"
            f"{'='*60}"
        )


# ---------------------------------------------------------------------------
# P11: Single-pass parser
# ---------------------------------------------------------------------------

def _parse_date_str(s: str) -> Optional[date]:
    s = s.strip()
    for fmt in ["%d %b %Y", "%d %B %Y", "%d-%m-%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def is_english_text(text: str) -> bool:
    if not text:
        return False
    sample = text[:3000]
    latin = sum(1 for c in sample if 0x0020 <= ord(c) <= 0x007E)
    total = max(len(sample), 1)
    return latin / total > 0.7


def parse_release_single_pass(html: str, prid: int) -> Release:
    """Single-pass parser: extract ALL fields from one HTML response."""
    from bs4 import BeautifulSoup

    release = Release(prid=prid)
    release.content_length = len(html)

    if len(html) < 1000:
        release.status = "empty_page"
        return release

    body_lower = html.lower()
    if "release id" not in body_lower and "posted on" not in body_lower:
        release.status = "not_release"
        return release

    soup = BeautifulSoup(html, "html.parser")

    # Date + time + location from PrDateTime or ReleaseDateSubHeaddateTime
    date_div = soup.find(id="PrDateTime")
    if not date_div:
        date_div = soup.select_one("div.ReleaseDateSubHeaddateTime")
    if date_div:
        dt_text = date_div.get_text(" ", strip=True)
        m = re.search(
            r"Posted\s+On\s*:\s*(\d{1,2}\s+\w+\s+\d{4})\s+(\d{1,2}:\d{2}\s*[APap][Mm])",
            dt_text, re.IGNORECASE,
        )
        if m:
            d = _parse_date_str(m.group(1))
            release.publication_date = d.isoformat() if d else ""
            release.publication_time = m.group(2).strip()
        else:
            m2 = re.search(r"Posted\s+On\s*:\s*(\d{1,2}\s+\w+\s+\d{4})", dt_text, re.IGNORECASE)
            if m2:
                d = _parse_date_str(m2.group(1))
                release.publication_date = d.isoformat() if d else ""
        loc_m = re.search(r"by\s+PIB\s+(.+)$", dt_text)
        if loc_m:
            release.location = loc_m.group(1).strip()

    # Content area
    content_div = soup.select_one("div.innner-page-main-about-us-content-right-part")
    if content_div:
        # Ministry
        ministry_div = content_div.select_one("div.MinistryNameSubhead")
        if ministry_div:
            release.ministry = ministry_div.get_text(" ", strip=True)

        # Title
        title_div = content_div.select_one("div.event-heading-background")
        if title_div:
            release.title = title_div.get_text(" ", strip=True)

        # Fallback: h2 tags
        if not release.ministry or not release.title:
            h2s = content_div.find_all("h2")
            if h2s and not release.ministry:
                release.ministry = h2s[0].get_text(" ", strip=True)
            if len(h2s) >= 2 and not release.title:
                release.title = h2s[1].get_text(" ", strip=True)

        # Body text
        bg = content_div.select_one("div.BackgroundRelease")
        if bg:
            paragraphs = []
            for p in bg.find_all(["p", "div", "li"]):
                text = p.get_text(" ", strip=True)
                text = re.sub(r"\s+", " ", text).strip()
                if text and text != "****" and "Release ID" not in text:
                    paragraphs.append(text)
            release.full_text = "\n\n".join(paragraphs) if paragraphs else bg.get_text("\n", strip=True)

    # Fallback body
    if not release.full_text:
        body_ps = soup.select("div.innner-page-main-about-us-content-right-part p")
        if body_ps:
            paragraphs = []
            for p in body_ps:
                text = p.get_text(" ", strip=True)
                text = re.sub(r"\s+", " ", text).strip()
                if text and len(text) > 10:
                    paragraphs.append(text)
            release.full_text = "\n\n".join(paragraphs)

    # Fallback title from <title> tag
    if not release.title:
        title_tag = soup.find("title")
        if title_tag:
            t = title_tag.get_text(" ", strip=True)
            t = re.sub(r"\s*[-|]\s*Press\s+Release.*$", "", t, flags=re.IGNORECASE)
            release.title = t.strip()

    # Fallback date from body text
    if not release.publication_date:
        body_text = soup.get_text(" ", strip=True)
        m = re.search(r"Posted\s+On\s*:\s*(\d{1,2}\s+\w+\s+\d{4})", body_text, re.IGNORECASE)
        if m:
            d = _parse_date_str(m.group(1))
            release.publication_date = d.isoformat() if d else ""

    # Language detection
    combined = release.title + " " + release.full_text[:2000]
    release.is_english = is_english_text(combined)
    release.language = "English" if release.is_english else "Non-English"

    # URL
    release.canonical_url = (
        f"{config.RELEASE_PAGE_URL}?PRID={prid}"
        f"&reg={config.DEFAULT_REGION}&lang={config.DEFAULT_LANG}"
    )

    # Content hash
    normalized = " ".join(release.full_text.split())
    release.content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    release.status = "valid" if release.title and release.publication_date else "incomplete"
    return release


# ---------------------------------------------------------------------------
# P12: Local validation
# ---------------------------------------------------------------------------

def validate_local(release: Release, start_date: date = None, end_date: date = None) -> bool:
    """Validate a release locally (no network). Returns True if valid."""
    if release.status != "valid":
        return False
    if not release.title:
        return False
    if not release.publication_date:
        return False
    if not release.is_english:
        return False
    if not release.full_text or len(release.full_text) < 50:
        return False
    if start_date and release.publication_date < start_date.isoformat():
        return False
    if end_date and release.publication_date > end_date.isoformat():
        return False
    return True


# ---------------------------------------------------------------------------
# P10: Raw HTML cache
# ---------------------------------------------------------------------------

def save_raw_html(prid: int, html: str):
    raw_dir = config.DATA_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"PRID_{prid}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def load_raw_html(prid: int) -> Optional[str]:
    path = config.DATA_DIR / "raw" / f"PRID_{prid}.html"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


# ---------------------------------------------------------------------------
# P13: Database writer (single thread)
# ---------------------------------------------------------------------------

class DBWriter:
    """Single-threaded SQLite writer. Consumes Release objects from queue."""

    def __init__(self, db_path: Path = None):
        self.    db_path = config.DATA_DIR / "pib_fast.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS releases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prid INTEGER UNIQUE NOT NULL,
            title TEXT,
            publication_date TEXT,
            publication_time TEXT,
            ministry TEXT,
            department TEXT,
            location TEXT,
            language TEXT DEFAULT 'English',
            region TEXT DEFAULT 'National',
            canonical_url TEXT,
            full_text TEXT,
            content_hash TEXT,
            page_variant TEXT,
            raw_html_path TEXT,
            first_seen_at TEXT,
            last_updated_at TEXT,
            status TEXT DEFAULT 'pending'
        );
        CREATE TABLE IF NOT EXISTS discovery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prid INTEGER NOT NULL,
            method TEXT NOT NULL,
            source_url TEXT,
            parent_prid INTEGER,
            discovered_at TEXT,
            FOREIGN KEY (prid) REFERENCES releases(prid)
        );
        CREATE TABLE IF NOT EXISTS crawl_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT,
            completed_at TEXT,
            total_candidates INTEGER,
            english_found INTEGER,
            non_english INTEGER,
            empty_pages INTEGER,
            http_errors INTEGER,
            requests_made INTEGER,
            elapsed_seconds REAL,
            config_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_releases_date ON releases(publication_date);
        CREATE INDEX IF NOT EXISTS idx_releases_status ON releases(status);
        CREATE INDEX IF NOT EXISTS idx_releases_lang ON releases(language);
        CREATE INDEX IF NOT EXISTS idx_discovery_prid ON discovery(prid);
        """)
        conn.commit()
        conn.close()

    def write_batch(self, releases: list):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        now = datetime.now().isoformat()

        for r in releases:
            existing = conn.execute(
                "SELECT prid, content_hash FROM releases WHERE prid=?", (r.prid,)
            ).fetchone()

            if existing:
                if existing["content_hash"] == r.content_hash:
                    continue
                conn.execute(
                    """UPDATE releases SET title=?, publication_date=?, publication_time=?,
                       ministry=?, department=?, location=?, language=?, region=?,
                       canonical_url=?, full_text=?, content_hash=?, page_variant=?,
                       raw_html_path=?, last_updated_at=?, status=? WHERE prid=?""",
                    (r.title, r.publication_date, r.publication_time,
                     r.ministry, r.department, r.location, r.language, r.region,
                     r.canonical_url, r.full_text, r.content_hash, r.page_variant,
                     r.raw_html_path, now, r.status, r.prid),
                )
            else:
                conn.execute(
                    """INSERT INTO releases
                       (prid, title, publication_date, publication_time, ministry,
                        department, location, language, region, canonical_url,
                        full_text, content_hash, page_variant, raw_html_path,
                        first_seen_at, last_updated_at, status)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (r.prid, r.title, r.publication_date, r.publication_time,
                     r.ministry, r.department, r.location, r.language, r.region,
                     r.canonical_url, r.full_text, r.content_hash, r.page_variant,
                     r.raw_html_path, now, now, r.status),
                )

            conn.execute(
                "INSERT OR IGNORE INTO discovery (prid, method, source_url, discovered_at) "
                "VALUES (?, ?, ?, ?)",
                (r.prid, "fast_crawl", r.canonical_url, now),
            )

        conn.commit()
        conn.close()

    def get_valid_prids(self) -> set:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT prid FROM releases WHERE status='valid'").fetchall()
        conn.close()
        return {r["prid"] for r in rows}

    def log_crawl(self, stats: CrawlStats, crawl_config: dict):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            """INSERT INTO crawl_log
               (started_at, completed_at, total_candidates, english_found,
                non_english, empty_pages, http_errors, requests_made,
                elapsed_seconds, config_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.fromtimestamp(stats.start_time).isoformat(),
             datetime.now().isoformat(),
             stats.total_candidates, stats.english_found,
             stats.non_english, stats.empty_pages, stats.http_errors,
             stats.requests_made, stats.elapsed,
             json.dumps(crawl_config)),
        )
        conn.commit()
        conn.close()


# ---------------------------------------------------------------------------
# P7+P8+P9: Async HTTP client with keep-alive, retries, backoff
# ---------------------------------------------------------------------------

class AsyncFetcher:
    def __init__(self, max_workers: int = 10, max_retries: int = 3):
        self.max_workers = max_workers
        self.max_retries = max_retries
        self._semaphore = None
        self._client = None

    async def __aenter__(self):
        self._semaphore = asyncio.Semaphore(self.max_workers)
        timeout = httpx.Timeout(30.0, connect=10.0)
        limits = httpx.Limits(
            max_connections=self.max_workers + 5,
            max_keepalive_connections=self.max_workers,
            keepalive_expiry=30,
        )
        self._client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
            headers={
                "User-Agent": config.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def fetch(self, url: str, prid: int) -> tuple:
        """Fetch URL with retries and exponential backoff. Returns (html, http_status, error)."""
        for attempt in range(self.max_retries + 1):
            try:
                async with self._semaphore:
                    resp = await self._client.get(url)
                    if resp.status_code == 200:
                        return resp.text, resp.status_code, ""
                    elif resp.status_code in (429, 500, 502, 503, 504):
                        wait = min(2 ** attempt * 1.0, 30.0)
                        await asyncio.sleep(wait)
                        continue
                    else:
                        return "", resp.status_code, f"HTTP {resp.status_code}"
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                if attempt < self.max_retries:
                    wait = min(2 ** attempt * 1.0, 30.0)
                    await asyncio.sleep(wait)
                else:
                    return "", 0, f"Connection error: {type(e).__name__}"
            except Exception as e:
                return "", 0, f"Error: {type(e).__name__}: {e}"

        return "", 0, "Max retries exceeded"


# ---------------------------------------------------------------------------
# Main crawler
# ---------------------------------------------------------------------------

async def crawl_range(
    start_prid: int,
    end_prid: int,
    start_date: date = None,
    end_date: date = None,
    max_workers: int = 10,
    max_retries: int = 3,
) -> CrawlStats:
    """Crawl PRID range with async workers. Single-fetch: fetch → parse → validate → save."""

    stats = CrawlStats()
    stats.start_time = time.time()
    stats.total_candidates = end_prid - start_prid + 1

    db = DBWriter()
    existing_valid = db.get_valid_prids()

    result_queue = asyncio.Queue(maxsize=500)
    stats_lock = asyncio.Lock()

    log.info(f"Starting fast crawl: PRID {start_prid} → {end_prid}")
    log.info(f"Workers: {max_workers}, Already valid: {len(existing_valid)}")

    # DB writer task
    async def db_writer_task():
        batch = []
        while True:
            try:
                release = await asyncio.wait_for(result_queue.get(), timeout=5.0)
                if release is None:  # Poison pill
                    if batch:
                        db.write_batch(batch)
                    break
                batch.append(release)
                if len(batch) >= 100:
                    db.write_batch(batch)
                    batch = []
            except asyncio.TimeoutError:
                if batch:
                    db.write_batch(batch)
                    batch = []
            except Exception as e:
                log.error(f"DB writer error: {e}")

    async def fetch_and_parse(fetcher: AsyncFetcher, prid: int) -> Optional[Release]:
        # Skip already valid
        if prid in existing_valid:
            async with stats_lock:
                stats.already_valid += 1
                stats.completed += 1
            return None

        url = (
            f"{config.RELEASE_PAGE_URL}?PRID={prid}"
            f"&reg={config.DEFAULT_REGION}&lang={config.DEFAULT_LANG}"
        )

        html, http_status, error = await fetcher.fetch(url, prid)

        async with stats_lock:
            stats.requests_made += 1

        if error or not html:
            async with stats_lock:
                stats.http_errors += 1
                stats.completed += 1
                if error:
                    stats.errors_by_type[error] += 1
            return None

        # P10: Cache raw HTML
        raw_path = save_raw_html(prid, html)

        # P11: Single-pass parse
        release = parse_release_single_pass(html, prid)
        release.http_status = http_status
        release.raw_html_path = raw_path

        # P12: Local validation
        if not validate_local(release, start_date, end_date):
            async with stats_lock:
                if not release.is_english:
                    stats.non_english += 1
                elif not release.title:
                    stats.empty_pages += 1
                stats.completed += 1
            release.status = "failed" if release.status == "valid" else release.status
            return release

        async with stats_lock:
            stats.english_found += 1
            stats.completed += 1

        return release

    async def progress_reporter():
        while True:
            await asyncio.sleep(30)
            async with stats_lock:
                if stats.completed > 0:
                    log.info(
                        f"Progress: {stats.completed}/{stats.total_candidates} "
                        f"({stats.requests_per_sec:.1f} req/s, "
                        f"{stats.english_found} EN, {stats.non_english} non-EN, "
                        f"est {stats.estimated_remaining/60:.0f}m remaining)"
                    )

    # Run
    db_task = asyncio.create_task(db_writer_task())
    progress_task = asyncio.create_task(progress_reporter())

    async with AsyncFetcher(max_workers=max_workers, max_retries=max_retries) as fetcher:
        sem = asyncio.Semaphore(max_workers)

        async def bounded_fetch(prid):
            async with sem:
                return await fetch_and_parse(fetcher, prid)

        # Process in batches to avoid memory issues
        batch_size = 500
        for batch_start in range(start_prid, end_prid + 1, batch_size):
            batch_end = min(batch_start + batch_size, end_prid + 1)
            prids = list(range(batch_start, batch_end))

            tasks = [bounded_fetch(p) for p in prids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in results:
                if isinstance(r, Release) and r:
                    await result_queue.put(r)

    # Signal DB writer to finish
    await result_queue.put(None)
    progress_task.cancel()
    await db_task

    # Final report
    log.info(stats.report())
    db.log_crawl(stats, {
        "start_prid": start_prid,
        "end_prid": end_prid,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "max_workers": max_workers,
    })

    return stats


def run_fast_crawl(
    start_prid: int = None,
    end_prid: int = None,
    start_date_str: str = None,
    end_date_str: str = None,
    max_workers: int = 10,
):
    """Synchronous entry point for CLI."""
    from .database import init_db
    init_db()

    start_prid = start_prid or config.PRID_RANGE_START
    end_prid = end_prid or config.PRID_RANGE_END
    start_date = date.fromisoformat(start_date_str) if start_date_str else None
    end_date = date.fromisoformat(end_date_str) if end_date_str else None

    stats = asyncio.run(
        crawl_range(start_prid, end_prid, start_date, end_date, max_workers)
    )
    return stats
