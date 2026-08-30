# =========================================================
# UTKARSH YOUTUBE CURRENT AFFAIRS PIPELINE
# Full pipeline: auto-pick day's video -> Hindi transcript
# -> translate to English -> parse into individual items
# -> send each as a separate Telegram message.
# Integrated into run_all.py (step 4).
# =========================================================
import os
import re
import time
import json
import datetime
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi
from deep_translator import GoogleTranslator
import requests

_BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_BASE, "pipeline_config.json")
STATE_PATH = os.path.join(_BASE, "utkarsh_state.json")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------- 1. FIND THE DAY'S VIDEO ----------
def find_utkarsh_ca_video(d):
    datestr = f"{d.day} {d.strftime('%B')} {d.year}"
    query = f"ytsearch10:Utkarsh {datestr} Current Affairs Kumar Gaurav Sir"
    with YoutubeDL({"quiet": True, "skip_download": True,
                    "no_warnings": True, "extract_flat": "in_playlist"}) as ydl:
        info = ydl.extract_info(query, download=False)
    best = None
    for e in (info.get("entries") or []):
        t = (e.get("title") or "").lower()
        if datestr.lower() in t and "current affairs" in t:
            best = e
            break
    if not best:
        for e in (info.get("entries") or []):
            if datestr.lower() in (e.get("title") or "").lower():
                best = e
                break
    if best:
        return best.get("id"), best.get("title")
    return None, None


# ---------- 2. TRANSCRIPT (Hindi) ----------
def get_hindi(vid):
    api = YouTubeTranscriptApi()
    fetched = api.fetch(vid, languages=["hi"])
    segs = fetched.snippets if hasattr(fetched, "snippets") else fetched
    return " ".join(s.text for s in segs)


# ---------- 3. TRANSLATE (resume-able) ----------
def translate(hindi, cache_path):
    chunks, cur = [], ""
    for w in hindi.split(" "):
        if len(cur) + len(w) + 1 > 700:
            chunks.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        chunks.append(cur)

    done = 0
    out = []
    if os.path.exists(cache_path):
        out = [l for l in open(cache_path, encoding="utf-8").read().split("\n") if l != ""]
        done = len(out)
        print(f"[utkarsh] Resuming translation: {done}/{len(chunks)} chunks done")

    tr = GoogleTranslator(source="hi", target="en")
    for i in range(done, len(chunks)):
        ok = False
        for a in range(5):
            try:
                t = tr.translate(chunks[i])
                ok = True
                break
            except Exception:
                time.sleep(3 * (a + 1))
        text = t if ok else f"[TR_ERR {i}]"
        out.append(text)
        with open(cache_path, "a", encoding="utf-8") as f:
            f.write(text + "\n")
        time.sleep(3.5)
    return "\n\n".join(out)


# ---------- 4. PARSE INTO ITEMS ----------
_NUMW = r"(to do a task|\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
_TITLE_CLEAN = re.compile(
    r"^(do a task\.?\s*)?(first,?\s*friends,?|recently,?\s*friends,?|look\s+friends,?|so,?|ok\?,?|"
    r"let's\s+question\s+number\s+\w+\.?\s*|see\s+question\s+number\s+\w+\.?\s*|"
    r"coming\s+to\s+question\s+number\s+\w+\.?\s*|next\s+question\s+is,?\s*|"
    r"let's\s+talk\s+about\s+question\s+number\s+\w+\.?\s*)",
    re.I,
)


def parse_ca(en_text):
    # Only parse the DAILY section (skip static-GK Five-Year-Plan intro)
    m0 = re.search(r"(?i)important headlines", en_text)
    if m0:
        en_text = en_text[m0.start():]
    # Normalize every transition to one delimiter (avoids double-splits)
    norm = re.sub(r"(?i)(next\s+question\s*,?\s*)?question\s+number\s+\w+",
                  " |||ITEM||| ", en_text)
    norm = re.sub(r"(?i)next\s+question\s+is,?", " |||ITEM||| ", norm)
    parts = norm.split(" |||ITEM||| ")
    items = []
    for seg in parts[1:]:
        seg = seg.replace("\n", " ")
        seg = re.sub(r"^\s*" + _NUMW + r"\.?\s*", "", seg, flags=re.I)
        seg = seg.lstrip(". ").strip()
        if not seg:
            continue
        sents = [s.strip() for s in re.split(r"(?<=[.?!])\s+", seg) if s.strip()]
        if not sents:
            continue
        title = _TITLE_CLEAN.sub("", sents[0]).strip(" .,")
        if not title or len(title) < 10:
            continue
        low = title.lower()
        if low.startswith(("lallan", "do a task")):
            continue
        if len(title) > 170:
            title = title[:170] + "..."
        bullets = sents[1:]
        items.append((title, bullets))
    return items


# ---------- 5. SEND ----------
def _send_one(token, chat, msg):
    for attempt in range(6):
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat, "text": msg},
                timeout=30,
            )
            j = r.json()
            if r.status_code == 200 and j.get("ok"):
                return True
            if r.status_code == 429 or "Too Many Requests" in str(j):
                ra = 5
                try:
                    ra = int(j.get("parameters", {}).get("retry_after", 5))
                except Exception:
                    pass
                time.sleep(ra + 1)
                continue
            if attempt < 5:
                time.sleep(2 * (attempt + 1))
                continue
            return False
        except Exception:
            if attempt < 5:
                time.sleep(2 * (attempt + 1))
                continue
            return False
    return False


def _chunk_msg(title, bullets, limit=3900):
    base = f"{title}\n"
    blocks, buf = [], base
    for b in bullets:
        line = "- " + b + "\n"
        if len(buf) + len(line) > limit and buf != base:
            blocks.append(buf)
            buf = base + line
        else:
            buf += line
    if buf:
        blocks.append(buf)
    return blocks


def send_items(items, config, source_url):
    token = config["telegram_bot_token"]
    chat = config["telegram_chat_id"]
    total = len(items)
    sent = 0
    # Intro message
    intro = f"📰 Utkarsh Daily Current Affairs\nSource: {source_url}"
    if _send_one(token, chat, intro):
        sent += 1
    time.sleep(1.5)
    for idx, (title, bullets) in enumerate(items, 1):
        blocks = _chunk_msg(f"{idx}/{total}  {title}", bullets)
        for i, blk in enumerate(blocks):
            label = f"\n[part {i+1}/{len(blocks)}]" if len(blocks) > 1 else ""
            if _send_one(token, chat, blk + label):
                sent += 1
            time.sleep(1.5)
    return sent


# ---------- MAIN ----------
def main():
    cfg = load_config()
    today = datetime.date.today()
    datekey = today.isoformat()
    state = {}
    if os.path.exists(STATE_PATH):
        try:
            state = json.load(open(STATE_PATH))
        except Exception:
            state = {}
    if state.get(datekey):
        print(f"[utkarsh] Already processed {datekey} -> {state[datekey]}")
        return

    vid, title = find_utkarsh_ca_video(today)
    if not vid:
        print(f"[utkarsh] No video found for {datekey}")
        return
    print(f"[utkarsh] Found: {title} ({vid})")
    source_url = f"https://www.youtube.com/watch?v={vid}"

    cache_path = f"utkarsh_cache_{datekey}.txt"
    hindi = get_hindi(vid)
    print(f"[utkarsh] Hindi transcript chars: {len(hindi)}")
    en = translate(hindi, cache_path)
    print(f"[utkarsh] English chars: {len(en)}")
    items = parse_ca(en)
    print(f"[utkarsh] Parsed items: {len(items)}")
    sent = send_items(items, cfg, source_url)
    print(f"[utkarsh] Sent messages: {sent}")

    # Cleanup: drop translation cache, keep dedup state
    try:
        os.remove(cache_path)
    except Exception:
        pass
    state[datekey] = vid
    json.dump(state, open(STATE_PATH, "w"))
    print(f"[utkarsh] Done for {datekey}")


if __name__ == "__main__":
    main()
