import json, sys, os
from datetime import datetime
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
DARK_GRAY = RGBColor(0xE8, 0xF5, 0xE9)
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
    "Sports Current Affairs": RGBColor(0x66, 0xBB, 0x6A),
    "Science & Technology Current Affairs": RGBColor(0x43, 0xA0, 0x47),
}


def load_ca_database():
    try:
        with open(CA_DB, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_articles_by_date(database, target_date=None):
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")
    articles = []
    for aid, art in database.items():
        art_date = art.get("date", "")[:10]
        if art_date == target_date:
            articles.append(art)
    return articles


def get_color(category):
    return CATEGORY_COLORS.get(category, ACCENT_BLUE)


def add_textbox(slide, left, top, width, height, text, font_size=18,
                bold=False, color=DARK_GRAY, alignment=PP_ALIGN.LEFT, font_name="Calibri"):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = alignment
    return tf


def create_title_slide(prs, date_str, total, categories=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = DARK_GREEN

    add_textbox(slide, 1, 1.5, 11.3, 1.5, "DAILY CURRENT AFFAIRS",
                font_size=48, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)
    add_textbox(slide, 1, 3, 11.3, 1, date_str,
                font_size=32, color=WHITE, alignment=PP_ALIGN.CENTER)
    add_textbox(slide, 1, 4.2, 11.3, 0.8,
                f"Total Articles: {total} | Source: GKToday (13 Categories)",
                font_size=20, color=LIGHT_GREEN, alignment=PP_ALIGN.CENTER)

    if categories:
        cat_text = " | ".join([f"{cat}: {count}" for cat, count in categories.items()])
        add_textbox(slide, 0.5, 5.2, 12.3, 0.8, cat_text,
                    font_size=14, color=LIGHT_GREEN, alignment=PP_ALIGN.CENTER)

    add_textbox(slide, 1, 6.5, 11.3, 0.6, "Harrit Current Affairs",
                font_size=16, color=LIGHT_GREEN, alignment=PP_ALIGN.CENTER)


def create_category_slide(prs, category, articles):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    color = get_color(category)

    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = DARK_GREEN

    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.2))
    bar.fill.solid()
    bar.fill.fore_color.rgb = color
    bar.line.fill.background()

    add_textbox(slide, 0.5, 0.2, 12, 0.8, category.upper(),
                font_size=36, bold=True, color=WHITE, alignment=PP_ALIGN.LEFT)

    add_textbox(slide, 10, 0.3, 3, 0.6, f"{len(articles)} articles",
                font_size=18, bold=True, color=WHITE, alignment=PP_ALIGN.RIGHT)

    y = 1.5
    for i, art in enumerate(articles[:8]):
        title = art.get("title", "")[:120]
        content = art.get("content", "")[:150].replace("\n", " ")
        date = art.get("date", "")[:10]

        add_textbox(slide, 0.8, y, 11.5, 0.5, f"{i+1}. {title}",
                    font_size=20, bold=True, color=WHITE)
        add_textbox(slide, 1.2, y + 0.4, 8, 0.5, content,
                    font_size=14, color=LIGHT_GREEN)
        add_textbox(slide, 10, y + 0.4, 3, 0.5, date,
                    font_size=12, color=LIGHT_GREEN, alignment=PP_ALIGN.RIGHT)
        y += 1.1
        if y > 6.5:
            break


def create_article_slide(prs, article):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    category = article.get("category", "")
    color = get_color(category)

    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = DARK_GREEN

    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(0.15))
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

    url = article.get("url", "")
    if url:
        add_textbox(slide, 0.5, 1.6, 12.3, 0.3, url,
                    font_size=10, color=RGBColor(0x81, 0xC7, 0x84))

    content = article.get("content", "").replace("\n", " ")
    add_textbox(slide, 0.5, 2.0, 12.3, 5, content[:4000],
                font_size=18, color=WHITE)


def generate_presentation(target_date=None):
    database = load_ca_database()
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")

    articles = get_articles_by_date(database, target_date)
    if not articles:
        print(f"No articles found for {target_date}")
        return None

    print(f"Found {len(articles)} articles for {target_date}")

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    create_title_slide(prs, target_date, len(articles))

    categories = {}
    for art in articles:
        cat = art.get("category", "General")
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1

    create_title_slide(prs, target_date, len(articles), categories)

    cat_groups = {}
    for art in articles:
        cat = art.get("category", "General")
        if cat not in cat_groups:
            cat_groups[cat] = []
        cat_groups[cat].append(art)

    for cat, cat_articles in cat_groups.items():
        create_category_slide(prs, cat, cat_articles)
        for art in cat_articles[:5]:
            create_article_slide(prs, art)

    os.makedirs(PPTX_DIR, exist_ok=True)
    filename = f"current_affairs_{target_date}.pptx"
    filepath = os.path.join(PPTX_DIR, filename)
    prs.save(filepath)
    print(f"Saved: {filepath}")
    return filepath


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    generate_presentation(date_arg)
