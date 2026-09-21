import logging
from datetime import date, timedelta
from typing import Optional

from .. import config
from ..http_client import HttpClient
from ..parsers import parse_aspnet_form, parse_listing_releases, parse_ministry_dropdown
from .. import database as db

log = logging.getLogger("harritpib.engine.ministry")


class MinistryEngine:
    def __init__(self, http: HttpClient, region: int = None, lang: int = None):
        self.http = http
        self.region = region or config.DEFAULT_REGION
        self.lang = lang or config.DEFAULT_LANG
        self._ministries = None

    def _build_url(self) -> str:
        return f"{config.ALL_REL_URL}?reg={self.region}&lang={self.lang}"

    def _get_form(self, target_date: date) -> Optional[dict]:
        html = self.http.get(self._build_url(), use_cache=False)
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

    def _post_ministry(self, form: dict, ministry_val: str) -> Optional[str]:
        data = dict(form)
        data["__EVENTTARGET"] = "ctl00$ContentPlaceHolder1$ddlMinistry"
        data["__EVENTARGUMENT"] = ""
        data["ctl00$ContentPlaceHolder1$ddlMinistry"] = ministry_val
        return self.http.post(self._build_url(), data=data, use_cache=False)

    def discover_ministry_for_date(self, target_date: date, ministry_val: str, ministry_name: str) -> list:
        date_str = target_date.isoformat()
        form = self._get_form(target_date)
        if not form:
            return []

        html = self._post_ministry(form, ministry_val)
        if not html:
            return []

        releases = parse_listing_releases(html)
        new_count = 0
        for rel in releases:
            prid = rel["prid"]
            existing = db.get_release(prid)
            if not existing or existing.get("status") != "valid":
                db.upsert_release(
                    prid,
                    title=rel.get("title", ""),
                    publication_date=rel.get("date", ""),
                    ministry=rel.get("ministry", "") or ministry_name,
                    status="pending",
                )
                db.add_discovery(prid, "ministry_listing", source_url=f"ministry={ministry_val}")
                new_count += 1

        db.update_crawl_date(date_str, f"ministry_{ministry_val}", len(releases), new_count, "discovered")
        return releases

    def discover_date(self, target_date: date, max_ministries: int = None) -> dict:
        date_str = target_date.isoformat()
        log.info(f"Ministry engine: discovering {date_str}")

        if not self._ministries:
            self._ministries = self.get_ministries()
            log.info(f"Found {len(self._ministries)} ministries")

        total_found = 0
        results = {}
        ministries = self._ministries[:max_ministries] if max_ministries else self._ministries

        for m in ministries:
            try:
                releases = self.discover_date_for_ministry(target_date, m["value"], m["name"])
                count = len(releases)
                results[m["name"]] = count
                total_found += count
                if count > 0:
                    log.info(f"  {m['name']}: {count} releases")
            except Exception as e:
                log.warning(f"  {m['name']}: error - {e}")

        log.info(f"Ministry engine {date_str}: {total_found} total releases across {len(ministries)} ministries")
        return results

    def discover_date_for_ministry(self, target_date: date, ministry_val: str, ministry_name: str) -> list:
        date_str = target_date.isoformat()
        form = self._get_form(target_date)
        if not form:
            return []

        html = self._post_ministry(form, ministry_val)
        if not html:
            return []

        releases = parse_listing_releases(html)
        for rel in releases:
            prid = rel["prid"]
            db.upsert_release(
                prid,
                title=rel.get("title", ""),
                publication_date=rel.get("date", ""),
                ministry=rel.get("ministry", "") or ministry_name,
                status="pending",
            )
            db.add_discovery(prid, "ministry_listing", source_url=f"ministry={ministry_val}&date={date_str}")
        return releases

    def get_ministries(self) -> list:
        html = self.http.get(self._build_url(), use_cache=False)
        if not html:
            return []
        return parse_ministry_dropdown(html)
