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
import html


# =========================================================
# CURRENT AFFAIRS SCRAPER
# GKToday
# =========================================================


# =========================================================
# CONFIGURATION
# =========================================================

LOOKBACK_DAYS = 7
REQUEST_DELAY = 0.5

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
# SCRAPER ERROR ALERTS (Telegram)
# =========================================================

def send_alert(msg):
    """Send scraper failure alert to Telegram."""
    try:
        config_path = Path(__file__).resolve().parent / "pipeline_config.json"
        if not config_path.exists():
            config_path = Path(__file__).resolve().parent.parent / "pipeline_config.json"
        if not config_path.exists():
            return
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        token = config.get("telegram_bot_token", "")
        chat_id = config.get("telegram_chat_id", "")
        if not token or not chat_id:
            return
        text = f"⚠️ <b>SCRAPER ALERT</b>\n\n{msg}"
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
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

def scrape_gktoday(existing_db=None):
    """Scrape GKToday current affairs articles (paginated across listing pages + categories)."""
    log("GKTODAY: Starting scrape...")
    articles = []
    skipped = 0

    # Main page + category pages for complete coverage
    base_urls = [
        "https://www.gktoday.in/current-affairs",
        "https://www.gktoday.in/current-affairs/category/india-current-affairs",
        "https://www.gktoday.in/current-affairs/category/government-schemes",
        "https://www.gktoday.in/current-affairs/category/science-technology-current-affairs",
        "https://www.gktoday.in/current-affairs/category/sports-current-affairs",
        "https://www.gktoday.in/current-affairs/category/reports-indexes",
        "https://www.gktoday.in/current-affairs/category/economy-current-affairs",
        "https://www.gktoday.in/current-affairs/category/defence-current-affairs",
        "https://www.gktoday.in/current-affairs/category/international-current-affairs",
        "https://www.gktoday.in/current-affairs/category/awards-honours-persons-news-current-affairs",
        "https://www.gktoday.in/current-affairs/category/summits-conferences",
        "https://www.gktoday.in/current-affairs/category/environment-current-affairs",
        "https://www.gktoday.in/current-affairs/category/places-in-news",
    ]
    cutoff_date = datetime(2026, 6, 1)
    for base in base_urls:
        for pg in range(1, 20):  # Max 20 pages per category
            url = base if pg == 1 else f"{base}/page/{pg}/"
            try:
                resp = requests.get(url, headers=HEADERS, timeout=30)
                resp.raise_for_status()
            except Exception as e:
                break
            soup = BeautifulSoup(resp.text, "html.parser")

            # Find all article items on this page
            items = soup.select(".home-post-item")
            if not items:
                break

            stop_scraping = False
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

                    # Stop if article is older than June 1, 2026
                    if pub_date < cutoff_date:
                        stop_scraping = True
                        break

                    # Generate article ID
                    article_id = f"GKT_{link.split('/')[-2] if link.endswith('/') else link.split('/')[-1]}"

                    # Skip if already in database
                    if existing_db and article_id in existing_db:
                        skipped += 1
                        continue

                    # Fetch full article content from individual page
                    full_content = desc
                    try:
                        time.sleep(0.3)  # Reduced delay
                        article_resp = requests.get(link, headers=HEADERS, timeout=15)
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
                                full_content = full_content[:50000]  # Full content for PowerPoint
                    except Exception as e:
                        error_log(f"GKTODAY: Failed to fetch article content: {e}")

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
            if stop_scraping:
                break
            time.sleep(REQUEST_DELAY)

    log(f"GKTODAY: Scraped {len(articles)} new articles, skipped {skipped} existing")
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
    
    # Scrape all sources with error tracking
    new_articles = []
    alerts = []

    scrapers = [
        ("GKToday", lambda: scrape_gktoday(database)),
    ]

    for name, fn in scrapers:
        try:
            result = fn()
            if not result:
                alerts.append(f"{name}: 0 new articles")
            new_articles.extend(result)
        except Exception as e:
            error_log(f"{name}: CRASHED - {e}")
            alerts.append(f"{name}: CRASHED - {e}")
        time.sleep(REQUEST_DELAY)

    # Send Telegram alerts for empty/failed scrapers
    if alerts:
        alert_msg = "\n".join(f"• {a}" for a in alerts)
        log(f"ALERTS: {alert_msg}")
        send_alert(alert_msg)
    
    # Add new articles to database
    new_saved = 0
    duplicates = 0
    updated = 0
    
    for article in new_articles:
        article_id = article["id"]
        
        if article_id in database:
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
    
    if save_database(database):
        log(f"Database saved: {len(database)} total articles")
    
    latest = build_latest_output(database)
    
    log("==========================================")
    log("RUN COMPLETED")
    log(f"INITIAL DATABASE: {initial_count}")
    log(f"NEW SCRAPED:      {len(new_articles)}")
    log(f"NEW SAVED:        {new_saved}")
    log(f"UPDATED:          {updated}")
    log(f"DUPLICATES:       {duplicates}")
    log(f"FINAL DATABASE:   {len(database)}")
    log(f"7-DAY OUTPUT:     {len(latest)}")
    log(f"ALERTS:           {len(alerts)}")
    log("==========================================")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSCRAPER STOPPED BY USER.")
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
