import time
import random
import hashlib
import logging
from pathlib import Path
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config

log = logging.getLogger("harritpib.http")


class HttpClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.pib.gov.in/",
        })
        retry = Retry(total=config.HTTP_MAX_RETRIES, backoff_factor=config.HTTP_BACKOFF,
                      status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=["GET", "POST"])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self._last_request_time = 0.0
        self._request_count = 0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        delay = random.uniform(config.MIN_DELAY, config.MAX_DELAY)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request_time = time.time()

    def _cache_path(self, url: str) -> Path:
        h = hashlib.md5(url.encode()).hexdigest()
        return config.RAW_CACHE_DIR / f"{h}.html"

    def _read_cache(self, url: str) -> Optional[str]:
        p = self._cache_path(url)
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")
        return None

    def _write_cache(self, url: str, html: str):
        config.RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._cache_path(url).write_text(html, encoding="utf-8")

    def get(self, url: str, use_cache: bool = True, **kwargs) -> Optional[str]:
        if use_cache:
            cached = self._read_cache(url)
            if cached:
                return cached
        self._rate_limit()
        try:
            self._request_count += 1
            resp = self.session.get(url, timeout=config.HTTP_TIMEOUT, **kwargs)
            resp.raise_for_status()
            html = resp.text
            if use_cache and len(html) > 100:
                self._write_cache(url, html)
            return html
        except requests.RequestException as e:
            log.warning(f"GET failed: {url} - {e}")
            return None

    def post(self, url: str, data: dict, use_cache: bool = False, **kwargs) -> Optional[str]:
        self._rate_limit()
        try:
            self._request_count += 1
            resp = self.session.post(url, data=data, timeout=config.HTTP_TIMEOUT, **kwargs)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            log.warning(f"POST failed: {url} - {e}")
            return None

    def get_with_session(self, url: str) -> Optional[requests.Response]:
        self._rate_limit()
        try:
            self._request_count += 1
            resp = self.session.get(url, timeout=config.HTTP_TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            log.warning(f"GET failed: {url} - {e}")
            return None

    @property
    def stats(self) -> dict:
        return {
            "total_requests": self._request_count,
            "cookies": len(self.session.cookies),
        }
