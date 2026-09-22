import json, os, requests
from datetime import datetime
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

TOKEN = "7792990046:AAGfOItkWgJfTZRFHYNsNcwuqHuyjv3UkGk"
CHAT_ID = "8250786682"

DATA_DIR = r"C:\Users\ratho\Documents\Default Project\data\PIB"
SLIDES_DIR = os.path.join(DATA_DIR, "slides")

DARK_GREEN = RGBColor(0x58, 0x6E, 0x5A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREEN = RGBColor(0xA5, 0xD6, 0xA7)
ACCENT_GREEN = RGBColor(0x2E, 0x7D, 0x32)

CATEGORY_COLORS = {
    "Government Schemes": RGBColor(0x2E, 0x7D, 0x32),
    "Economy & Banking": RGBColor(0x38, 0x8E, 0x3C),
    "Defence": RGBColor(0x1B, 0x5E, 0x20),
    "International / World": RGBColor(0x4C, 0xAF, 0x50),
    "Science & Technology": RGBColor(0x43, 0xA0, 0x47),
    "Sports": RGBColor(0x66, 0xBB, 0x6A),
    "Awards, Honours & Persons in News": RGBColor(0x81, 0xC7, 0x84),
    "Environment & Biodiversity": RGBColor(0x2E, 0x7D, 0x32),
    "Art & Culture": RGBColor(0x38, 0x8E, 0x3C),
    "Places in News": RGBColor(0x1B, 0x5E, 0x20),
    "Reports & Indexes": RGBColor(0x4C, 0xAF, 0x50),
    "Summits & Conferences": RGBColor(0x43, 0xA0, 0x47),
    "PIB": RGBColor(0x01, 0x57, 0x9B),
    "Ministry of Defence": RGBColor(0x1B, 0x5E, 0x20),
    "Ministry of Finance": RGBColor(0x38, 0x8E, 0x3C),
    "Ministry of External Affairs": RGBColor(0x4C, 0xAF, 0x50),
    "Ministry of Education": RGBColor(0x43, 0xA0, 0x47),
}


def get_color(cat):
    return CATEGORY_COLORS.get(cat, ACCENT_GREEN)


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


def add_bg(slide):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = DARK_GREEN


def create_title_slide(prs, month_str, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide)
    add_textbox(slide, 1, 1.5, 11.3, 1, "DAILY CURRENT AFFAIRS",
                font_size=44, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)
    add_textbox(slide, 1, 3.0, 11.3, 1, month_str,
                font_size=36, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)
    add_textbox(slide, 1, 4.3, 11.3, 0.8,
                f"Total Articles: {total} | PIB + GKToday",
                font_size=20, color=LIGHT_GREEN, alignment=PP_ALIGN.CENTER)
    add_textbox(slide, 1, 6.0, 11.3, 0.6, "Harrit Current Affairs",
                font_size=16, color=LIGHT_GREEN, alignment=PP_ALIGN.CENTER)


def create_article_slide(prs, article):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide)
    category = article.get("category", article.get("ministry", ""))
    color = get_color(category)
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = color
    bar.line.fill.background()
    title = article.get("title", "")
    add_textbox(slide, 0.5, 0.3, 12.3, 1, title,
                font_size=28, bold=True, color=WHITE)
    tags = []
    if category:
        tags.append(category)
    source = article.get("source", "")
    if source:
        tags.append(source)
    date = article.get("date", "")[:10]
    if date:
        tags.append(date)
    add_textbox(slide, 0.5, 1.2, 12.3, 0.4, " | ".join(tags),
                font_size=14, color=LIGHT_GREEN)
    content = article.get("content", "").replace("\n", " ")
    add_textbox(slide, 0.5, 1.7, 12.3, 5.3, content,
                font_size=18, color=WHITE)


def generate_month_pptx(month_str, articles):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    month_names = {"06": "June", "07": "July", "08": "August", "09": "September"}
    mn = month_names.get(month_str[5:7], month_str[5:7])
    year = month_str[:4]
    create_title_slide(prs, f"{mn} {year}", len(articles))
    for art in articles:
        create_article_slide(prs, art)
    path = os.path.join(SLIDES_DIR, f"current_affairs_{month_str}.pptx")
    prs.save(path)
    return path


def send_to_telegram(filepath, caption):
    with open(filepath, 'rb') as f:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendDocument",
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"document": (os.path.basename(filepath), f,
                   "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
        )
    return r.json().get("ok", False)


# Load all data
with open(os.path.join(DATA_DIR, "pib_database.json"), encoding="utf-8") as f:
    pib = json.load(f)
with open(os.path.join(DATA_DIR, "current_affairs_database.json"), encoding="utf-8") as f:
    ca = json.load(f)

# Normalize all articles
all_articles = []
for k, v in pib.items():
    d = v.get("date", "")[:10]
    if d:
        all_articles.append({
            "title": v.get("title", ""),
            "content": v.get("content", ""),
            "date": d,
            "category": v.get("ministry", "PIB"),
            "source": "PIB",
        })
for k, v in ca.items():
    d = v.get("date", "")[:10]
    if d:
        all_articles.append({
            "title": v.get("title", ""),
            "content": v.get("content", ""),
            "date": d,
            "category": v.get("category", ""),
            "source": "GKToday",
        })

# Group by month
months = {}
for art in all_articles:
    m = art["date"][:7]
    months.setdefault(m, []).append(art)

os.makedirs(SLIDES_DIR, exist_ok=True)

# Generate and send each month
for m in sorted(months.keys()):
    arts = months[m]
    pptx_path = generate_month_pptx(m, arts)
    month_names = {"06": "June", "07": "July", "08": "August", "09": "September"}
    mn = month_names.get(m[5:7], m[5:7])
    caption = f"{mn} 2026 Current Affairs - {len(arts)} articles (PIB + GKToday)"
    ok = send_to_telegram(pptx_path, caption)
    print(f"{m}: {len(arts)} articles -> sent={ok}")
    # Check for duplicates by checking existing dates
    # to avoid sending same content twice
