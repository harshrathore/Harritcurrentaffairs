import logging
import re
from datetime import date

from .. import config
from ..http_client import HttpClient
from ..parsers import parse_release_page
from .. import database as db

log = logging.getLogger("harritpib.engine.prid")


def is_english_text(text: str) -> bool:
    if not text:
        return False
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    return ascii_chars / max(len(text), 1) > 0.7


class PRIDEngine:
    def __init__(self, http: HttpClient, region: int = None, lang: int = None):
        self.http = http
        self.region = region or config.DEFAULT_REGION
        self.lang = lang or config.DEFAULT_LANG

    def _release_url(self, prid: int) -> str:
        return (
            f"{config.RELEASE_PAGE_URL}?PRID={prid}"
            f"&reg={self.region}&lang={self.lang}"
        )

    def probe_prid(self, prid: int) -> dict:
        url = self._release_url(prid)
        html = self.http.get(url, use_cache=False)
        if not html:
            return {"prid": prid, "status": "http_error"}

        if len(html) < 1000:
            return {"prid": prid, "status": "empty_page"}

        body_text = html.lower()
        if "release id" not in body_text and "posted on" not in body_text:
            return {"prid": prid, "status": "not_release"}

        parsed = parse_release_page(html, prid)
        return {"prid": prid, "status": "found", "data": parsed}

    def probe_range(self, start_prid: int, end_prid: int, start_date: date = None, end_date: date = None) -> dict:
        discovered = 0
        skipped = 0
        errors = 0
        non_english = 0

        for prid in range(start_prid, end_prid + 1):
            existing = db.get_release(prid)
            if existing and existing.get("status") == "valid":
                skipped += 1
                continue

            try:
                result = self.probe_prid(prid)
                if result["status"] == "found":
                    data = result["data"]
                    pub_date = data.get("publication_date", "")

                    if start_date and pub_date and pub_date < start_date.isoformat():
                        skipped += 1
                        continue
                    if end_date and pub_date and pub_date > end_date.isoformat():
                        skipped += 1
                        continue

                    full_text = data.get("full_text", "")
                    title = data.get("title", "")
                    if not is_english_text(title + " " + full_text[:500]):
                        non_english += 1
                        if non_english % 100 == 0:
                            log.info(f"PRID probe: {non_english} non-English skipped up to {prid}")
                        continue

                    db.upsert_release(
                        prid,
                        title=data.get("title", ""),
                        publication_date=pub_date,
                        publication_time=data.get("publication_time", ""),
                        ministry=data.get("ministry", ""),
                        full_text=full_text,
                        location=data.get("location", ""),
                        canonical_url=data.get("canonical_url", ""),
                        successful_url=self._release_url(prid),
                        page_variant="PressReleasePage",
                        status="valid",
                    )
                    db.add_discovery(prid, "prid_probe", source_url=self._release_url(prid))
                    discovered += 1

                    if discovered % 25 == 0:
                        log.info(f"PRID probe: {prid} - {discovered} English found, {skipped} skipped, {non_english} non-English")

            except Exception as e:
                errors += 1
                log.warning(f"PRID {prid}: error - {e}")

        return {
            "discovered": discovered,
            "skipped": skipped,
            "errors": errors,
            "non_english": non_english,
        }
