import sys, os, json, re, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from current_affairs_scraper import scrape_pmfias
import telegram_sender
from run_pipeline import load_config, categorize, extract_key_points, load_dedup, save_dedup, log

config = load_config()
dedup = load_dedup(config)

pmfias = scrape_pmfias()
log("PMF IAS scraped: %d articles" % len(pmfias), config)

sent_count = 0
skipped = 0
failed = 0

for article in pmfias:
    title = article.get("title", "")
    content = article.get("content", "")
    url = article.get("url", "")
    date = article.get("date", "")
    aid = "pmfias|" + url

    if aid in dedup:
        skipped += 1
        continue

    domain, exams = categorize(title)
    analysis = {
        "exams": exams,
        "source": "PMF IAS",
        "domain": domain,
        "link": url,
    }
    key_points = extract_key_points(content, 3)

    result = telegram_sender.send_text_to_telegram(title, content, analysis, key_points, config)
    if result["success"]:
        dedup[aid] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_dedup(dedup, config)
        sent_count += 1
        log("SENT | PMF IAS | %s" % title[:60], config)
    else:
        failed += 1
        log("FAILED | %s | %s" % (title[:60], result["message"]), config)
    time.sleep(1)

log("DONE | Sent: %d | Skipped (already sent): %d | Failed: %d" % (sent_count, skipped, failed), config)
