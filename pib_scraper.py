import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime, timedelta
from pathlib import Path
import json
import re
import time


# =========================================================
# PIB SCRAPER
# RESUME + REPAIR + 7-DAY DATABASE
# =========================================================


# =========================================================
# CONFIGURATION
# =========================================================

BASE_URL = "https://www.pib.gov.in"

START_URL = (
    "https://www.pib.gov.in/"
    "AllRelease.aspx?lang=1&reg=3"
)

# Hindi PIB
HINDI_URL = (
    "https://www.pib.gov.in/"
    "AllRelease.aspx?lang=2&reg=3"
)

# Also try the region-specific URL if main fails
FALLBACK_URL = (
    "https://www.pib.gov.in/"
    "allRel.aspx?reg=48&lang=1"
)

LOOKBACK_DAYS = 14

REQUEST_DELAY = 1.0

# ---------------------------------------------------------
# IMPORTANT:
#
# 5 = process only first 5 candidates
#
# None = process ALL 7-day candidates
#
# KEEP THIS AT 5 FOR THE FIRST TEST.
# After successful test, change to:
#
# TEST_LIMIT = 5
# ---------------------------------------------------------

TEST_LIMIT = None


# =========================================================
# FILES
# =========================================================

DATA_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "PIB"
)
DATABASE_FILE = (
    DATA_DIR /
    "pib_database.json"
)

OUTPUT_FILE = (
    DATA_DIR /
    "pib_latest_7_days.json"
)

LOG_FILE = (
    DATA_DIR /
    "pib_scraper.log"
)

ERROR_LOG_FILE = (
    DATA_DIR /
    "pib_errors.log"
)


# =========================================================
# HTTP HEADERS
# =========================================================

HEADERS = {

    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),

    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),

    "Accept-Language":
        "en-US,en;q=0.9",

    "Referer":
        "https://www.pib.gov.in/",

}


# =========================================================
# CREATE DATA DIRECTORY
# =========================================================

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# SESSION
# =========================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


# =========================================================
# SAFE LOGGING
# =========================================================

def safe_write_log(
    filename,
    line
):

    try:

        with open(
            filename,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                line + "\n"
            )

    except Exception:

        # Logging must NEVER crash scraper.
        pass


def log(
    message
):

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    line = (
        f"[{timestamp}] "
        f"{message}"
    )

    print(line)

    safe_write_log(
        LOG_FILE,
        line
    )


def error_log(
    message
):

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    line = (
        f"[{timestamp}] "
        f"{message}"
    )

    print(line)

    safe_write_log(
        ERROR_LOG_FILE,
        line
    )


# =========================================================
# DATABASE
# =========================================================

def load_database():

    if not DATABASE_FILE.exists():

        log(
            "DATABASE: No existing database"
        )

        return {}

    try:

        with open(
            DATABASE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            database = json.load(
                f
            )

        if not isinstance(
            database,
            dict
        ):

            raise ValueError(
                "Database must be a JSON object"
            )

        log(
            f"DATABASE: Loaded "
            f"{len(database)} records"
        )

        return database

    except Exception as e:

        error_log(
            f"DATABASE LOAD ERROR: {e}"
        )

        raise


# =========================================================
# ATOMIC DATABASE SAVE
# =========================================================

def save_database(
    database
):

    temp_file = (
        DATA_DIR /
        "pib_database.tmp"
    )

    try:

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                database,
                f,
                ensure_ascii=False,
                indent=2
            )

            f.flush()

        temp_file.replace(
            DATABASE_FILE
        )

        return True

    except Exception as e:

        error_log(
            f"DATABASE SAVE ERROR: {e}"
        )

        try:

            if temp_file.exists():

                temp_file.unlink()

        except Exception:

            pass

        return False


# =========================================================
# FETCH URL
# =========================================================

def fetch_page(
    url
):

    log(
        f"FETCH: {url}"
    )

    response = session.get(
        url,
        timeout=40
    )

    log(
        f"HTTP {response.status_code} | "
        f"{len(response.content):,} bytes"
    )

    response.raise_for_status()

    return response.text


# =========================================================
# NORMALIZE URL
# =========================================================

def normalize_url(
    url
):

    return (
        url
        .split("#")[0]
        .rstrip("/")
    )


# =========================================================
# EXTRACT PRID
# =========================================================

def extract_prid(
    url
):

    if not url:

        return None

    parsed = urlparse(
        url
    )

    query = parse_qs(
        parsed.query
    )

    values = query.get(
        "PRID"
    )

    if values:

        return values[0]

    match = re.search(
        r"PRID=(\d+)",
        url,
        re.IGNORECASE
    )

    if match:

        return match.group(1)

    return None


# =========================================================
# CHECK RELEASE URL
# =========================================================

def is_release_url(
    url
):

    if not url:

        return False

    parsed = urlparse(
        url
    )

    host = (
        parsed.netloc.lower()
    )

    if host not in {
        "",
        "pib.gov.in",
        "www.pib.gov.in"
    }:

        return False

    path = (
        parsed.path.lower()
    )

    return (
        "pressrelesedetail.aspx"
        in path
    )


# =========================================================
# DATE PARSER
# =========================================================

def parse_date(
    value
):

    if not value:

        return None

    value = (
        value
        .strip()
    )

    formats = [

        "%d-%m-%Y",

        "%d/%m/%Y",

        "%d.%m.%Y",

        "%Y-%m-%d",

        "%B %d, %Y",

        "%b %d, %Y",

        "%d %B %Y",

        "%d %b %Y",

    ]

    for fmt in formats:

        try:

            return datetime.strptime(
                value,
                fmt
            ).date()

        except ValueError:

            continue

    return None


# =========================================================
# EXTRACT PIB POSTED DATE
# =========================================================

def extract_posted_date(
    text
):

    if not text:

        return None

    patterns = [

        r"Posted\s+on\s*:\s*"
        r"(\d{1,2}\s+"
        r"[A-Za-z]+\s+"
        r"\d{4})",

        r"Posted\s+On\s*:\s*"
        r"(\d{1,2}\s+"
        r"[A-Za-z]+\s+"
        r"\d{4})",

        r"Posted\s*:\s*"
        r"(\d{1,2}\s+"
        r"[A-Za-z]+\s+"
        r"\d{4})",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:

            continue

        parsed = parse_date(
            match.group(1)
        )

        if parsed:

            return parsed

    return None


# =========================================================
# EXTRACT ARTICLE DATE
#
# IMPORTANT:
# This is only a FALLBACK.
#
# We do NOT prefer arbitrary dates appearing inside
# article prose over the PIB posting date.
# =========================================================

def extract_pib_article_date(
    text
):

    if not text:

        return None

    patterns = [

        r"\b"
        r"(January|February|March|April|May|June|"
        r"July|August|September|October|November|December)"
        r"\s+\d{1,2},\s+\d{4}"
        r"\b",

        r"\b"
        r"\d{1,2}\s+"
        r"(January|February|March|April|May|June|"
        r"July|August|September|October|November|December)"
        r"\s+\d{4}"
        r"\b",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:

            continue

        parsed = parse_date(
            match.group(0)
        )

        if parsed:

            return parsed

    return None


# =========================================================
# EXTRACT ARCHIVE RELEASE LINKS
# =========================================================

def extract_release_links(
    html
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    releases = []

    seen = set()

    current_ministry = ""

    containers = soup.select(
        "ul.num"
    )

    log(
        f"PIB ministry containers: "
        f"{len(containers)}"
    )

    for container in containers:

        heading = container.find(
            "h3"
        )

        if heading:

            current_ministry = (
                heading
                .get_text(
                    " ",
                    strip=True
                )
            )

        for li in container.find_all(
            "li",
            recursive=False
        ):

            link = li.find(
                "a",
                href=True
            )

            if not link:

                continue

            href = (
                link
                .get(
                    "href",
                    ""
                )
                .strip()
            )

            absolute_url = urljoin(
                BASE_URL,
                href
            )

            absolute_url = normalize_url(
                absolute_url
            )

            if not is_release_url(
                absolute_url
            ):

                continue

            prid = extract_prid(
                absolute_url
            )

            if not prid:

                continue

            if prid in seen:

                continue

            seen.add(
                prid
            )

            title = (
                link
                .get(
                    "title",
                    ""
                )
                .strip()
            )

            if not title:

                title = (
                    link
                    .get_text(
                        " ",
                        strip=True
                    )
                )

            li_text = li.get_text(
                " ",
                strip=True
            )

            date = (
                extract_posted_date(
                    li_text
                )
            )

            releases.append({

                "prid":
                    prid,

                "url":
                    absolute_url,

                "title":
                    title,

                "date":
                    (
                        date.isoformat()
                        if date
                        else ""
                    ),

                "ministry":
                    current_ministry,

            })

    return releases


# =========================================================
# TITLE QUALITY
# =========================================================

def is_good_title(
    text
):

    if not text:

        return False

    text = (
        text
        .strip()
    )

    if len(text) < 15:

        return False

    bad_titles = {

        "पत्र सूचना कार्यालय",

        "press information bureau",

        "press information bureau (pib)",

        "government of india",

    }

    if text.lower() in {

        x.lower()

        for x in bad_titles

    }:

        return False

    return True


# =========================================================
# FIND TITLE
# =========================================================

def find_article_title(
    soup,
    fallback=""
):

    selectors = [

        "#ContentPlaceHolder1_lblTitle",

        "#ContentPlaceHolder1_lblHeading",

        ".release-title",

        ".press-title",

        "h1",

    ]

    for selector in selectors:

        element = soup.select_one(
            selector
        )

        if not element:

            continue

        text = element.get_text(
            " ",
            strip=True
        )

        if is_good_title(
            text
        ):

            return text

    # -----------------------------------------------------
    # OpenGraph title
    # -----------------------------------------------------

    meta = soup.find(
        "meta",
        attrs={
            "property": "og:title"
        }
    )

    if meta:

        text = (
            meta
            .get(
                "content",
                ""
            )
            .strip()
        )

        if is_good_title(
            text
        ):

            return text

    # -----------------------------------------------------
    # Page title
    # -----------------------------------------------------

    title_tag = soup.find(
        "title"
    )

    if title_tag:

        text = title_tag.get_text(
            " ",
            strip=True
        )

        if is_good_title(
            text
        ):

            return text

    # -----------------------------------------------------
    # Archive title
    # -----------------------------------------------------

    if is_good_title(
        fallback
    ):

        return fallback

    return ""


# =========================================================
# CLEAN ARTICLE TEXT
# =========================================================

def clean_article_text(
    text
):

    if not text:

        return ""

    lines = []

    for line in text.splitlines():

        line = re.sub(
            r"\s+",
            " ",
            line
        ).strip()

        if not line:

            continue

        if line in {

            "Home",

            "Back",

            "Print",

            "Share",

            "Download",

        }:

            continue

        lines.append(
            line
        )

    return "\n".join(
        lines
    )


# =========================================================
# EXTRACT ARTICLE FRAME CONTENT
#
# THIS IS THE IMPORTANT PIB FIX.
#
# Actual release text is inside <p> elements of:
#
# PressReleasePage.aspx?PRID=...
# =========================================================

def extract_article_frame_content(
    soup
):

    paragraphs = []

    seen = set()

    # -----------------------------------------------------
    # Extract normal <p> elements.
    #
    # DO NOT decompose the document before doing this.
    # -----------------------------------------------------

    for p in soup.find_all(
        "p"
    ):

        text = p.get_text(
            " ",
            strip=True
        )

        if not text:

            continue

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        # -------------------------------------------------
        # PIB separators
        # -------------------------------------------------

        if text == "****":

            continue

        # -------------------------------------------------
        # PIB internal reference codes
        #
        # Example:
        # MJPS/SS/PRK
        # -------------------------------------------------

        if re.fullmatch(
            r"[A-Za-z]{2,10}/"
            r"[A-Za-z]{2,10}/"
            r"[A-Za-z]{2,10}",
            text
        ):

            continue

        # -------------------------------------------------
        # Release ID
        # -------------------------------------------------

        if re.search(
            r"Release\s*ID\s*:",
            text,
            re.IGNORECASE
        ):

            continue

        if "रिलीज़ आईडी" in text:

            continue

        # -------------------------------------------------
        # Visitor counter
        # -------------------------------------------------

        if "आगंतुक पटल" in text:

            continue

        # -------------------------------------------------
        # Exact duplicate removal
        # -------------------------------------------------

        normalized = (
            text
            .casefold()
            .strip()
        )

        if normalized in seen:

            continue

        seen.add(
            normalized
        )

        paragraphs.append(
            text
        )

    # -----------------------------------------------------
    # Normal successful result
    # -----------------------------------------------------

    if paragraphs:

        return clean_article_text(
            "\n\n".join(
                paragraphs
            )
        )

    # -----------------------------------------------------
    # FALLBACK SELECTORS
    # -----------------------------------------------------

    selectors = [

        "#ContentPlaceHolder1_lblContent",

        "#ContentPlaceHolder1_dvContent",

        "#ContentPlaceHolder1_divContent",

        ".release-content",

        ".press-release-content",

        ".content-area",

        "article",

    ]

    best = ""

    for selector in selectors:

        for element in soup.select(
            selector
        ):

            text = element.get_text(
                "\n",
                strip=True
            )

            text = re.sub(
                r"\s+",
                " ",
                text
            ).strip()

            if len(text) > len(best):

                best = text

    return best


# =========================================================
# FETCH ONE PIB RELEASE
# =========================================================

def fetch_release(
    release
):

    time.sleep(
        REQUEST_DELAY
    )

    # =====================================================
    # STEP 1
    # FETCH OUTER RELEASE PAGE
    # =====================================================

    outer_url = release["url"]

    log(
        f"FETCH OUTER: {outer_url}"
    )

    outer_response = session.get(
        outer_url,
        timeout=40
    )

    log(
        f"OUTER HTTP "
        f"{outer_response.status_code} | "
        f"{len(outer_response.content):,} bytes"
    )

    outer_response.raise_for_status()

    outer_html = outer_response.text

    outer_soup = BeautifulSoup(
        outer_html,
        "html.parser"
    )

    # =====================================================
    # STEP 2
    # TITLE
    # =====================================================

    title = find_article_title(
        outer_soup,
        release.get(
            "title",
            ""
        )
    )

    # =====================================================
    # STEP 3
    # FIND ARTICLE IFRAME
    # =====================================================

    iframe = outer_soup.find(
        "iframe",
        id="ContentPlaceHolder1_iframepressrealese"
    )

    if not iframe:

        for candidate in outer_soup.find_all(
            "iframe"
        ):

            src = candidate.get(
                "src",
                ""
            )

            if (
                "PressReleasePage.aspx"
                in src
            ):

                iframe = candidate

                break

    if not iframe:

        raise RuntimeError(
            "PIB article iframe not found"
        )

    iframe_src = (
        iframe
        .get(
            "src",
            ""
        )
        .strip()
    )

    if not iframe_src:

        raise RuntimeError(
            "PIB article iframe has empty src"
        )

    iframe_url = urljoin(
        outer_url,
        iframe_src
    )

    log(
        f"FETCH ARTICLE FRAME: "
        f"{iframe_url}"
    )

    # =====================================================
    # STEP 4
    # FETCH ACTUAL ARTICLE FRAME
    # =====================================================

    time.sleep(
        0.3
    )

    iframe_response = session.get(
        iframe_url,
        timeout=40
    )

    log(
        f"ARTICLE FRAME HTTP "
        f"{iframe_response.status_code} | "
        f"{len(iframe_response.content):,} bytes"
    )

    iframe_response.raise_for_status()

    iframe_html = (
        iframe_response.text
    )

    article_soup = BeautifulSoup(
        iframe_html,
        "html.parser"
    )

    # =====================================================
    # STEP 5
    # FRAME TITLE
    # =====================================================

    frame_title = find_article_title(
        article_soup,
        title
    )

    if is_good_title(
        frame_title
    ):

        title = frame_title

    # =====================================================
    # STEP 6
    # ARTICLE CONTENT
    # =====================================================

    content = extract_article_frame_content(
        article_soup
    )

    # =====================================================
    # STEP 7
    # DATE
    #
    # IMPORTANT:
    #
    # Do NOT blindly use the first date found in article
    # prose. A date inside the article can refer to an event.
    #
    # Priority:
    #
    # 1. PIB Posted On date
    # 2. PIB article date fallback
    # 3. Archive date
    # =====================================================

    frame_text = article_soup.get_text(
        "\n",
        strip=True
    )

    outer_text = outer_soup.get_text(
        "\n",
        strip=True
    )

    date = extract_posted_date(
        frame_text
    )

    if not date:

        date = extract_posted_date(
            outer_text
        )

    if not date:

        date = extract_pib_article_date(
            frame_text
        )

    if not date:

        date = parse_date(
            release.get(
                "date",
                ""
            )
        )

    # =====================================================
    # STEP 8
    # REGION
    # =====================================================

    region = ""

    region_match = re.search(
        r"Region\s*:\s*([^\n]+)",
        frame_text,
        re.IGNORECASE
    )

    if region_match:

        region = (
            region_match
            .group(1)
            .strip()
        )

    # =====================================================
    # STEP 9
    # BUILD ARTICLE
    # =====================================================

    article = {

        "prid":
            release["prid"],

        "source":
            "PIB",

        "title":
            title,

        "date":
            (
                date.isoformat()
                if date
                else ""
            ),

        "ministry":
            release.get(
                "ministry",
                ""
            ),

        "region":
            region,

        "url":
            outer_url,

        "article_url":
            iframe_url,

        "content":
            content,

        "collected_at":
            datetime.now().isoformat(),

    }

    return article


# =========================================================
# ARTICLE VALIDATION
# =========================================================

def article_is_valid(
    article
):

    if not isinstance(
        article,
        dict
    ):

        return False

    title = (
        article
        .get(
            "title",
            ""
        )
        .strip()
    )

    content = (
        article
        .get(
            "content",
            ""
        )
        .strip()
    )

    date = (
        article
        .get(
            "date",
            ""
        )
        .strip()
    )

    # -----------------------------------------------------
    # Date must exist
    # -----------------------------------------------------

    if not date:

        return False

    # -----------------------------------------------------
    # Title must be meaningful
    # -----------------------------------------------------

    if not is_good_title(
        title
    ):

        return False

    # -----------------------------------------------------
    # PIB can publish very short releases.
    #
    # 300 characters was TOO HIGH.
    # We have already verified a valid 180-character PIB
    # release.
    # -----------------------------------------------------

    if len(content) < 80:

        return False

    return True


# =========================================================
# DETERMINE WHETHER EXISTING RECORD NEEDS REPAIR
# =========================================================

def needs_repair(
    article
):

    if not article:

        return True

    title = (
        article
        .get(
            "title",
            ""
        )
        .strip()
    )

    content = (
        article
        .get(
            "content",
            ""
        )
        .strip()
    )

    date = (
        article
        .get(
            "date",
            ""
        )
        .strip()
    )

    if not is_good_title(
        title
    ):

        return True

    if len(content) < 80:

        return True

    if not date:

        return True

    return False


# =========================================================
# BUILD 7-DAY OUTPUT
# =========================================================

def build_latest_output(
    database
):

    today = datetime.now().date()

    oldest_date = (
        today -
        timedelta(
            days=LOOKBACK_DAYS
        )
    )

    latest = []

    for article in database.values():

        article_date = parse_date(
            article.get(
                "date",
                ""
            )
        )

        if not article_date:

            continue

        if (
            oldest_date
            <= article_date
            <= today
        ):

            latest.append(
                article
            )

    # -----------------------------------------------------
    # Sort newest first
    # -----------------------------------------------------

    latest.sort(
        key=lambda x: (
            x.get(
                "date",
                ""
            ),
            x.get(
                "prid",
                ""
            )
        ),
        reverse=True
    )

    # -----------------------------------------------------
    # Save output atomically
    # -----------------------------------------------------

    temp_file = (
        DATA_DIR /
        "pib_latest_7_days.tmp"
    )

    try:

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                latest,
                f,
                ensure_ascii=False,
                indent=2
            )

            f.flush()

        temp_file.replace(
            OUTPUT_FILE
        )

        log(
            f"7-DAY OUTPUT: "
            f"{len(latest)} articles"
        )

    except Exception as e:

        error_log(
            f"7-DAY OUTPUT ERROR: {e}"
        )

    return latest


# =========================================================
# MAIN SCRAPER
# =========================================================

def main():

    log(
        "=========================================="
    )

    log(
        "PIB RESUME + REPAIR SCRAPER"
    )

    log(
        "=========================================="
    )

    today = datetime.now().date()

    oldest_date = (
        today -
        timedelta(
            days=LOOKBACK_DAYS
        )
    )

    log(
        f"TARGET DATE: {today}"
    )

    log(
        f"OLDEST ALLOWED: {oldest_date}"
    )

    # =====================================================
    # LOAD EXISTING DATABASE
    # =====================================================

    database = load_database()

    initial_count = len(
        database
    )

    # =====================================================
    # FETCH PIB ARCHIVE
    # =====================================================

    try:

        html = fetch_page(
            START_URL
        )

        releases = extract_release_links(
            html
        )

    except Exception as e:

        error_log(
            f"ARCHIVE ERROR: {e}"
        )

        build_latest_output(
            database
        )

        return

    log(
        f"ARCHIVE DISCOVERED: "
        f"{len(releases)} releases"
    )

    # =====================================================
    # FETCH HINDI PIB ARCHIVE
    # =====================================================

    try:

        hindi_html = fetch_page(
            HINDI_URL
        )

        hindi_releases = extract_release_links(
            hindi_html
        )

        # Merge: add Hindi releases not already seen
        seen_prids = {r.get("prid") for r in releases}

        for hr in hindi_releases:

            if hr.get("prid") not in seen_prids:

                releases.append(hr)

                seen_prids.add(
                    hr.get("prid")
                )

        log(
            f"AFTER HINDI MERGE: "
            f"{len(releases)} total releases"
        )

    except Exception as e:

        error_log(
            f"HINDI ARCHIVE ERROR: {e}"
        )

    # =====================================================
    # FILTER TO 7-DAY WINDOW
    # =====================================================

    candidates = []

    for release in releases:

        article_date = parse_date(
            release.get(
                "date",
                ""
            )
        )

        if not article_date:

            continue

        if (
            oldest_date
            <= article_date
            <= today
        ):

            candidates.append(
                release
            )

    log(
        f"7-DAY CANDIDATES: "
        f"{len(candidates)}"
    )

    # =====================================================
    # TEST LIMIT
    # =====================================================

    if TEST_LIMIT is None:

        process_candidates = (
            candidates
        )

    else:

        process_candidates = (
            candidates[
                :TEST_LIMIT
            ]
        )

        log(
            f"TEST MODE: Processing "
            f"only {len(process_candidates)} "
            f"of {len(candidates)} candidates"
        )

    # =====================================================
    # COUNTERS
    # =====================================================

    new_saved = 0

    repaired = 0

    skipped = 0

    failed = 0

    # =====================================================
    # PROCESS
    # =====================================================

    total_to_process = len(
        process_candidates
    )

    for index, release in enumerate(
        process_candidates,
        start=1
    ):

        prid = release[
            "prid"
        ]

        existing = database.get(
            prid
        )

        # -------------------------------------------------
        # EXISTING VALID RECORD
        # -------------------------------------------------

        if (
            existing
            and
            not needs_repair(
                existing
            )
        ):

            log(
                f"[{index}/{total_to_process}] "
                f"SKIP VALID: PRID={prid}"
            )

            skipped += 1

            continue

        # -------------------------------------------------
        # REPAIR OR NEW
        # -------------------------------------------------

        if existing:

            action = "REPAIR"

        else:

            action = "NEW"

        log(
            f"[{index}/{total_to_process}] "
            f"{action}: PRID={prid}"
        )

        try:

            article = fetch_release(
                release
            )

            # ---------------------------------------------
            # Validate
            # ---------------------------------------------

            if not article_is_valid(
                article
            ):

                failed += 1

                error_log(
                    f"INVALID ARTICLE: "
                    f"PRID={prid} | "
                    f"TITLE="
                    f"{article.get('title', '')} | "
                    f"DATE="
                    f"{article.get('date', '')} | "
                    f"CONTENT_LENGTH="
                    f"{len(article.get('content', ''))}"
                )

                continue

            # ---------------------------------------------
            # Save into database
            # ---------------------------------------------

            database[
                prid
            ] = article

            if save_database(
                database
            ):

                if existing:

                    repaired += 1

                    log(
                        f"REPAIRED: "
                        f"PRID={prid}"
                    )

                else:

                    new_saved += 1

                    log(
                        f"SAVED: "
                        f"PRID={prid}"
                    )

            else:

                failed += 1

                error_log(
                    f"DATABASE SAVE FAILED: "
                    f"PRID={prid}"
                )

        except Exception as e:

            failed += 1

            error_log(
                f"ARTICLE ERROR: "
                f"PRID={prid} | "
                f"{e}"
            )

        # -------------------------------------------------
        # Delay between articles
        # -------------------------------------------------

        time.sleep(
            0.2
        )

    # =====================================================
    # BUILD 7-DAY FILE
    # =====================================================

    latest = build_latest_output(
        database
    )

    final_count = len(
        database
    )

    # =====================================================
    # FINAL REPORT
    # =====================================================

    log(
        "=========================================="
    )

    log(
        "RUN COMPLETED"
    )

    log(
        f"INITIAL DATABASE: "
        f"{initial_count}"
    )

    log(
        f"FINAL DATABASE:   "
        f"{final_count}"
    )

    log(
        f"NEW SAVED:        "
        f"{new_saved}"
    )

    log(
        f"REPAIRED:         "
        f"{repaired}"
    )

    log(
        f"VALID SKIPPED:    "
        f"{skipped}"
    )

    log(
        f"FAILED:           "
        f"{failed}"
    )

    log(
        f"7-DAY OUTPUT:     "
        f"{len(latest)}"
    )

    log(
        f"DATABASE FILE:    "
        f"{DATABASE_FILE}"
    )

    log(
        f"7-DAY FILE:       "
        f"{OUTPUT_FILE}"
    )

    log(
        "=========================================="
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print(
            "SCRAPER STOPPED BY USER."
        )

    except Exception as e:

        print()
        print(
            "FATAL ERROR:",
            e
        )