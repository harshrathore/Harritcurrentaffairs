import logging
import re
from typing import Set

from .. import config
from ..http_client import HttpClient
from ..parsers import extract_prid_from_url
from .. import database as db

log = logging.getLogger("harritpib.engine.internal")


class InternalEngine:
    def __init__(self, http: HttpClient):
        self.http = http
        self._visited: Set[int] = set()

    def crawl_release_links(self, prid: int, max_depth: int = 1) -> list:
        if prid in self._visited:
            return []
        self._visited.add(prid)

        url = (
            f"{config.RELEASE_PAGE_URL}?PRID={prid}"
            f"&reg={config.DEFAULT_REGION}&lang={config.DEFAULT_LANG}"
        )
        html = self.http.get(url, use_cache=True)
        if not html:
            return []

        discovered = []
        seen = set()
        for m in re.finditer(r"PRID=(\d+)", html, re.IGNORECASE):
            link_prid = int(m.group(1))
            if link_prid != prid and link_prid not in seen:
                seen.add(link_prid)
                existing = db.get_release(link_prid)
                if not existing:
                    db.upsert_release(link_prid, status="pending")
                    db.add_discovery(link_prid, "internal_link", source_url=url, parent_prid=prid)
                    discovered.append(link_prid)

        if max_depth > 1:
            for link_prid in discovered[:10]:
                sub = self.crawl_release_links(link_prid, max_depth - 1)
                discovered.extend(sub)

        return discovered
