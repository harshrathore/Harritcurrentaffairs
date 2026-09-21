import re
from datetime import datetime, date
from typing import Optional
from bs4 import BeautifulSoup

from . import config


def parse_aspnet_form(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    form_data = {}
    for inp in soup.find_all("input"):
        name = inp.get("name")
        if name:
            form_data[name] = inp.get("value", "")
    return form_data


def parse_listing_releases(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    releases = []
    seen_prids = set()
    current_ministry = ""

    for container in soup.select("ul.num"):
        heading = container.find("h3")
        if heading:
            current_ministry = heading.get_text(" ", strip=True)

        for li in container.find_all("li", recursive=False):
            link = li.find("a", href=True)
            if not link:
                continue
            href = link.get("href", "").strip()
            if "PressReleseDetail" not in href and "PressRelease" not in href:
                continue
            prid = extract_prid_from_url(href)
            if not prid or prid in seen_prids:
                continue
            seen_prids.add(prid)
            title = link.get("title", "").strip() or link.get_text(" ", strip=True)
            li_text = li.get_text(" ", strip=True)
            date_str = extract_posted_date(li_text)
            releases.append({
                "prid": prid,
                "title": title,
                "date": date_str or "",
                "ministry": current_ministry,
                "url": href,
            })
    return releases


def extract_prid_from_url(url: str) -> Optional[int]:
    m = re.search(r"PRID=(\d+)", url, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def extract_prid_from_text(text: str) -> Optional[int]:
    m = re.search(r"Release\s*ID\s*:\s*(\d+)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def parse_date_from_text(text: str) -> Optional[date]:
    if not text:
        return None
    m = re.search(
        r"Posted\s+On\s*:\s*(\d{1,2}\s+\w+\s+\d{4})",
        text, re.IGNORECASE
    )
    if m:
        return _parse_date_str(m.group(1))
    m = re.search(r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})", text, re.IGNORECASE)
    if m:
        return _parse_date_str(m.group(1))
    return None


def _parse_date_str(s: str) -> Optional[date]:
    s = s.strip()
    for fmt in ["%d %b %Y", "%d %B %Y", "%d-%m-%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def extract_posted_date(text: str) -> Optional[str]:
    m = re.search(
        r"Posted\s+On\s*:\s*(\d{1,2}\s+\w+\s+\d{4})",
        text, re.IGNORECASE
    )
    if m:
        d = _parse_date_str(m.group(1))
        return d.isoformat() if d else None
    return None


def extract_posted_datetime(text: str) -> tuple:
    m = re.search(
        r"Posted\s+On\s*:\s*(\d{1,2}\s+\w+\s+\d{4})\s+(\d{1,2}:\d{2}\s*[APap][Mm])",
        text, re.IGNORECASE
    )
    if m:
        d = _parse_date_str(m.group(1))
        return (d.isoformat() if d else None, m.group(2).strip())
    d = extract_posted_date(text)
    return (d, None)


def parse_release_page(html: str, prid: int) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    result = {
        "prid": prid,
        "title": "",
        "publication_date": "",
        "publication_time": "",
        "ministry": "",
        "full_text": "",
        "location": "",
        "canonical_url": f"{config.RELEASE_PAGE_URL}?PRID={prid}&reg={config.DEFAULT_REGION}&lang={config.DEFAULT_LANG}",
    }

    date_div = soup.find(id="PrDateTime")
    if date_div:
        dt_text = date_div.get_text(" ", strip=True)
        pub_date, pub_time = extract_posted_datetime(dt_text)
        result["publication_date"] = pub_date or ""
        result["publication_time"] = pub_time or ""
        loc_m = re.search(r"by\s+PIB\s+(.+)$", dt_text)
        if loc_m:
            result["location"] = loc_m.group(1).strip()

    if not result["publication_date"]:
        date_sub = soup.select_one("div.ReleaseDateSubHeaddateTime")
        if date_sub:
            dt_text = date_sub.get_text(" ", strip=True)
            pub_date, pub_time = extract_posted_datetime(dt_text)
            result["publication_date"] = pub_date or ""
            result["publication_time"] = pub_time or ""
            loc_m = re.search(r"by\s+PIB\s+(.+)$", dt_text)
            if loc_m:
                result["location"] = loc_m.group(1).strip()

    content_div = soup.select_one("div.innner-page-main-about-us-content-right-part")
    if content_div:
        ministry_div = content_div.select_one("div.MinistryNameSubhead")
        if ministry_div:
            result["ministry"] = ministry_div.get_text(" ", strip=True)

        title_div = content_div.select_one("div.event-heading-background")
        if title_div:
            result["title"] = title_div.get_text(" ", strip=True)

        if not result["ministry"]:
            h2s = content_div.find_all("h2")
            if len(h2s) >= 1:
                result["ministry"] = h2s[0].get_text(" ", strip=True)
            if len(h2s) >= 2 and not result["title"]:
                result["title"] = h2s[1].get_text(" ", strip=True)

        bg = content_div.select_one("div.BackgroundRelease")
        if bg:
            paragraphs = []
            for p in bg.find_all(["p", "div", "li"]):
                text = p.get_text(" ", strip=True)
                text = re.sub(r"\s+", " ", text).strip()
                if text and text != "****" and "Release ID" not in text:
                    paragraphs.append(text)
            if paragraphs:
                result["full_text"] = "\n\n".join(paragraphs)
            else:
                result["full_text"] = bg.get_text("\n", strip=True)

    if not result["full_text"]:
        body_ps = soup.select("div.innner-page-main-about-us-content-right-part p")
        if body_ps:
            paragraphs = []
            for p in body_ps:
                text = p.get_text(" ", strip=True)
                text = re.sub(r"\s+", " ", text).strip()
                if text and len(text) > 10:
                    paragraphs.append(text)
            result["full_text"] = "\n\n".join(paragraphs)

    if not result["title"]:
        title_tag = soup.find("title")
        if title_tag:
            t = title_tag.get_text(" ", strip=True)
            t = re.sub(r"\s*[-|]\s*Press\s+Release.*$", "", t, flags=re.IGNORECASE)
            result["title"] = t.strip()

    if not result["publication_date"]:
        body_text = soup.get_text(" ", strip=True)
        pub_date, pub_time = extract_posted_datetime(body_text)
        result["publication_date"] = pub_date or ""
        result["publication_time"] = pub_time or ""

    return result


def parse_ministry_dropdown(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", {"id": "ContentPlaceHolder1_ddlMinistry"})
    if not select:
        return []
    ministries = []
    for opt in select.find_all("option"):
        val = opt.get("value", "").strip()
        text = opt.get_text(" ", strip=True)
        if val and text and val != "0":
            ministries.append({"value": val, "name": text})
    return ministries


def parse_day_dropdown(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", {"id": "ContentPlaceHolder1_ddlday"})
    if not select:
        return []
    days = []
    for opt in select.find_all("option"):
        val = opt.get("value", "").strip()
        if val and val != "0":
            days.append(int(val))
    return days
