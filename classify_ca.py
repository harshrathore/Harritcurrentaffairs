#!/usr/bin/env python3
"""classify_ca.py - Segregate current affairs (Jun 1 - Sep 30, 2026) into
RPSC RAS Prelims syllabus topics. Spec v1.0 (hybrid org rule).

Usage:
  python classify_ca.py --stats          # classify + distribution + samples
  python classify_ca.py --build          # classify + generate 9 PPTX files
  python classify_ca.py --build --send   # also send to Telegram
"""
import argparse
import collections
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("HARRIT_DATA_DIR") or os.path.join(BASE, "..", "data", "PIB")
SLIDES_DIR = os.path.join(DATA_DIR, "slides", "topicwise")

START_DATE = "2026-06-01"
END_DATE = "2026-09-30"

TOKEN = "7792990046:AAGfOItkWgJfTZRFHYNsNcwuqHuyjv3UkGk"
CHAT_ID = "8250786682"

# ---------------------------------------------------------------- topics
TOPICS = [
    ("t1", "01_Rajasthan_Culture_Heritage.pptx", "Rajasthan - Art, Culture & Heritage"),
    ("t2", "02_Rajasthan_Polity_Administration.pptx", "Rajasthan - Polity & Administration"),
    ("t3", "03_Rajasthan_Economy_Schemes.pptx", "Rajasthan - Economy & Schemes"),
    ("t4", "04_Indian_Polity_Governance.pptx", "Indian Polity & Governance"),
    ("t5", "05_Indian_Economy.pptx", "Indian Economy"),
    ("t6", "06_Geography_Environment.pptx", "Geography & Environment"),
    ("t7", "07_Science_Technology.pptx", "Science & Technology"),
    ("t8", "08_Indian_History_Culture.pptx", "Indian History & Culture"),
    ("extra", "09_Extra_Content.pptx", "Extra Content (Out of Syllabus)"),
]
TOPIC_IDS = [t[0] for t in TOPICS]
TOPIC_NAME = {t[0]: t[2] for t in TOPICS}
TOPIC_FILE = {t[0]: t[1] for t in TOPICS}

PRIORITY = ["t7", "t5", "t4", "t6", "t8"]        # non-Rajasthan tie order
RJ_PRIORITY = ["t2", "t3", "t1"]                  # Rajasthan tie order

# ---------------------------------------------------------------- keywords
RJ_SCOPE = [
    "rajasthan", "rajasthani", "jaipur", "jodhpur", "udaipur", "jaisalmer", "bikaner",
    "ajmer", "kota", "bharatpur", "alwar", "sikar", "chittorgarh", "mewar", "marwar",
    "shekhawati", "ranthambore", "keoladeo", "sariska", "mount abu", "pushkar", "pali",
    "nagaur", "jalore", "barmer", "dungarpur", "banswara", "pratapgarh", "rajsamand",
    "bhilwara", "churu", "jhunjhunu", "dausa", "tonk", "sawai madhopur", "karauli",
    "dholpur", "bundi", "kumbhalgarh", "ranakpur", "mehrangarh", "hawa mahal",
    "city palace", "jantar mantar", "amber fort", "osian", "haldi ghati",
    "gurushikhar", "indira gandhi canal", "riico", "rpsc", "sso rajasthan",
    "emitra", "jan aadhaar", "maharana", "maharaj", "maharaja", "rajput",
    "rajputana",
]

KW = {}

KW["t1"] = [
    "fort", "forts", "palace", "haveli", "monument", "heritage", "archaeological",
    "excavation", "ruins", "temple", "stepwell", "baori", "mosque", "dargah",
    "gurudwara", "church", "chhatri", "cenotaph", "inscription", "museum", "gallery",
    "jain", "sacred", "shrine", "unesco", "world heritage", "gi tag",
    "geographical indication", "craft", "craftsmanship", "artisan", "handicraft",
    "handloom", "weaving", "block print", "bandhani", "tie and dye", "lac",
    "silver work", "wood carving", "blue pottery", "painting", "miniature", "phad",
    "pichwai", "mural", "sculpture", "fresco", "architecture", "architectural",
    "folk dance", "ghoomar", "kalbelia", "chang", "panihari", "folk music", "langa",
    "manganiyar", "bhopa", "kathak", "nautanki", "ramleela", "drama", "natak",
    "rangmanch", "theatre", "sangeet", "nritya", "singer", "composer", "lyricist",
    "sitar", "tabla", "flute", "instrumental", "classical", "folk song", "sufi",
    "saint", "bhakti", "fair", "festival", "mela", "kumbh", "teej", "gangaur",
    "pushkar fair", "camel festival", "marwar festival", "urs", "procession",
    "utsav", "mahotsav", "literature", "dialect", "rajasthani language", "bhasha",
    "sahitya", "kavya", "kavi", "poet", "book release", "pustak", "jayanti",
    "birth anniversary", "remembering", "life and times", "biography", "renowned",
    "legendary", "veteran", "eminent", "maestro", "ustad", "pandit", "guru",
    "acharya", "shayar", "folk deity", "handloom day", "rich handloom",
    "maharana", "maharaj", "rajput", "rajputana", "royal", "dynasty", "ruler",
    "kingdom", "prince", "princess", "maharaja",
]

KW["t2"] = [
    "rajasthan government", "rajasthan assembly", "vidhan sabha", "vidhan parishad",
    "rajasthan high court", "jodhpur bench", "jaipur bench", "governor rajasthan",
    "chief minister rajasthan", "rajasthan cabinet", "speaker", "opposition leader",
    "assembly session", "mla", "mlc", "chief secretary", "secretariat",
    "divisional commissioner", "district collector", "district magistrate",
    "superintendent of police", "tehsildar", "sub-divisional officer",
    "sub divisional magistrate", "block development officer", "bdo",
    "additional district", "revenue department", "survey department", "board of revenue",
    "rajasthan service rules", "district panchayat", "zila parishad", "panchayat samiti",
    "village panchayat", "gram sabha", "nagar palika", "nagar nigam", "ulb",
    "municipal", "panchayati raj", "rajasthan public service commission",
    "state election commission", "state information commission",
    "rajasthan human rights", "state women commission", "lokayukt", "lokayukta",
    "anti-corruption bureau", "acb", "rajasthan police", "fir", "ats",
    "reservation", "obc", "sc/st", "house adjourned", "state commission",
    "minister of rajasthan", "rajasthan chief", "department rajasthan",
]

KW["t3"] = [
    "mukhyamantri", "jan aadhaar", "chiranjeevi", "bhamashah", "palanhar",
    "kali ghodi", "indira rasoi", "ojhla", "nishulk", "shramik", "udyam",
    "solar", "kisan", "krishi", "jaal", "sadak", "shiksha", "berojgari",
    "protsahan", "shala", "rajasthan sampark", "cm helpline", "rajasthan budget",
    "gsdp", "state economic survey", "rajasthan economic", "rajasthan agriculture",
    "rajasthan industry", "rajasthan tourism", "rajasthan health",
    "rajasthan education", "rajasthan energy", "rajasthan rural", "rajasthan irrigation",
    "rajasthan water", "rajasthan animal husbandry", "rajasthan dairy",
    "rajasthan forest", "rajasthan mining", "fiscal deficit", "revenue surplus",
    "centrally sponsored", "pm kisan", "pmay", "sbm", "jjm", "pmjdy", "mudra",
    "pmegp", "nrlm", "ajivika", "riico", "madar", "bhiwadi", "kotputli",
    "neemrana", "alwar industrial", "barmer refinery", "chittorgarh plant",
    "captive power", "greenfield airport", "bikaner airport", "udaipur airport",
    "jodhpur airport", "eastern canal", "western canal", "command area",
    "watershed", "fodder", "ekta nagar", "hanumangarh", "minor irrigation",
    "jas kisan", "krishi udyan", "ayushman", "welfare scheme", "yojana",
]

KW["t4"] = [
    "parliament question", "parliament passes", "parliament", "lok sabha", "rajya sabha",
    "bill", "private member bill", "ordinance", "resolution", "adjournment",
    "no-confidence", "motion", "question hour", "standing committee",
    "public accounts", "estimates committee", "select committee", "cabinet approves",
    "cabinet meeting", "cabinet", "president assent", "joint session", "amendment",
    "act 2026", "act 2025", "constitution", "constitutional", "preamble",
    "constituent assembly", "drafting committee", "ambedkar", "anti-defection",
    "whip", "floor test", "presidential rule", "president rule", "delimitation",
    "nominated", "supreme court", "high court", "judgment", "verdict", "suo motu",
    "judicial", "court directs", "review petition", "acquittal", "bail",
    "charge sheet", "contempt", "writ", "habeas corpus", "mandamus",
    "public interest litigation", "litigation", "judicial review", "collegium",
    "chief justice", "law ministry", "ndps", "uapa", "pocso", "atrocities act",
    "dowry", "domestic violence", "fcra", "money laundering", "election commission",
    "upsc", "ssc", "niti aayog", "niti ayog", "planning commission", "finance commission",
    "law commission", "lokpal", "vigilance", "information commission", "nhrc",
    "human rights", "national commission for women", "ncw", "ncpcr", "ncsc", "ncst",
    "ncbc", "minorities commission", "pay commission", "seventh pay", "eighth pay",
    "commission of inquiry", "comptroller and auditor", "cag", "administrative tribunal",
    "directorate", "cabinet secretariat",
    "prime minister office", "pmo", "registrar general", "ncrb",
    "bureau of indian standards", "census", "rti", "citizen charter", "social audit",
    "grievance redressal", "fundamental right", "fundamental duties",
    "directive principles", "citizenship", "emergency provisions", "union-state",
    "governor", "public policy", "mission karmayogi",
    "panchayati raj", "panchayat", "gram sabha", "ward", "nagar palika", "nagar nigam",
    "urban local body", "municipality", "municipal corporation", "municipal council",
    "national security council", "anti-terror", "terror financing",
    "national investigation agency", "nia", "central bureau of investigation", "cbi",
    "enforcement directorate", "narcotics control", "intelligence bureau",
    "financial intelligence", "bureau of police research", "home guard", "civil defence",
    "ndrf", "disaster response", "crisis management", "director general",
    "inspector general", "indian administrative service", "ias ", "ips ",
    "indian forest service", "chief of army staff", "chief of naval staff",
    "chief of air staff", "chief of defence staff", "theatre command",
    "armed forces", "indian army", "indian navy", "indian air force",
    "border security force", "bsf", "crpf", "cisf", "ssb ", "assam rifles", "itbp",
    "nsg", "territorial army", "ncc", "sainik school", "agniveer", "veteran",
    "ex-servicemen", "defence acquisition", "defence procurement", "defence budget",
    "tri-service", "raksha mantri", "home minister", "union home ministry",
    "ministry of cooperation", "labour code", "esic", "epfo", "provident fund",
    "appointment", "appointed", "chairman", "managing director", "governance",
    "guideline", "regulation", "funding", "merger", "union minister",
    "sabha",
    "article ", "supreme court of india", "high courts", "act, 2026", "act, 2025",
    "rules", "scheme launched", "launches scheme", "national mission", "mission ",
    "brics", "g20", "g7 ", "quad", "saarc", "asean", "summit", "narcotics",
    "international", "bilateral",
]

KW["t5"] = [
    "rbi", "repo rate", "reverse repo", "bank rate", "monetary policy",
    "inflation", "cpi", "wpi", "iip", "banking", "upi", "digital payment", "sebi",
    "irda", "pfrda", "nbfc", "payment bank", "npa", "insolvency", "nclt",
    "lic ", "insurance", "pension", "nps", "atal pension", "ppf", "sukanya",
    "mutual fund", "ipo", "share market", "sensex", "nifty", "bond", "treasury",
    "disinvestment", "privatization", "fiscal", "gst", "tax", "income tax", "tds",
    "customs", "gdp", "economic survey", "union budget", "budget 2026", "budget",
    "growth rate", "resource mobilization", "human development index",
    "ease of doing business", "world bank", "imf", "wef", "forex reserves",
    "foreign exchange", "exchange rate", "trade deficit", "balance of payment",
    "trade agreement", "import duty", "export", "import", "agriculture", "farm",
    "farmer", "msp", "minimum support price", "fpo", "fertilizer", "urea",
    "organic", "millets", "shree anna", "food security", "nfsa", "pds", "ration card",
    "mid day meal", "poshan", "angangwadi", "angawadi", "icds", "horticulture",
    "sericulture", "fisheries", "poultry", "dairy", "kharif", "rabi", "crop",
    "sowing", "area coverage", "irrigation", "canal", "livestock",
    "animal husbandry", "sugar", "cotton", "wheat", "rice", "pulse", "oilseed",
    "industry", "industrial", "commerce", "trade", "fdi", "wto", "manufacturing",
    "make in india", "pli", "competition commission", "liberalization",
    "economic reform", "service sector", "skill development", "employment",
    "unemployment", "labour", "wage", "msme", "startup", "gati shakti",
    "infrastructure", "logistics", "sagarmala", "bharatmala", "metro",
    "vande bharat", "bullet train", "airport", "port", "waterway", "broadband",
    "digital india", "smart city", "amrut", "swachh bharat", "namami gange",
    "jan dhan", "power", "energy", "electricity", "coal", "petroleum", "refinery",
    "renewable energy", "solar energy", "wind energy", "transmission",
    "highway", "expressway", "corridor", "economic growth", "survey",
    "psu", "public sector", "corporate", "turnover", "profit", "ntpc", "powergrid",
    "sail", "coal india", "ongc", "oil india", "gail", "iocl", "bpcl", "hpcl",
    "air india", "nhai", "aai", "exim bank", "sidbi", "nabard", "fci",
    "gdp growth", "quarterly", "company", "manufactured", "production",
    "railway", "railways", "train", "express service", "abhiyan", "udan",
    "scholarship", "sanctioned", "approved", "scheme", "yojana", "programme",
    "crore", "lakh", "invest", "investment", "financial", "economic",
    "rural development",
    "cooperative", "food corporation", "of india approves", "industries",
]

KW["t6"] = [
    "river", "glacier", "lake", "dam", "reservoir", "flood", "drought", "landslide",
    "earthquake", "tsunami", "cyclone", "monsoon", "rainfall", "climate",
    "himalaya", "bay of bengal", "arabian sea", "glacial lake outburst", "glof",
    "cloudburst", "subsidence", "avalanche", "heat wave", "cold wave",
    "thunderstorm", "lightning", "hailstorm", "western disturbance", "el nino",
    "la nina", "retreating monsoon", "northeast monsoon", "southwest monsoon",
    "weather warning", "imd", "storm surge", "coastal erosion", "sea level",
    "plateau", "delta", "estuary", "peninsula", "coast", "island", "strait",
    "ganga", "yamuna", "brahmaputra", "godavari", "krishna", "narmada", "tapti",
    "sutlej", "chenab", "ravi", "jhelum", "indus", "kosi", "damodar", "mahanadi",
    "cauvery", "periyar", "subarnarekha", "ghaggar", "luni", "chambal", "betwa",
    "gandak", "climate change", "global warming", "carbon", "emission",
    "greenhouse", "ghg", "methane", "net zero", "cop", "unfccc", "paris agreement",
    "ipcc", "climate finance", "carbon sink", "ozone", "desertification",
    "deforestation", "biodiversity", "wetland", "ramsar", "biosphere",
    "national park", "wildlife sanctuary", "sanctuary", "tiger reserve",
    "elephant reserve", "forest", "conservation", "endangered", "vulnerable",
    "extinct", "invasive species", "iucn", "red list", "cites", "green tribunal",
    "ngt", "environment impact", "eia", "pollution", "air quality", "aqi",
    "stubble burning", "pm2.5", "pm10", "plastic ban", "single use plastic",
    "e waste", "smog", "environment", "ecological", "ecosystem", "pollination",
    "mangrove", "sundarbans", "reef", "coral", "species", "wildlife", "tiger",
    "leopard", "elephant", "dolphin", "crocodile", "gharial", "turtle", "migratory",
    "hornbill", "bustard", "vulture", "peacock", "flamingo", "blackbuck", "wild ass",
    "zoo", "safari", "nesting", "mining", "mineral", "coal", "iron ore",
    "rare earth", "critical mineral", "lithium", "groundwater", "soil",
    "water resource", "volcano", "seismic", "arctic", "antarctic", "amazon",
    "sahara", "mediterranean", "red sea", "persian gulf", "suez", "greenhouse gas",
    "warming", "bird", "birds", "flora", "fauna", "biodiversity park", "reserve",
]

KW["t7"] = [
    "isro", "nasa", "space", "satellite", "rocket", "launch vehicle", "pslv",
    "gslv", "sslv", "lvm3", "cartosat", "resourcesat", "navic", "gsat", "insat",
    "antrix", "sriharikota", "thumba", "launch pad", "chandrayaan", "gaganyaan",
    "aditya", "mars", "orbit", "soft landing", "vikram", "pragyan", "crew module",
    "space station", "telescope", "observatory", "exoplanet", "asteroid", "comet",
    "solar eclipse", "lunar eclipse", "planet", "defence", "drdo", "missile",
    "brahmos", "agni", "prithvi", "pralay", "shaurya", "akash", "tejas", "hal",
    "sukhoi", "rafale", "amca", "scorpene", "kalvari", "arihant", "warship",
    "frigate", "destroyer", "aircraft carrier", "vikrant", "submarine",
    "fighter jet", "apache", "chinook", "howitzer", "t-90", "arjun tank",
    "radar", "sonar", "drone", "uav", "unmanned", "torpedo", "army", "navy",
    "air force", "iaf", "airbase", "squadron", "combat", "border infrastructure",
    "artificial intelligence", "ai ", "machine learning", "cyber", "data centre",
    "quantum", "semiconductor", "chip", "graphene", "supercomputer", "blockchain",
    "5g", "6g", "telecom", "trai", "tower", "mobile network", "internet",
    "software", "robot", "robotics", "3d printing", "nanotechnology", "nano ",
    "health", "disease", "vaccine", "who ", "cancer", "diabetes", "hospital",
    "ayushman", "nutrition", "biotech", "genetic", "medicine", "drug",
    "clinical trial", "icmr", "aiims", "tuberculosis", "malaria", "dengue",
    "zika", "nipah", "avian flu", "antimicrobial", "antibiotic", "genomic",
    "sequencing", "mrna", "organ transplant", "stem cell", "cloning", "crispr",
    "dna", "microplastic", "anaemia", "obesity", "mental health", "telemedicine",
    "pandemic", "virus", "outbreak", "fssai", "food safety", "nuclear", "reactor",
    "npcil", "kudankulam", "fusion", "hydrogen", "battery", "electric vehicle",
    "solar panel", "wind turbine", "csir", "iit", "iisc", "laboratory", "research",
    "study", "scientist", "experiment", "patent", "journal", "nobel",
    "science", "technology", "innovation", "digital", "app ", "portal",
    "computer", "information technology", "biotechnology", "engineering",
    "developed", "develops", "invented", "breakthrough", "prototype",
    "naval", "ins ", "war game", "exercise",
]

KW["t8"] = [
    "independence day", "republic day", "gandhi", "nehru", "subhash", "azadi",
    "freedom fighter", "freedom struggle", "quit india", "dandi", "sabarmati",
    "champaran", "bhagat singh", "chandrashekhar azad", "sukhdev", "rajguru",
    "bismil", "lala lajpat", "tilak", "bipin chandra", "rajendra prasad",
    "sardar patel", "amrit mahotsav", "1857", "revolt", "british", "colonial",
    "national movement", "partition", "panchsheel", "non-alignment", "world war",
    "harappan", "mohenjo", "lothal", "kalibangan", "dholavira", "sanchi",
    "ajanta", "ellora", "konark", "hampi", "taxila", "nalanda", "pataliputra",
    "maurya", "ashoka", "gupta", "kushana", "satavahana", "chalukya", "pallava",
    "chola", "pandya", "maratha", "shivaji", "tipu sultan", "mughal", "akbar",
    "aurangzeb", "vijayanagar", "ancient", "medieval", "sultanate", "khilji",
    "tughlaq", "babur", "humayun", "jahangir", "shah jahan", "nawab",
    "bhakti movement", "sufi", "chishti", "kabir", "mirabai", "tulsidas",
    "vivekananda", "ram mohan roy", "jyotiba phule", "savitribai", "gokhale",
    "guru nanak", "sikh", "unesco", "world heritage", "sanskrit",
    "classical language", "mother tongue", "book fair", "literature",
    "book release", "padma", "bharat ratna", "national award", "filmfare",
    "dadasaheb", "jnanpith", "sahitya akademi", "booker", "pulitzer", "arjuna award",
    "dronacharya", "shourya", "kirti chakra", "ashoka chakra", "param vir",
    "gallantry award", "kavi", "sahitya", "poet", "writer", "author",
    "international day", "world day", "national day", "observance", "theme",
    "gandhi jayanti", "constitution day", "national voters day", "science day",
    "literacy day", "mother language day", "yoga day", "world heritage day",
    "museum", "archaeological", "ancient", "history", "anniversary", "birth anniversary",
    "jayanti", "tribute", "homage to", "releases book", "autobiography", "memoir",
]

# ---------------------------------------------------------------- noise -> extra
NOISE = [
    "condole", "condolence", "expresses grief", "grief over", "pays tribute",
    "pays homage", "mourns", "demise", "passing away", "passed away",
    "ex-gratia", "pmnrf", "shares highlights", "shares glimpses", "shares thoughts",
    "shares article", "shares sanskrit", "subhashitam", "english rendering",
    "congratulates", "extends greetings", "greets", "birthday greetings",
    "best wishes", "happy wishes", "felicitation", "meets the prime minister",
    "meets prime minister", "courtesy call", "extended an invitation", "farewell",
    "pays respect", "tomb of the unknown soldier", "wreath", "quiz",
    "practice questions", "test series", "mcq", "daily current affairs",
    "shares her", "shares his", "shares a ", "shares message", "shares video",
    "shares post", "shares greetings", "shares views", "graces", "confers",
    "pays obeisance", "condoling", "grieves", "to visit", "to grace",
    "foundation day", "valedictory session", "greetings on", "greetings to",
    "on the eve", "no change of guard", "change of guard ceremony",
    "pays tributes", "birth anniversary of", "calls on", "press release page",
    "press communique", "visits to",
]

SPORTS = [
    "asian games", "commonwealth games", "olympic", "medal", "cricket", "icc ",
    "hockey", "football", "badminton", "chess", "kabaddi", "ipl ", "wta ", "atp ",
    "fifa", "tournament", "world cup", "championship", "athletics", "tennis",
    "golf", "wrestl", "boxing", "boxer", "swimmer", "sportsperson", "sports person",
    "arjuna award", "dronacharya award", "ranji", "football", "league", "match",
    "goal", "penalty", "umpire", "referee", "batting", "bowling", "ties 1-1",
    "wins gold", "wins silver", "wins bronze", "gold medal", "silver medal",
    "bronze medal", "record in", "ranked first", "world no.", "no. 1 rank",
    "fide", "chess", "grandmaster", "wimbledon", "us open", "french open",
    "australian open", "premier league", "la liga", "nba",
]

# GKToday category boost -> topic
CAT_BOOST = {
    "science": ("t7", 4),
    "economy": ("t5", 4),
    "international": ("t4", 3),
    "defence": ("t7", 3),
    "government schemes": ("t5", 3),
    "environment": ("t6", 4),
    "awards": ("t8", 3),
    "legal": ("t4", 5),
    "constitution": ("t4", 5),
    "art & culture": ("t8", 4),
    "reports": ("t5", 3),
    "summits": ("t4", 3),
    "infrastructure": ("t5", 3),
    "important days": ("t8", 4),
    "places": ("t6", 3),
}

# ---------------------------------------------------------------- compile
def compile_kws(kws):
    """Single alternation regex: matches if ANY keyword present (fast)."""
    parts = []
    for kw in kws:
        kw = kw.strip().lower()
        if kw:
            parts.append(re.escape(kw))
    if not parts:
        parts = [r"(?!)"]
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")(?!\w)")


def compile_count(kws):
    """Alternation regex returning distinct keyword hits count (fast)."""
    parts = []
    for kw in kws:
        kw = kw.strip().lower()
        if kw:
            parts.append(re.escape(kw))
    if not parts:
        parts = [r"(?!)"]
    return re.compile(r"(?<!\w)(" + "|".join(parts) + r")(?!\w)")


PATS_M = {k: compile_kws(v) for k, v in KW.items()}      # match-only
PATS_C = {k: compile_count(v) for k, v in KW.items()}    # count hits
PAT_SCOPE = compile_kws(RJ_SCOPE)
PAT_NOISE = compile_kws(NOISE)
PAT_SPORTS = compile_kws(SPORTS)
PAT_SUMMIT = compile_kws([
    "summit", "g7", "g20", "g-7", "g-20", "brics", "quad", "saarc", "sco",
    "shanghai cooperation", "asean", "un general assembly", "side-lines",
    "sidelines", "bilateral", "state visit", "official visit",
])

SCI_ORG = compile_kws([
    "isro", "drdo", "icmr", "csir", "hal ", "iit", "iisc", "aiims", "nasa",
    "npcil", "barc", "antrix", "dbt", "dst ",
])
GOV_WORD = compile_kws([
    "appointment", "appointed", "chairman", "cmd", "policy", "funding", "budget",
    "merger", "cabinet", "committee", "guideline", "regulation", "governance",
    "named as", "set up", "establish", "act ", "bill", "parliament", "minister",
    "secretariat", "department", "director",
])
PSU_ORG = compile_kws([
    "ntpc", "powergrid", "sail", "coal india", "ongc", "oil india", "gail",
    "iocl", "bpcl", "hpcl", "air india", "nhai", "aai", "exim bank", "sidbi",
    "nabard", "fci", "ircon", "railtel", "dfccil",
])
APPT_WORD = compile_kws([
    "appointment", "appointed", "chairman", "cmd", "managing director", "ceo",
    "director", "governance", "board of directors",
])


def score_topic(tid, title, content):
    """title hit count * 6 + content distinct hits (capped 3)."""
    n = len(PATS_C[tid].findall(title))
    s = n * 6
    if content:
        s += min(len(set(PATS_C[tid].findall(content))), 3)
    return s


# ---------------------------------------------------------------- load
def load_articles():
    with open(os.path.join(DATA_DIR, "pib_database.json"), encoding="utf-8") as f:
        pib = json.load(f)
    with open(os.path.join(DATA_DIR, "current_affairs_database.json"), encoding="utf-8") as f:
        ca = json.load(f)

    arts = []
    for v in pib.values():
        d = (v.get("date") or "")[:10]
        if START_DATE <= d <= END_DATE:
            arts.append({
                "title": (v.get("title") or "").strip(),
                "content": (v.get("content") or "").strip(),
                "date": d,
                "category": v.get("ministry", "PIB"),
                "source": "PIB",
                "url": v.get("article_url", "") or v.get("url", ""),
            })
    for v in ca.values():
        d = (v.get("date") or "")[:10]
        if START_DATE <= d <= END_DATE:
            arts.append({
                "title": (v.get("title") or "").strip(),
                "content": (v.get("content") or "").strip(),
                "date": d,
                "category": v.get("category", ""),
                "source": "GKToday",
                "url": v.get("url", ""),
            })
    return arts


# ---------------------------------------------------------------- classify
def classify(a):
    title = a["title"].lower()
    content = a["content"][:4000].lower()
    cat = (a.get("category") or "").lower()

    # 1. rotation noise / sports -> extra (summit meetings are exam-relevant,
    #    so they bypass the "meets prime minister" noise rule)
    if PAT_SPORTS.search(title) or "sports" in cat:
        return "extra"
    if PAT_NOISE.search(title) and not PAT_SUMMIT.search(title):
        return "extra"

    # category boosts
    boosts = {}
    for key, (tid, val) in CAT_BOOST.items():
        if key in cat:
            boosts[tid] = boosts.get(tid, 0) + val

    # base scores
    scores = {}
    for tid in ("t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"):
        scores[tid] = score_topic(tid, title, content)
    for tid, val in boosts.items():
        if tid in scores:
            scores[tid] += val

    # 2. Rajasthan scope: title scope OR title-level RJ subject hit.
    #    (content-only Rajasthan mention does NOT divert national articles)
    if PAT_SCOPE.search(title):
        # pick highest RJ score; tie -> t2 > t3 > t1
        best = max(RJ_PRIORITY, key=lambda k: (scores[k], -RJ_PRIORITY.index(k)))
        if scores[best] > 0:
            return best
        # RJ article without RJ-subject keywords -> national fallback
        nat = {k: scores[k] for k in PRIORITY}
        if max(nat.values()) > 0:
            for tid in PRIORITY:
                if nat[tid] == max(nat.values()):
                    return tid
        return "extra"

    # 2b. title-evidence rule: no title keyword -> classify from content only,
    #     but require >= 2 distinct content hits, else Extra
    if max(score_topic(k, title, "") for k in KW) == 0:
        best_c, win_c = 0, None
        for tid in PRIORITY:
            c = len(set(PATS_C[tid].findall(content)))
            if c > best_c:
                best_c, win_c = c, tid
        if win_c and best_c >= 2:
            return win_c
        return "extra"

    # 3. hybrid org rule
    if SCI_ORG.search(title):
        if GOV_WORD.search(title):
            scores["t4"] += 12
            scores["t7"] = max(0, scores["t7"] - 8)
    if PSU_ORG.search(title) and APPT_WORD.search(title):
        scores["t4"] += 12
        scores["t5"] = max(0, scores["t5"] - 8)

    # 4. pick winner
    best = 0
    winner = None
    for tid in PRIORITY:
        if scores[tid] > best:
            best = scores[tid]
            winner = tid
    if winner and best > 0:
        return winner
    return "extra"


# ---------------------------------------------------------------- slides
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xA5, 0xD6, 0xA7)
TOPIC_BG = {
    "t1": RGBColor(0x4E, 0x34, 0x2E), "t2": RGBColor(0x1A, 0x23, 0x7E),
    "t3": RGBColor(0x00, 0x4D, 0x40), "t4": RGBColor(0x26, 0x32, 0x38),
    "t5": RGBColor(0x1B, 0x5E, 0x20), "t6": RGBColor(0x00, 0x69, 0x5C),
    "t7": RGBColor(0x0D, 0x47, 0xA1), "t8": RGBColor(0x4A, 0x14, 0x8C),
    "extra": RGBColor(0x37, 0x47, 0x4F),
}
TOPIC_ACCENT = {
    "t1": RGBColor(0xBC, 0x8F, 0x5F), "t2": RGBColor(0x5C, 0x6B, 0xC0),
    "t3": RGBColor(0x26, 0xA6, 0x9A), "t4": RGBColor(0x78, 0x90, 0x9C),
    "t5": RGBColor(0x66, 0xBB, 0x6A), "t6": RGBColor(0x4D, 0xB6, 0xAC),
    "t7": RGBColor(0x42, 0xA5, 0xF5), "t8": RGBColor(0xAB, 0x47, 0xBC),
    "extra": RGBColor(0x90, 0xA4, 0xAE),
}


def add_textbox(slide, left, top, width, height, text, font_size=18,
                bold=False, color=WHITE, alignment=PP_ALIGN.LEFT):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = "Calibri"
    p.alignment = alignment
    return tf


def build_pptx(tid, articles):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # title slide
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = TOPIC_BG[tid]
    add_textbox(s, 1, 1.4, 11.3, 1, "RPSC RAS PRELIMS - CURRENT AFFAIRS",
                font_size=40, bold=True, alignment=PP_ALIGN.CENTER)
    add_textbox(s, 1, 2.9, 11.3, 1, TOPIC_NAME[tid],
                font_size=32, bold=True, color=TOPIC_ACCENT[tid],
                alignment=PP_ALIGN.CENTER)
    add_textbox(s, 1, 4.2, 11.3, 0.8,
                f"Total Articles: {len(articles)} | {START_DATE} to {END_DATE}",
                font_size=20, color=LIGHT, alignment=PP_ALIGN.CENTER)
    add_textbox(s, 1, 6.0, 11.3, 0.6, "Harrit Current Affairs | PIB + GKToday",
                font_size=16, color=LIGHT, alignment=PP_ALIGN.CENTER)

    for art in articles:
        s = prs.slides.add_slide(prs.slide_layouts[6])
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = TOPIC_BG[tid]
        bar = s.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
        bar.fill.solid()
        bar.fill.fore_color.rgb = TOPIC_ACCENT[tid]
        bar.line.fill.background()
        add_textbox(s, 0.5, 0.3, 12.3, 1, art["title"], font_size=28, bold=True)
        tags = [t for t in (art.get("category", ""), art.get("source", ""), art["date"]) if t]
        add_textbox(s, 0.5, 1.2, 12.3, 0.4, " | ".join(tags), font_size=14, color=LIGHT)
        body = (art.get("content") or "").replace("\n", " ")
        if not body:
            body = "(No summary available - click Read more for full release)"
        add_textbox(s, 0.5, 1.7, 12.3, 5.3, body, font_size=18)
        if art.get("url"):
            txBox = s.shapes.add_textbox(Inches(8.8), Inches(7.05), Inches(4.2), Inches(0.35))
            tf = txBox.text_frame
            tf.word_wrap = False
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.RIGHT
            run = p.add_run()
            run.text = "Read more >"
            run.font.size = Pt(11)
            run.font.color.rgb = LIGHT
            run.hyperlink.address = art["url"]

    os.makedirs(SLIDES_DIR, exist_ok=True)
    path = os.path.join(SLIDES_DIR, TOPIC_FILE[tid])
    prs.save(path)
    return path


def send_file(path, caption):
    import requests
    with open(path, "rb") as f:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendDocument",
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"document": (os.path.basename(path), f,
                   "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
            timeout=300,
        )
    return r.json().get("ok", False)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--sample", type=int, default=8, help="sample titles per topic")
    ap.add_argument("--explain", type=str, default="", help="explain scores for a title")
    args = ap.parse_args()

    if args.explain:
        a = {"title": args.explain, "content": "", "category": "", "date": "", "source": ""}
        scores = {k: score_topic(k, args.explain.lower(), "") for k in KW}
        print(f"title: {args.explain}")
        print("scores:", dict(sorted(scores.items(), key=lambda x: -x[1])))
        print("noise:", bool(PAT_NOISE.search(args.explain.lower())),
              "sports:", bool(PAT_SPORTS.search(args.explain.lower())),
              "scope:", bool(PAT_SCOPE.search(args.explain.lower())))
        print("=> ", classify(a))
        return

    arts = load_articles()
    # dedup: same title+date appearing in both DBs / duplicate entries
    seen = set()
    uniq = []
    for a in arts:
        key = (re.sub(r"\s+", " ", a["title"]).lower(), a["date"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    if len(uniq) != len(arts):
        print(f"Deduped {len(arts) - len(uniq)} duplicate titles")
    arts = uniq
    print(f"Loaded {len(arts)} articles ({START_DATE} to {END_DATE})")

    groups = {t: [] for t in TOPIC_IDS}
    for a in arts:
        groups[classify(a)].append(a)

    print("\n=== DISTRIBUTION ===")
    total = 0
    for tid in TOPIC_IDS:
        n = len(groups[tid])
        total += n
        print(f"  {TOPIC_FILE[tid]:45s} {n:5d}")
    print(f"  {'TOTAL':45s} {total:5d}")
    assert total == len(arts), f"count mismatch {total} != {len(arts)}"

    if args.stats or not args.build:
        for tid in TOPIC_IDS:
            print(f"\n--- {TOPIC_NAME[tid]} ({len(groups[tid])}) sample ---")
            step = max(1, len(groups[tid]) // args.sample)
            for a in groups[tid][::step][:args.sample]:
                print(f"  [{a['date']}] {a['title'][:110]}")

    if args.build:
        paths = {}
        for tid in TOPIC_IDS:
            groups[tid].sort(key=lambda x: x["date"])
            p = build_pptx(tid, groups[tid])
            paths[tid] = p
            print(f"built {p} ({len(groups[tid])} slides)")

        if args.send:
            sys.path.insert(0, BASE)
            from dedup import is_file_sent, mark_file_sent
            for tid in TOPIC_IDS:
                fn = TOPIC_FILE[tid]
                n = len(groups[tid])
                if is_file_sent(fn, n):
                    print(f"send {fn}: skipped (already sent)")
                    continue
                caption = (f"{TOPIC_NAME[tid]} | {n} articles | "
                           f"{START_DATE} to {END_DATE} | RPSC RAS Prelims topics")
                ok = send_file(paths[tid], caption)
                if ok:
                    mark_file_sent(fn, n, info=caption)
                print(f"send {fn}: {ok}")


if __name__ == "__main__":
    main()
