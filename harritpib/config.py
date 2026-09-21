from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "PIB" / "harritpib"
RAW_CACHE_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "pib_historical.db"
EXPORTS_DIR = DATA_DIR / "exports"
REPORTS_DIR = DATA_DIR / "reports"

PIB_BASE = "https://www.pib.gov.in"
ALL_REL_URL = f"{PIB_BASE}/allRel.aspx"
RELEASE_SHARE_URL = f"{PIB_BASE}/Pressreleaseshare.aspx"
RELEASE_PAGE_URL = f"{PIB_BASE}/PressReleasePage.aspx"
ARCHIVE_BASE = "https://archive.pib.gov.in"

DEFAULT_REGION = 48
DEFAULT_LANG = 1
DEFAULT_START = date(2026, 6, 1)

HTTP_TIMEOUT = 30
HTTP_MAX_RETRIES = 5
HTTP_BACKOFF = 2
MIN_DELAY = 0.5
MAX_DELAY = 2.0

PRID_RANGE_START = 2_265_000
PRID_RANGE_END = 2_315_000
PRID_PROBE_STEP = 1

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0.0.0 Safari/537.36"
)
