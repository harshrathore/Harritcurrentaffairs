import logging
from datetime import date, timedelta
from typing import Optional

from .. import config
from ..http_client import HttpClient
from ..parsers import parse_aspnet_form, parse_listing_releases, extract_prid_from_url
from .. import database as db

log = logging.getLogger("harritpib.engine.date")

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


class DateEngine:
    def __init__(self, http: HttpClient, region: int = None, lang: int = None):
        self.http = http
        self.region = region or config.DEFAULT_REGION
        self.lang = lang or config.DEFAULT_LANG

    def _build_postback_url(self) -> str:
        return f"{config.ALL_REL_URL}?reg={self.region}&lang={self.lang}"

    def _get_initial_form(self, target_date: date) -> Optional[dict]:
        url = self._build_postback_url()
        html = self.http.get(url, use_cache=False)
        if not html:
            return None
        form = parse_aspnet_form(html)
        form["ctl00$Bar1$ddlregion"] = str(self.region)
        form["ctl00$Bar1$ddlLang"] = str(self.lang)
        form["ctl00$ContentPlaceHolder1$ddlMinistry"] = "0"
        form["ctl00$ContentPlaceHolder1$ddlday"] = "0"
        form["ctl00$ContentPlaceHolder1$ddlMonth"] = str(target_date.month)
        form["ctl00$ContentPlaceHolder1$ddlYear"] = str(target_date.year)
        return form

    def _post_with_date(self, form: dict, event_target: str, day: int = 0) -> Optional[str]:
        data = dict(form)
        data["__EVENTTARGET"] = event_target
        data["__EVENTARGUMENT"] = ""
        data["ctl00$ContentPlaceHolder1$ddlday"] = str(day)
        url = self._build_postback_url()
        return self.http.post(url, data=data, use_cache=False)

    def discover_date(self, target_date: date) -> list:
        date_str = target_date.isoformat()
        log.info(f"Date engine: discovering {date_str}")

        form = self._get_initial_form(target_date)
        if not form:
            log.warning(f"Failed to get initial form for {date_str}")
            db.update_crawl_date(date_str, "date_listing", 0, 0, "failed", "form_fetch_failed")
            return []

        all_releases = {}

        for day in range(1, 32):
            try:
                html = self._post_with_date(form, "ctl00$ContentPlaceHolder1$ddlMonth", day)
                if not html:
                    continue
                releases = parse_listing_releases(html)
                for rel in releases:
                    prid = rel["prid"]
                    if prid not in all_releases:
                        all_releases[prid] = rel
                        db.upsert_release(
                            prid,
                            title=rel.get("title", ""),
                            publication_date=rel.get("date", ""),
                            ministry=rel.get("ministry", ""),
                            status="pending",
                        )
                        db.add_discovery(prid, "date_listing", source_url=f"date={date_str}&day={day}")
                log.info(f"  Day {day:2d}: {len(releases)} releases")
            except Exception as e:
                log.warning(f"  Day {day:2d}: error - {e}")

        discovered = len(all_releases)
        db.update_crawl_date(date_str, "date_listing", discovered, 0, "discovered")
        log.info(f"Date {date_str}: total {discovered} unique releases")
        return list(all_releases.values())

    def discover_range(self, start: date, end: date) -> dict:
        results = {}
        current = start
        while current <= end:
            date_str = current.isoformat()
            existing = db.get_crawl_dates("date_listing")
            if date_str in existing and existing[date_str].get("status") == "complete":
                log.info(f"Skipping {date_str} (already complete)")
                current += timedelta(days=1)
                continue
            releases = self.discover_date(current)
            results[date_str] = len(releases)
            current += timedelta(days=1)
        return results

    def get_ministries(self) -> list:
        url = self._build_postback_url()
        html = self.http.get(url, use_cache=False)
        if not html:
            return []
        from ..parsers import parse_ministry_dropdown
        return parse_ministry_dropdown(html)
