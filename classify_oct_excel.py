"""Classify October 2026 current affairs into 7 exam-friendly headings.

Categories: Indian / International / Space / Defense / Economic / Prizes / Games
Stage 1: classify extracted slides -> classified JSON + stats/samples.
"""
import json
import random
import re
from collections import Counter
from functools import lru_cache

SRC = r"D:\Default Project\data\PIB\excel\oct_slides.json"
OUT = r"D:\Default Project\data\PIB\excel\oct_classified.json"

CATS = ["Indian", "International", "Space", "Defense", "Economic", "Prizes", "Games"]

# (keyword, strong)
KW = {
    "Space": [
        ("isro", 1), ("chandrayaan", 1), ("gaganyaan", 1), ("aditya-l1", 1),
        ("aditya l1", 1), ("pslv", 1), ("gslv", 1), ("lvm3", 1), ("sslv", 1),
        ("spadex", 1), ("navic", 1), ("mangalyaan", 1), ("mars orbiter", 1),
        ("space mission", 1), ("space programme", 1), ("space program", 1),
        ("space station", 1), ("international space station", 1),
        ("space telescope", 1), ("nasa", 1), ("spacex", 1), ("asteroid", 1),
        ("exoplanet", 1), ("astronaut", 1), ("cosmonaut", 1), ("spacewalk", 1),
        ("skyroot", 1), ("agnikul", 1), ("nsil", 1), ("in-space", 1),
        ("satellite launch", 1), ("lunar mission", 1), ("solar mission", 1),
        ("gaganyaan", 1), ("deep space", 1), ("satellite", 0), ("rocket", 0),
        ("orbit", 0), ("lunar", 0), ("moon", 0), ("esa", 0), ("comet", 0),
        ("galaxy", 0), ("astronomy", 0), ("space", 0), ("launch vehicle", 0),
        ("space sector", 0), ("space technology", 0), ("remote sensing", 0),
        ("geospatial", 0), ("solar eruption", 0), ("solar wind", 0),
        ("juno", 1), ("jupiter", 1), ("saturn", 1), ("mars", 1), ("venus", 1),
        ("mercury", 1), ("neptune", 1), ("uranus", 1), ("planetary", 1),
        ("dwarf planet", 1), ("white dwarf", 1), ("black hole", 1), ("nebula", 1),
        ("supernova", 1), ("cosmic", 0), ("observatory", 0), ("telescope", 0),
        ("rocket launch", 1), ("space agency", 1), ("space research", 1),
    ],
    "Defense": [
        ("defence", 1), ("defense", 1), ("drdo", 1), ("missile", 1),
        ("brahmos", 1), ("agni", 1), ("prithvi", 1), ("pinaka", 1),
        ("tejas", 1), ("rafale", 1), ("warship", 1), ("submarine", 1),
        ("aircraft carrier", 1), ("fighter jet", 1), ("armed forces", 1),
        ("indian army", 1), ("indian navy", 1), ("indian air force", 1),
        ("military", 1), ("coast guard", 1), ("bsf", 1), ("crpf", 1),
        ("itbp", 1), ("cisf", 1), ("hypersonic", 1), ("warhead", 1),
        ("artillery", 1), ("defence ministry", 1), ("ministry of defence", 1),
        ("raksha", 1), ("chief of defence", 1), ("tri-service", 1),
        ("military exercise", 1), ("airstrike", 1), ("naval ship", 1),
        ("ins", 1), ("air marshal", 1), ("chief of the air staff", 1),
        ("chief of army staff", 1), ("chief of naval staff", 1),
        ("gallantry", 1), ("param vir chakra", 1), ("shaurya chakra", 1),
        ("army", 0), ("navy", 0), ("air force", 0), ("soldier", 0),
        ("paramilitary", 0), ("nsa", 0), ("ammunition", 0), ("border", 0),
        ("ceasefire", 0), ("drone", 0), ("radar", 0), ("armed", 0),
        ("troops", 0), ("battalion", 0), ("regiment", 0), ("war", 0),
        ("nuclear", 0), ("ballistic", 0), ("strategic", 0),
        ("air defence", 1), ("air defense", 1), ("cruise missile", 1),
    ],
    "Economic": [
        ("economy", 1), ("economic", 1), ("gdp", 1),
        ("gross domestic product", 1), ("inflation", 1), ("cpi", 1),
        ("wpi", 1), ("rbi", 1), ("reserve bank", 1), ("repo rate", 1),
        ("monetary policy", 1), ("banking", 1), ("npa", 1), ("budget", 1),
        ("fiscal", 1), ("gst", 1), ("income tax", 1), ("rupee", 1),
        ("forex", 1), ("export", 1), ("import", 1), ("tariff", 1),
        ("stock market", 1), ("sensex", 1), ("nifty", 1), ("sebi", 1),
        ("ipo", 1), ("fdi", 1), ("manufacturing", 1), ("msme", 1),
        ("disinvestment", 1), ("privatisation", 1), ("privatization", 1),
        ("mutual fund", 1), ("gold price", 1), ("crude oil", 1),
        ("oil price", 1), ("trade agreement", 1), ("free trade", 1),
        ("gdp growth", 1), ("per capita income", 1), ("unemployment", 1),
        ("digital payment", 1), ("upi", 1), ("repo", 1), ("reverse repo", 1),
        ("foreign exchange", 1), ("current account deficit", 1),
        ("fiscal deficit", 1), ("capital expenditure", 1),
        ("wholesale price", 1), ("consumer price", 1), ("bank rate", 1),
        ("bank", 0), ("credit", 0), ("loan", 0), ("finance", 0),
        ("financial", 0), ("tax", 0), ("customs", 0), ("trade", 0),
        ("investment", 0), ("industry", 0), ("industrial", 0),
        ("startup", 0), ("insurance", 0), ("pension", 0), ("commodity", 0),
        ("market", 0), ("employment", 0), ("wage", 0), ("agriculture", 0),
        ("farmer", 0), ("crop", 0), ("food processing", 0),
        ("supply chain", 0), ("logistics", 0), ("infrastructure", 0),
        ("shipping", 0), ("aviation", 0), ("telecom", 0), ("business", 0),
        ("company", 0), ("companies", 0), ("revenue", 0), ("subsidy", 0),
    ],
    "Prizes": [
        ("award", 1), ("awards", 1), ("prize", 1), ("prizes", 1),
        ("nobel", 1), ("padma", 1), ("bharat ratna", 1), ("vir chakra", 1),
        ("param vir chakra", 1), ("maha vir chakra", 1), ("shaurya chakra", 1),
        ("arjuna award", 1), ("khel ratna", 1), ("dronacharya", 1),
        ("dhyan chand", 1), ("oscar", 1), ("academy award", 1), ("booker", 1),
        ("pulitzer", 1), ("grammy", 1), ("emmy", 1), ("bafta", 1),
        ("sahitya akademi", 1), ("jnanpith", 1), ("vyas samman", 1),
        ("laureate", 1), ("miss world", 1), ("miss universe", 1),
        ("mr world", 1), ("lifetime achievement", 1), ("puraskar", 1),
        ("padak", 1), ("samman", 1), ("gallantry award", 1),
        ("honour", 0), ("honor", 0), ("honoured", 0), ("honored", 0),
        ("felicitated", 0), ("conferred", 0), ("recipient", 0),
        ("medal", 0), ("awardee", 0), ("winner", 0),
    ],
    "Games": [
        ("sports", 1), ("asian games", 1), ("asian para games", 1),
        ("para games", 1), ("olympics", 1), ("olympic", 1),
        ("paralympics", 1), ("commonwealth games", 1), ("cricket", 1),
        ("football", 1), ("hockey", 1), ("badminton", 1), ("tennis", 1),
        ("kabaddi", 1), ("athletics", 1), ("medal", 1), ("tournament", 1),
        ("championship", 1), ("world cup", 1), ("ipl", 1), ("test match", 1),
        ("odi", 1), ("t20", 1), ("ranji", 1), ("athlete", 1), ("fifa", 1),
        ("icc", 1), ("bcci", 1), ("wrestling", 1), ("boxing", 1),
        ("archery", 1), ("weightlifting", 1), ("chess", 1), ("squash", 1),
        ("table tennis", 1), ("volleyball", 1), ("basketball", 1),
        ("swimming", 1), ("khelo india", 1), ("national games", 1),
        ("grand slam", 1), ("formula one", 1), ("motogp", 1),
        ("syed modi", 1), ("thomas cup", 1), ("davis cup", 1),
        ("wimbledon", 1), ("us open", 1), ("australian open", 1),
        ("french open", 1), ("pro kabaddi", 1), ("hockey india", 1),
        ("ispl", 1), ("rowing", 1), ("golf", 1), ("hat-trick", 1),
        ("worldskills", 1), ("sport", 0), ("relay", 0), ("gold medal", 0),
        ("silver medal", 0), ("bronze medal", 0), ("player", 0),
        ("coach", 0), ("shooting", 0), ("century", 0), ("wicket", 0),
        ("semifinal", 0), ("quarterfinal", 0), ("runners-up", 0),
        ("captain", 0), ("team india", 0), ("bronze", 0), ("silver", 0),
        ("gold", 0), ("snooker", 1), ("billiards", 1), ("sepaktakraw", 1),
        ("la liga", 1), ("premier league", 1), ("uefa", 1),
        ("real madrid", 1), ("barcelona", 1), ("bwf", 1), ("wtt", 1),
        ("fide", 1), ("atp", 1), ("wta", 1), ("pkl", 1), ("sailing", 1),
        ("equestrian", 1), ("fencing", 1), ("judo", 1), ("taekwondo", 1),
        ("wushu", 1), ("kayaking", 1), ("canoeing", 1), ("gymnastics", 1),
    ],
    "International": [
        ("united nations", 1), ("un security council", 1), ("unsc", 1),
        ("unga", 1), ("un general assembly", 1), ("world health organization", 1),
        ("wto", 1), ("imf", 1), ("world bank", 1), ("brics", 1), ("g20", 1),
        ("g7", 1), ("shanghai cooperation", 1), ("asean", 1), ("saarc", 1),
        ("european union", 1), ("china", 1), ("united states", 1), ("usa", 1),
        ("russia", 1), ("ukraine", 1), ("japan", 1), ("australia", 1),
        ("pakistan", 1), ("bangladesh", 1), ("sri lanka", 1), ("nepal", 1),
        ("bhutan", 1), ("myanmar", 1), ("afghanistan", 1), ("iran", 1),
        ("israel", 1), ("gaza", 1), ("palestine", 1), ("saudi", 1),
        ("uae", 1), ("qatar", 1), ("turkey", 1), ("germany", 1),
        ("france", 1), ("britain", 1), ("united kingdom", 1), ("canada", 1),
        ("brazil", 1), ("south korea", 1), ("north korea", 1),
        ("vietnam", 1), ("philippines", 1), ("indonesia", 1),
        ("malaysia", 1), ("singapore", 1), ("thailand", 1), ("nigeria", 1),
        ("kenya", 1), ("egypt", 1), ("south africa", 1), ("mexico", 1),
        ("argentina", 1), ("italy", 1), ("spain", 1), ("new zealand", 1),
        ("switzerland", 1), ("sweden", 1), ("norway", 1), ("denmark", 1),
        ("netherlands", 1), ("poland", 1), ("bilateral", 1),
        ("foreign minister", 1), ("diplomatic", 1), ("treaty", 1),
        ("ambassador", 1), ("opec", 1), ("cop30", 1), ("cop29", 1),
        ("climate summit", 1), ("g77", 1), ("un peacekeeping", 1),
        ("state visit", 1), ("east asia summit", 1), ("commonwealth", 1),
        ("international", 0), ("summit", 0), ("delegation", 0),
        ("official visit", 0), ("abroad", 0), ("overseas", 0),
        ("diaspora", 0), ("africa", 0), ("europe", 0), ("asia", 0),
        ("middle east", 0), ("latin america", 0), ("cuba", 1), ("swiss", 1),
        ("abu dhabi", 1), ("dubai", 1), ("yemen", 1), ("syria", 1),
        ("lebanon", 1), ("iraq", 1), ("libya", 1), ("sudan", 1),
        ("ethiopia", 1), ("ghana", 1), ("tanzania", 1), ("uganda", 1),
        ("zimbabwe", 1), ("zambia", 1), ("botswana", 1), ("namibia", 1),
        ("mozambique", 1), ("madagascar", 1), ("mauritius", 1), ("maldives", 1),
        ("fiji", 1), ("papua new guinea", 1), ("kazakhstan", 1),
        ("uzbekistan", 1), ("tajikistan", 1), ("kyrgyzstan", 1),
        ("turkmenistan", 1), ("azerbaijan", 1), ("armenia", 1), ("georgia", 1),
        ("belarus", 1), ("romania", 1), ("bulgaria", 1), ("greece", 1),
        ("portugal", 1), ("ireland", 1), ("belgium", 1), ("austria", 1),
        ("czech", 1), ("hungary", 1), ("finland", 1), ("iceland", 1),
        ("luxembourg", 1), ("monaco", 1), ("vatican", 1), ("peru", 1),
        ("chile", 1), ("colombia", 1), ("venezuela", 1), ("ecuador", 1),
        ("bolivia", 1), ("paraguay", 1), ("uruguay", 1), ("panama", 1),
        ("costa rica", 1), ("guatemala", 1), ("honduras", 1),
        ("el salvador", 1), ("nicaragua", 1), ("dominican", 1), ("haiti", 1),
        ("jamaica", 1), ("trinidad", 1), ("bahamas", 1), ("barbados", 1),
        ("guyana", 1), ("suriname", 1), ("nato", 1), ("unesco", 1),
        ("unicef", 1), ("undp", 1), ("unep", 1), ("unhcr", 1), ("fao", 1),
        ("ilo", 1), ("iaea", 1), ("quad", 1), ("indo-pacific", 1),
        ("gulf cooperation council", 1), ("gcc", 1), ("un resolution", 1),
        ("non-aligned", 1), ("bimstec", 1), ("i2u2", 1),
    ],
}

# earlier category wins ties
PRIORITY = ["Prizes", "Space", "Defense", "Games", "Economic", "International", "Indian"]


def norm(s):
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9\s\-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def hits_in(text, kw):
    # whole-word/phrase match (cheap substring prefilter, then cached regex)
    if kw not in text:
        return False
    return _pat(kw).search(text) is not None


@lru_cache(maxsize=None)
def _pat(kw):
    return re.compile(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])")


def score_cat(title, body, kws):
    score = 0
    title_hits = []
    body_hits = 0
    strong_title = 0
    strong_body = 0
    for kw, strong in kws:
        t = hits_in(title, kw)
        b = hits_in(body, kw)
        if not (t or b):
            continue
        if t:
            score += 8 if strong else 5
            title_hits.append(kw)
            if strong:
                strong_title += 1
        if b and body_hits < 3:
            score += 2 if strong else 1
            body_hits += 1
            if strong:
                strong_body += 1
    return score, title_hits, strong_title, strong_body


def classify(rec):
    title = norm(rec["title"])
    body = norm(rec["content"][:3000])
    scores, thits = {}, {}
    for cat, kws in KW.items():
        s, th, st, sb = score_cat(title, body, kws)
        # Space / Games need a strong signal, not just generic words
        if cat in ("Space", "Games") and st == 0 and sb < 2:
            s = 0
        # Prizes must be evident from the headline (avoids "award" in body text)
        if cat == "Prizes" and st == 0:
            s = 0
        if cat == "Space" and re.search(r"\b(cop3\d|pre-cop|climate|emission|weather)\b", title):
            s = 0
        # International needs a specific entity, not just "summit"/"international"
        if cat == "International" and st == 0 and sb < 2:
            s = 0
        scores[cat], thits[cat] = s, th
    scores["Indian"] = 0
    best = max(scores.values())
    if best < 5:
        return "Indian", scores, thits
    for cat in PRIORITY:
        if scores.get(cat, 0) == best:
            # obituaries should not land in Prizes just because the person won awards
            if cat == "Prizes" and re.search(r"\b(dies|died|passes away|death|obituary|no more)\b", title):
                return "Indian", scores, thits
            return cat, scores, thits
    return "Indian", scores, thits


def summary(text, limit=430):
    text = re.sub(r"\s+", " ", (text or "").strip())
    text = re.sub(r"\*{3,}", "", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for p in parts:
        if len(out) + len(p) + 1 > limit:
            break
        out = (out + " " + p).strip()
        if len(out) > 240:
            break
    if not out:
        out = text[:limit].rsplit(" ", 1)[0] + "..."
    return out


def main():
    raw = json.load(open(SRC, encoding="utf-8"))
    rows, seen = [], set()
    skip = re.compile(r"^(daily current affairs quiz|current affairs quiz)\b|^press release page$", re.I)
    for r in raw:
        if skip.match(r["title"].strip()):
            continue
        key = norm(r["title"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(r)

    out = []
    for r in rows:
        cat, scores, thits = classify(r)
        meta = [m.strip() for m in r["meta"].split("|")]
        date = next((p for p in meta if re.match(r"^2026-\d{2}-\d{2}$", p)), "")
        out.append({
            "category": cat,
            "date": date,
            "title": r["title"],
            "ministry": meta[0] if meta else "",
            "source": meta[-2] if len(meta) >= 2 else "",
            "summary": summary(r["content"]),
            "link": r["link"],
            "scores": {k: v for k, v in scores.items() if v},
            "title_hits": {k: v for k, v in thits.items() if v},
        })
    out.sort(key=lambda x: (CATS.index(x["category"]), x["date"], x["title"]))
    json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    print("TOTAL (deduped):", len(out), "| removed duplicates:", len(raw) - len(out))
    c = Counter(r["category"] for r in out)
    for cat in CATS:
        print(f"  {cat:15s} {c[cat]:5d}")
    print()
    random.seed(11)
    for cat in CATS:
        pool = [r for r in out if r["category"] == cat]
        print("=" * 95)
        print(cat, len(pool))
        for r in random.sample(pool, min(10, len(pool))):
            print(f"  - {r['title'][:105]}")
            print(f"    hits={r['title_hits'].get(cat, [])[:6]}")


if __name__ == "__main__":
    main()
