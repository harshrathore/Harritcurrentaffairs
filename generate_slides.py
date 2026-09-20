import json, sys, os
from datetime import datetime, timedelta
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "..", "data", "PIB")
CA_DB = os.path.join(DATA_DIR, "current_affairs_database.json")
PPTX_DIR = os.path.join(DATA_DIR, "slides")

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
}


def load_ca_database():
    try:
        with open(CA_DB, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_color(category):
    return CATEGORY_COLORS.get(category, ACCENT_GREEN)


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


def create_date_title_slide(prs, date_str, total, categories=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide)

    add_textbox(slide, 1, 1.2, 11.3, 1, "DAILY CURRENT AFFAIRS",
                font_size=44, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)
    add_textbox(slide, 1, 2.5, 11.3, 1, date_str,
                font_size=36, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)
    add_textbox(slide, 1, 3.8, 11.3, 0.8,
                f"Total Articles: {total} | Source: GKToday",
                font_size=20, color=LIGHT_GREEN, alignment=PP_ALIGN.CENTER)

    if categories:
        cat_lines = []
        for cat, count in categories.items():
            cat_lines.append(f"{cat}: {count}")
        cat_text = " | ".join(cat_lines)
        add_textbox(slide, 0.5, 4.8, 12.3, 1, cat_text,
                    font_size=14, color=LIGHT_GREEN, alignment=PP_ALIGN.CENTER)

    add_textbox(slide, 1, 6.5, 11.3, 0.6, "Harrit Current Affairs",
                font_size=16, color=LIGHT_GREEN, alignment=PP_ALIGN.CENTER)


def create_article_slide(prs, article):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide)

    category = article.get("category", "")
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
    add_textbox(slide, 0.5, 1.7, 12.3, 5.3, content[:4000],
                font_size=18, color=WHITE)


def generate_presentation(dates=None, output_name=None):
    database = load_ca_database()

    if not dates:
        dates = [datetime.now().strftime("%Y-%m-%d")]

    if isinstance(dates, str):
        dates = [dates]

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    total_articles = 0

    for date_str in dates:
        articles = [a for a in database.values() if a.get("date", "")[:10] == date_str]
        if not articles:
            print(f"No articles for {date_str}, skipping")
            continue

        print(f"{date_str}: {len(articles)} articles")
        total_articles += len(articles)

        categories = {}
        for art in articles:
            cat = art.get("category", "General")
            categories[cat] = categories.get(cat, 0) + 1

        create_date_title_slide(prs, date_str, len(articles), categories)

        for art in articles:
            create_article_slide(prs, art)

    if total_articles == 0:
        print("No articles found for any date")
        return None

    os.makedirs(PPTX_DIR, exist_ok=True)
    if not output_name:
        output_name = "current_affairs_all.pptx"
    filepath = os.path.join(PPTX_DIR, output_name)
    prs.save(filepath)
    print(f"Saved: {filepath} ({total_articles} articles)")
    return filepath


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--range":
            start = datetime.strptime(sys.argv[2], "%Y-%m-%d")
            end = datetime.strptime(sys.argv[3], "%Y-%m-%d")
            dates = []
            current = start
            while current <= end:
                dates.append(current.strftime("%Y-%m-%d"))
                current += timedelta(days=1)
            out = sys.argv[4] if len(sys.argv) > 4 else None
            generate_presentation(dates, out)
        else:
            generate_presentation(sys.argv[1:])
    else:
        generate_presentation()
