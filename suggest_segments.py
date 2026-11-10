import json
import re
from collections import Counter

SRC = r"D:\Default Project\data\PIB\excel\oct_classified.json"
rows = json.load(open(SRC, encoding="utf-8"))

SEGMENTS = {
    "Polity & Governance": [
        "parliament", "lok sabha", "rajya sabha", "supreme court", "high court",
        "judiciary", "bill", "act", "amendment", "election", "eci",
        "election commission", "president", "prime minister", "governor",
        "chief minister", "cabinet", "commission", "tribunal", "panchayat",
        "constitution", "governance", "ministry",
    ],
    "Schemes & Missions": [
        "scheme", "yojana", "mission", "abhiyan", "programme", "program",
        "initiative", "launch", "launched", "portal", "app",
    ],
    "Economy, Banking & Budget": [
        "economy", "economic", "gdp", "inflation", "rbi", "reserve bank",
        "repo", "monetary policy", "bank", "loan", "credit", "insurance",
        "pension", "budget", "fiscal", "tax", "gst", "rupee", "sensex",
        "nifty", "sebi", "ipo", "fdi", "disinvestment", "msme", "startup",
    ],
    "Trade, Industry & Infrastructure": [
        "export", "import", "trade", "tariff", "manufacturing", "industry",
        "industrial", "investment", "road", "highway", "railway", "metro",
        "airport", "port", "shipping", "bridge", "tunnel", "infrastructure",
        "logistics", "power", "energy", "solar", "renewable",
    ],
    "Agriculture & Rural": [
        "agriculture", "farmer", "farmers", "crop", "msp", "kisan",
        "irrigation", "fertilizer", "food", "rural", "village", "livestock",
        "fisheries", "dairy",
    ],
    "International Relations": [
        "bilateral", "summit", "united nations", "unga", "unsc", "g20",
        "brics", "asean", "saarc", "sco", "wto", "imf", "world bank",
        "diplomatic", "treaty", "ambassador", "foreign minister",
        "state visit", "delegation", "indo-pacific", "nato", "eu",
    ],
    "Defence & Security": [
        "defence", "defense", "army", "navy", "air force", "drdo", "missile",
        "warship", "submarine", "military", "coast guard", "bsf", "crpf",
        "itbp", "cisf", "border", "security", "terror", "naxal", "cyber",
    ],
    "Space": [
        "isro", "space", "satellite", "gslv", "pslv", "lvm3", "navic",
        "gaganyaan", "chandrayaan", "aditya", "nasa", "spacex", "orbit",
        "mars", "jupiter", "planet", "astronomy", "telescope", "black hole",
    ],
    "Science, Tech & Health": [
        "technology", "artificial intelligence", "ai", "quantum",
        "semiconductor", "research", "scientist", "scientists", "innovation",
        "biotech", "vaccine", "health", "hospital", "disease", "ayushman",
        "digital", "data", "robot", "drone", "telecom", "5g",
    ],
    "Environment & Ecology": [
        "climate", "environment", "biodiversity", "wildlife", "forest",
        "pollution", "emission", "cop30", "cop31", "conservation", "tiger",
        "elephant", "wetland", "glacier", "river", "ganga", "air quality",
        "renewable", "green hydrogen", "carbon",
    ],
    "Geography & Disasters": [
        "flood", "cyclone", "earthquake", "landslide", "heatwave", "disaster",
        "rainfall", "monsoon", "drought", "eruption", "tsunami", "forest fire",
    ],
    "History, Art & Culture": [
        "festival", "temple", "heritage", "archaeology", "archaeological",
        "art", "culture", "cultural", "dance", "music", "literature",
        "saint", "dynasty", "inscription", "museum", "sculpture", "painting",
        "classical", "folk",
    ],
    "Awards, Honours & Authors": [
        "award", "awards", "prize", "nobel", "padma", "bharat ratna",
        "puraskar", "samman", "padak", "honour", "honor", "laureate",
        "author", "book", "novel", "writer", "poet",
    ],
    "Sports & Games": [
        "sports", "asian games", "olympic", "paralympic", "cricket",
        "football", "hockey", "badminton", "tennis", "kabaddi", "medal",
        "tournament", "championship", "world cup", "athlete", "wrestling",
        "boxing", "archery", "chess", "golf", "snooker",
    ],
    "Reports, Indices & Rankings": [
        "report", "index", "ranking", "rank", "survey", "census",
        "projection", "estimate", "data", "study", "findings",
    ],
    "Appointments & Who's Who": [
        "appointed", "appoints", "appointment", "takes oath", "assumes charge",
        "elected", "elected as", "new chief", "chairman", "chairperson",
        "director general", "secretary", "ceo", "md",
    ],
    "Obituaries": [
        "dies", "died", "passes away", "passed away", "death", "obituary",
        "no more", "cremated", "tribute",
    ],
    "Important Days & Anniversaries": [
        "day", "anniversary", "jayanti", "birth anniversary", "observed",
        "celebration", "celebrates", "commemorat",
    ],
    "Rajasthan": [
        "rajasthan", "jaipur", "jodhpur", "udaipur", "kota", "bikaner",
        "ajmer", "alwar", "bharatpur", "banswara", "chittorgarh", "pali",
        "sikar", "bhilwara", "mount abu", "jaisalmer", "barmer",
    ],
}


def pat(kw):
    return re.compile(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])")


def hit(text, kws):
    return sum(1 for k in kws if pat(k).search(text))


title_counts = Counter()
both_counts = Counter()
examples = {}

for r in rows:
    t = " " + re.sub(r"\s+", " ", r["title"].lower()) + " "
    b = " " + re.sub(r"\s+", " ", (r["title"] + " " + r["summary"]).lower()) + " "
    for seg, kws in SEGMENTS.items():
        nt = hit(t, kws)
        nb = hit(b, kws)
        if nt:
            title_counts[seg] += 1
            examples.setdefault(seg, r["title"])
        if nt or nb >= 2:
            both_counts[seg] += 1

print(f"{'Segment':38s} {'In title':>9s} {'Title+body':>11s}")
for seg in SEGMENTS:
    print(f"{seg:38s} {title_counts[seg]:9d} {both_counts[seg]:11d}")

print("\nExamples:")
for seg in SEGMENTS:
    if seg in examples:
        print(f"  {seg:36s} {examples[seg][:90]}")
