import sys
import io

# Set stdout to UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pathlib import Path
import json
import time
import re


# =========================================================
# CURRENT AFFAIRS SCRAPER
# GKToday + Insights IAS + Drishti IAS
# =========================================================


# =========================================================
# CONFIGURATION
# =========================================================

LOOKBACK_DAYS = 7
REQUEST_DELAY = 1.0

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "PIB"

DATABASE_FILE = DATA_DIR / "current_affairs_database.json"
OUTPUT_FILE = DATA_DIR / "current_affairs_latest_7_days.json"
LOG_FILE = DATA_DIR / "current_affairs_scraper.log"
ERROR_LOG_FILE = DATA_DIR / "current_affairs_errors.log"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# =========================================================
# LOGGING
# =========================================================

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass


def error_log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass


# =========================================================
# DATABASE
# =========================================================

def load_database():
    if DATABASE_FILE.exists():
        try:
            with open(DATABASE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_database(database):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DATABASE_FILE, "w", encoding="utf-8") as f:
            json.dump(database, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        error_log(f"DATABASE SAVE FAILED: {e}")
        return False


# =========================================================
# GKTODAY SCRAPER
# =========================================================

def scrape_gktoday():
    """Scrape GKToday current affairs articles (paginated across listing pages)."""
    log("GKTODAY: Starting scrape...")
    articles = []

    base = "https://www.gktoday.in/current-affairs"
    max_pages = 10
    for pg in range(1, max_pages + 1):
        url = base if pg == 1 else f"{base}/page/{pg}/"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            error_log(f"GKTODAY: Failed to fetch page {pg}: {e}")
            break
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find all article items on this page
        items = soup.select(".home-post-item")
        log(f"GKTODAY: Found {len(items)} articles on page {pg}")
        if not items:
            break

        for item in items:
            try:
                # Extract title and link
                title_tag = item.select_one("h3 a")
                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                link = title_tag.get("href", "")
                if not title or not link:
                    continue

                # Extract date
                date_tag = item.select_one(".home-post-data-meta")
                date_str = ""
                if date_tag:
                    date_text = date_tag.get_text(strip=True)
                    date_match = re.search(r"(\w+ \d+, \d{4})", date_text)
                    if date_match:
                        date_str = date_match.group(1)

                category = ""
                cat_tag = item.select_one(".home-post-data-meta a")
                if cat_tag:
                    category = cat_tag.get_text(strip=True)

                # Extract description from listing page (short snippet)
                desc = ""
                desc_tag = item.select_one(".post-data")
                if desc_tag:
                    desc = desc_tag.get_text(strip=True)
                    desc = desc.replace(title, "").strip()
                    desc = desc[:500]

                # Parse date
                pub_date = None
                if date_str:
                    try:
                        pub_date = datetime.strptime(date_str, "%B %d, %Y")
                    except Exception:
                        pass
                if not pub_date:
                    pub_date = datetime.now()

                # Fetch full article content from individual page
                full_content = desc
                try:
                    time.sleep(1)  # Be polite - 1 second delay
                    article_resp = requests.get(link, headers=HEADERS, timeout=30)
                    if article_resp.status_code == 200:
                        article_soup = BeautifulSoup(article_resp.text, "html.parser")
                        content_div = article_soup.select_one(".content-area")
                        if content_div:
                            for tag in content_div.select(
                                "script, style, .related-articles, .social-share, "
                                ".adsbygoogle, .breadcrumb, .post-meta, "
                                ".gktoday-share-box, .a2a_kit"
                            ):
                                tag.decompose()
                            full_content = content_div.get_text(separator=" ", strip=True)
                            full_content = full_content[:2000]  # Limit to 2000 chars
                except Exception as e:
                    error_log(f"GKTODAY: Failed to fetch article content: {e}")

                # Generate article ID
                article_id = f"GKT_{link.split('/')[-2] if link.endswith('/') else link.split('/')[-1]}"

                articles.append({
                    "id": article_id,
                    "source": "GKToday",
                    "title": title,
                    "url": link,
                    "date": pub_date.isoformat(),
                    "category": category,
                    "content": full_content if full_content else desc,
                    "collected_at": datetime.now().isoformat()
                })
            except Exception as e:
                error_log(f"GKTODAY: Error parsing article: {e}")
                continue
        time.sleep(REQUEST_DELAY)

    log(f"GKTODAY: Scraped {len(articles)} articles")
    return articles


# =========================================================
# VISION IAS SCRAPER
# =========================================================

def scrape_visionias():
    """Scrape Vision IAS current affairs articles from news-today page."""
    log("VISIONIAS: Starting scrape...")
    articles = []
    
    # Scrape Vision IAS news-today page directly
    url = "https://visionias.in/current-affairs/news-today"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        error_log(f"VISIONIAS: Failed to fetch page: {e}")
        return articles
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Vision IAS articles have URLs like /current-affairs/news-today/YYYY-MM-DD/category/article-slug
    # Filter for actual article links only
    seen_urls = set()
    
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        title = link.get_text(strip=True)
        
        # Skip if no title or too short (menu items)
        if not title or len(title) < 25:
            continue
        
        # Skip menu/navigation items (Premium, Popular, New, Archive, etc.)
        skip_keywords = ["Premium", "Popular", "New", "Archive", "Workbook", 
                        "Magazine", "Quiz", "Sprint", "Download", "Video",
                        "In Conversation", "Simplified", "Personality", "Budget"]
        if any(kw.lower() in title.lower() for kw in skip_keywords):
            continue
        
        # Must be a news-today article with date pattern
        if "/current-affairs/news-today/" not in href:
            continue
        
        # Extract date from URL pattern: /news-today/YYYY-MM-DD/
        import re
        date_match = re.search(r"/news-today/(\d{4}-\d{2}-\d{2})/", href)
        if not date_match:
            continue
        
        date_str = date_match.group(1)
        
        # Build full URL
        full_url = href if href.startswith("http") else f"https://visionias.in{href}"
        
        # Skip duplicates
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        
        # Parse date
        try:
            pub_date = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            pub_date = datetime.now()
        
        # Extract category from URL (economy, polity-and-governance, etc.)
        category = "Current Affairs"
        cat_match = re.search(r"/news-today/\d{4}-\d{2}-\d{2}/([^/]+)/", href)
        if cat_match:
            category = cat_match.group(1).replace("-", " ").title()
        
        # Generate article ID from URL slug
        slug = href.rstrip("/").split("/")[-1]
        article_id = f"VIAS_{slug[:40]}"
        
        articles.append({
            "id": article_id,
            "source": "Vision IAS",
            "title": title,
            "url": full_url,
            "date": pub_date.isoformat(),
            "category": category,
            "content": "",  # Will be fetched separately if needed
            "collected_at": datetime.now().isoformat()
        })
    
    log(f"VISIONIAS: Found {len(articles)} articles from news-today page")
    
    # Fetch content for each article (limit to 10 most recent)
    for i, article in enumerate(articles[:10]):
        try:
            time.sleep(1)  # Be polite
            art_resp = requests.get(article["url"], headers=HEADERS, timeout=30)
            if art_resp.status_code == 200:
                art_soup = BeautifulSoup(art_resp.text, "html.parser")
                
                # Vision IAS article content is in div.ck-content
                content_div = art_soup.select_one(".ck-content, .article-content, .content-area")
                if content_div:
                    # Remove unwanted elements
                    for tag in content_div.select("script, style, .related-posts, .share-buttons, nav"):
                        tag.decompose()
                    content = content_div.get_text(separator=" ", strip=True)
                    article["content"] = content[:2000]
                    log(f"VISIONIAS: Fetched content for: {article['title'][:50]}")
        except Exception as e:
            error_log(f"VISIONIAS: Failed to fetch article content: {e}")
    
    log(f"VISIONIAS: Scraped {len(articles)} articles total")
    return articles


# =========================================================
# INSIGHTS IAS SCRAPER
# =========================================================

def scrape_insightsonindia():
    """Scrape Insights IAS daily current affairs from per-date pages.

    Each day's CA lives at:
      https://www.insightsonindia.com/YYYY/MM/DD/upsc-current-affairs-DD-monthname-YYYY/
    Topics appear as <h2> headings; content follows inline until the next <h2>.
    """
    log("INSIGHTSIAS: Starting scrape (daily date pages)...")
    articles = []
    seen = set()
    INSIGHTS_DAYS = 15

    today = datetime.now()
    for d in range(INSIGHTS_DAYS):
        date = today - timedelta(days=d)
        y = date.strftime("%Y")
        m = date.strftime("%m")
        day = date.strftime("%d")
        month = date.strftime("%B").lower()  # august
        slug = f"upsc-current-affairs-{day}-{month}-{y}"
        url = f"https://www.insightsonindia.com/{y}/{m}/{day}/{slug}/"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                log(f"INSIGHTSIAS: {url} status {resp.status_code}")
                continue
        except Exception as e:
            error_log(f"INSIGHTSIAS: list fetch {url}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        main = soup.select_one("article, .entry-content, .post-content, main")
        if not main:
            continue

        # Walk block elements in document order, grouping by <h2> article titles
        blocks = main.find_all(["h2", "h3", "h4", "p", "li"])
        cur_title = None
        cur_content = []
        for b in blocks:
            tag = b.name
            txt = b.get_text(strip=True)
            if tag == "h2":
                # flush previous article
                if cur_title and cur_content:
                    content = " ".join(cur_content).strip()
                    if len(content) >= 50:
                        slug_id = re.sub(r"[^a-z0-9]+", "-", cur_title.lower())[:60].strip("-")
                        aid = f"IIAS_{y}{m}{day}_{slug_id}"
                        if aid not in seen:
                            seen.add(aid)
                            articles.append({
                                "id": aid,
                                "source": "Insights IAS",
                                "title": cur_title,
                                "url": url,
                                "date": date.strftime("%Y-%m-%d") + "T00:00:00",
                                "category": "Current Affairs",
                                "content": content[:3000],
                                "collected_at": datetime.now().isoformat()
                            })
                if "post navigation" in txt.lower():
                    cur_title = None
                    cur_content = []
                    continue
                cur_title = txt
                cur_content = []
            elif tag in ("h3", "h4"):
                if cur_title is None:
                    continue
                low = txt.lower()
                if "related articles" in low or "post navigation" in low:
                    # close current article
                    if cur_title and cur_content:
                        content = " ".join(cur_content).strip()
                        if len(content) >= 50:
                            slug_id = re.sub(r"[^a-z0-9]+", "-", cur_title.lower())[:60].strip("-")
                            aid = f"IIAS_{y}{m}{day}_{slug_id}"
                            if aid not in seen:
                                seen.add(aid)
                                articles.append({
                                    "id": aid,
                                    "source": "Insights IAS",
                                    "title": cur_title,
                                    "url": url,
                                    "date": date.strftime("%Y-%m-%d") + "T00:00:00",
                                    "category": "Current Affairs",
                                    "content": content[:3000],
                                    "collected_at": datetime.now().isoformat()
                                })
                    cur_title = None
                    cur_content = []
                    continue
                # section header (GS Paper 2, CME, etc.) -> skip text
                continue
            else:  # p, li
                if cur_title is None:
                    continue
                if txt:
                    cur_content.append(txt)
        # flush last article
        if cur_title and cur_content:
            content = " ".join(cur_content).strip()
            if len(content) >= 50:
                slug_id = re.sub(r"[^a-z0-9]+", "-", cur_title.lower())[:60].strip("-")
                aid = f"IIAS_{y}{m}{day}_{slug_id}"
                if aid not in seen:
                    seen.add(aid)
                    articles.append({
                        "id": aid,
                        "source": "Insights IAS",
                        "title": cur_title,
                        "url": url,
                        "date": date.strftime("%Y-%m-%d") + "T00:00:00",
                        "category": "Current Affairs",
                        "content": content[:3000],
                        "collected_at": datetime.now().isoformat()
                    })

    log(f"INSIGHTSIAS: Scraped {len(articles)} articles")
    return articles


def scrape_drishtiias():
    """Scrape Drishti IAS daily current affairs.

    Drishti publishes daily CA under:
      https://www.drishtiias.com/current-affairs-news-analysis-editorials/news-analysis/DD-MM-YYYY
    Each date page lists article links under
      /daily-updates/daily-news-analysis/<slug>
    which are static and individually fetchable.
    """
    log("DRISHTIIAS: Starting scrape...")
    articles = []
    seen_slugs = set()
    seen_titles = set()
    DRISHTI_DAYS = 15

    # Skip already-known articles for fast re-runs
    try:
        existing_db = load_database()
    except Exception:
        existing_db = {}

    base = ("https://www.drishtiias.com/"
            "current-affairs-news-analysis-editorials/news-analysis")
    today = datetime.now()

    for d in range(DRISHTI_DAYS):
        date = today - timedelta(days=d)
        date_str = date.strftime("%d-%m-%Y")
        list_url = f"{base}/{date_str}"
        try:
            resp = requests.get(list_url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                log(f"DRISHTIIAS: list {date_str} status {resp.status_code}")
                continue
        except Exception as e:
            error_log(f"DRISHTIIAS: list fetch {date_str}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for a in soup.select('a[href*="/daily-updates/daily-news-analysis/"]'):
            href = a.get("href", "")
            if href.startswith("/"):
                href = "https://www.drishtiias.com" + href
            if "/daily-updates/daily-news-analysis/" in href:
                links.append(href)
        links = list(dict.fromkeys(links))
        log(f"DRISHTIIAS: {date_str} -> {len(links)} article links")

        for link in links:
            slug = link.rstrip("/").split("/")[-1]
            if not slug or slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            aid = f"DIAS_{slug[:60]}"
            if aid in existing_db and len(existing_db[aid].get("content", "")) > 100:
                continue
            try:
                art = requests.get(link, headers=HEADERS, timeout=30)
                if art.status_code != 200:
                    continue
                asoup = BeautifulSoup(art.text, "html.parser")
                title = ""
                h1 = asoup.select_one("h1")
                if h1:
                    title = h1.get_text(strip=True)
                if not title and asoup.title:
                    title = asoup.title.get_text(strip=True)
                title = re.split(r"\s*\|\s*Drishti", title)[0].strip()
                if not title:
                    title = slug.replace("-", " ").title()
                norm_title = re.sub(r"\s+", " ", title.lower()).strip()
                if norm_title in seen_titles:
                    continue
                seen_titles.add(norm_title)
                content = ""
                for sel in ["article", ".field--name-body",
                            ".node__content", ".content", "main"]:
                    c = asoup.select_one(sel)
                    if c:
                        for tag in c.select("script, style, .related-posts, nav, footer"):
                            tag.decompose()
                        content = c.get_text(separator=" ", strip=True)
                        if len(content) > 100:
                            break
                articles.append({
                    "id": aid,
                    "source": "Drishti IAS",
                    "title": title,
                    "url": link,
                    "date": date.strftime("%Y-%m-%d") + "T00:00:00",
                    "category": "Current Affairs",
                    "content": content[:2000],
                    "collected_at": datetime.now().isoformat()
                })
            except Exception as e:
                error_log(f"DRISHTIIAS: article {link}: {e}")
            time.sleep(0.5)

    log(f"DRISHTIIAS: Scraped {len(articles)} articles total")
    return articles


# =========================================================
# BUILD 7-DAY OUTPUT
# =========================================================

def build_latest_output(database):
    """Build output file with articles from last 7 days."""
    cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    latest = {}
    
    for key, article in database.items():
        try:
            pub_date = datetime.fromisoformat(article["date"])
            if pub_date.tzinfo:
                pub_date = pub_date.replace(tzinfo=None)
            if pub_date >= cutoff:
                latest[key] = article
        except:
            continue
    
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(latest, f, ensure_ascii=False, indent=2)
    except Exception as e:
        error_log(f"Failed to write 7-day output: {e}")
    
    return latest


# =========================================================
# MAIN
# =========================================================

def main():
    log("==========================================")
    log("CURRENT AFFAIRS SCRAPER - STARTING")
    log("==========================================")
    
    # Load existing database
    database = load_database()
    initial_count = len(database)
    log(f"Existing database: {initial_count} articles")
    
    # Scrape all sources
    new_articles = []
    
    # GKToday
    gktoday_articles = scrape_gktoday()
    new_articles.extend(gktoday_articles)
    time.sleep(REQUEST_DELAY)
    
    # Insights IAS
    insightsias_articles = scrape_insightsonindia()
    new_articles.extend(insightsias_articles)
    time.sleep(REQUEST_DELAY)
    
    # Drishti IAS
    drishtiias_articles = scrape_drishtiias()
    new_articles.extend(drishtiias_articles)
    
    # Add new articles to database
    new_saved = 0
    duplicates = 0
    updated = 0
    
    for article in new_articles:
        article_id = article["id"]
        
        if article_id in database:
            # Update if existing article has short content
            existing = database[article_id]
            if len(existing.get("content", "")) < 500 and len(article.get("content", "")) > len(existing.get("content", "")):
                database[article_id] = article
                updated += 1
                log(f"UPDATED: {article['source']} | {article['title'][:60]}")
            else:
                duplicates += 1
            continue
        
        database[article_id] = article
        new_saved += 1
        log(f"SAVED: {article['source']} | {article['title'][:60]}")
    
    # Save database
    if save_database(database):
        log(f"Database saved: {len(database)} total articles")
    
    # Build 7-day output
    latest = build_latest_output(database)
    
    # Report
    log("==========================================")
    log("RUN COMPLETED")
    log(f"INITIAL DATABASE: {initial_count}")
    log(f"NEW SCRAPED:      {len(new_articles)}")
    log(f"NEW SAVED:        {new_saved}")
    log(f"UPDATED:          {updated}")
    log(f"DUPLICATES:       {duplicates}")
    log(f"FINAL DATABASE:   {len(database)}")
    log(f"7-DAY OUTPUT:     {len(latest)}")
    log("==========================================")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSCRAPER STOPPED BY USER.")
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
