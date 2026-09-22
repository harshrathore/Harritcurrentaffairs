# =========================================================
# DEDUPLICATION MODULE
# Prevents sending the same content to Telegram twice
# =========================================================

import json
import hashlib
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "PIB"
DEDUP_FILE = DATA_DIR / "sent_messages.json"


def _load():
    if DEDUP_FILE.exists():
        try:
            with open(DEDUP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"sent": {}, "last_updated": ""}
    return {"sent": {}, "last_updated": ""}


def _save(state):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now().isoformat()
    temp = DEDUP_FILE.with_suffix(".tmp")
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    temp.replace(DEDUP_FILE)


def fingerprint(text):
    """Create a content fingerprint from text."""
    clean = " ".join(text.lower().split())
    return hashlib.md5(clean.encode("utf-8")).hexdigest()


def article_fingerprint(article):
    """Create a fingerprint for an article dict."""
    title = article.get("title", "").strip()
    date = article.get("date", "")[:10]
    source = article.get("source", "")
    key = f"{source}|{date}|{title}"
    return fingerprint(key)


def is_sent(key):
    """Check if a key has already been sent."""
    state = _load()
    return key in state.get("sent", {})


def mark_sent(key, info=""):
    """Mark a key as sent."""
    state = _load()
    state.setdefault("sent", {})[key] = {
        "time": datetime.now().isoformat(),
        "info": info,
    }
    _save(state)


def is_article_sent(article):
    """Check if an article has already been sent."""
    fp = article_fingerprint(article)
    return is_sent(fp)


def mark_article_sent(article, info=""):
    """Mark an article as sent."""
    fp = article_fingerprint(article)
    mark_sent(fp, info)


def is_file_sent(filename, article_count):
    """Check if a file with same name and count was already sent."""
    key = fingerprint(f"{filename}|{article_count}")
    return is_sent(key)


def mark_file_sent(filename, article_count, info=""):
    """Mark a file as sent."""
    key = fingerprint(f"{filename}|{article_count}")
    mark_sent(key, info)


def get_sent_count():
    """Get total number of sent items tracked."""
    state = _load()
    return len(state.get("sent", {}))


def cleanup_old(days=30):
    """Remove entries older than N days."""
    state = _load()
    cutoff = datetime.now().timestamp() - (days * 86400)
    sent = state.get("sent", {})
    cleaned = {}
    for k, v in sent.items():
        try:
            t = datetime.fromisoformat(v.get("time", "")).timestamp()
            if t > cutoff:
                cleaned[k] = v
        except Exception:
            cleaned[k] = v
    state["sent"] = cleaned
    _save(state)
    return len(sent) - len(cleaned)
