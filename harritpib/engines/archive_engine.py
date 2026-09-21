import logging
import re
from datetime import date
from typing import Optional

from .. import config
from ..http_client import HttpClient
from ..parsers import extract_prid_from_url
from .. import database as db

log = logging.getLogger("harritpib.engine.archive")


class ArchiveEngine:
    def __init__(self, http: HttpClient):
        self.http = http

    def probe_archive(self) -> list:
        discovered = []
        urls_to_check = [
            f"{config.ARCHIVE_BASE}/archive2/erelease.aspx",
            f"{config.ARCHIVE_BASE}/archive/phase2/archiveministry.aspx?phase=3",
            f"{config.ARCHIVE_BASE}/newsite/archivepage.aspx",
        ]
        for url in urls_to_check:
            try:
                html = self.http.get(url, use_cache=False)
                if not html:
                    continue
                prids = set()
                for m in re.finditer(r"PRID=(\d+)", html, re.IGNORECASE):
                    prid = int(m.group(1))
                    if prid not in prids:
                        prids.add(prid)
                        existing = db.get_release(prid)
                        if not existing:
                            db.upsert_release(prid, status="pending")
                            db.add_discovery(prid, "archive", source_url=url)
                            discovered.append(prid)
                log.info(f"Archive {url}: found {len(prids)} PRIDs")
            except Exception as e:
                log.warning(f"Archive {url}: error - {e}")
        return discovered
