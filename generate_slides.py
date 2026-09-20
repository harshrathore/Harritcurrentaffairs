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
MASTER_FILE = os.path.join(PPTX_DIR, "current_affairs_all.pptx")

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


def create_date_title_slide(prs, date_str, total, page_num=None, categories=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide)

    add_textbox(slide, 1, 1.2, 11.3, 1, "DAILY CURRENT AFFAIRS",
                font_size=44, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)
    add_textbox(slide, 1, 2.5, 11.3, 1, date_str,
                font_size=36, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)
    add_textbox(slide, 1, 3.8, 11.3, 0.8,
                f"Total Articles: {total} | Source: GKToday",
                font_size=20, color=LIGHT_GREEN, alignment=PP_ALIGN.CENTER)

    if page_num:
        add_textbox(slide, 1, 4.5, 11.3, 0.5, f"Page {page_num}",
                    font_size=16, color=LIGHT_GREEN, alignment=PP_ALIGN.CENTER)

    if categories:
        cat_lines = []
        for cat, count in categories.items():
            cat_lines.append(f"{cat}: {count}")
        cat_text = " | ".join(cat_lines)
        add_textbox(slide, 0.5, 5.2, 12.3, 1, cat_text,
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


def get_existing_dates_in_file(filepath):
    """Check which dates already exist in the master file."""
    if not os.path.exists(filepath):
        return set()
    try:
        prs = Presentation(filepath)
        dates = set()
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        text = para.text.strip()
                        if len(text) == 10 and text.count("-") == 2:
                            try:
                                datetime.strptime(text, "%Y-%m-%d")
                                dates.add(text)
                            except ValueError:
                                pass
        return dates
    except Exception:
        return set()


def get_current_page_count(filepath):
    """Get current number of slides in master file."""
    if not os.path.exists(filepath):
        return 0
    try:
        prs = Presentation(filepath)
        return len(prs.slides)
    except Exception:
        return 0


def add_date_to_master(date_str=None):
    """Add a single date's articles to the master file."""
    database = load_ca_database()

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    os.makedirs(PPTX_DIR, exist_ok=True)

    existing_dates = get_existing_dates_in_file(MASTER_FILE)
    if date_str in existing_dates:
        print(f"Date {date_str} already in file, skipping")
        return MASTER_FILE

    articles = [a for a in database.values() if a.get("date", "")[:10] == date_str]
    if not articles:
        print(f"No articles for {date_str}")
        return None

    page_num = get_current_page_count(MASTER_FILE) + 1

    if os.path.exists(MASTER_FILE):
        prs = Presentation(MASTER_FILE)
    else:
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

    print(f"{date_str}: {len(articles)} articles (starting page {page_num})")

    categories = {}
    for art in articles:
        cat = art.get("category", "General")
        categories[cat] = categories.get(cat, 0) + 1

    create_date_title_slide(prs, date_str, len(articles), page_num, categories)

    for art in articles:
        create_article_slide(prs, art)

    prs.save(MASTER_FILE)
    print(f"Saved: {MASTER_FILE} (total slides now: {len(prs.slides)})")
    return MASTER_FILE


def add_dates_to_master(dates):
    """Add multiple dates to master file."""
    for d in dates:
        add_date_to_master(d)


def generate_full_presentation(dates=None):
    """Regenerate entire master file from scratch."""
    database = load_ca_database()

    if not dates:
        dates = sorted(set(a.get("date", "")[:10] for a in database.values() if a.get("date")))

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    total = 0
    page_num = 1

    for date_str in dates:
        articles = [a for a in database.values() if a.get("date", "")[:10] == date_str]
        if not articles:
            continue

        print(f"{date_str}: {len(articles)} articles")
        total += len(articles)

        categories = {}
        for art in articles:
            cat = art.get("category", "General")
            categories[cat] = categories.get(cat, 0) + 1

        create_date_title_slide(prs, date_str, len(articles), page_num, categories)
        page_num += 1

        for art in articles:
            create_article_slide(prs, art)

    os.makedirs(PPTX_DIR, exist_ok=True)
    prs.save(MASTER_FILE)
    print(f"Saved: {MASTER_FILE} ({total} articles)")
    return MASTER_FILE


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--append":
            date_arg = sys.argv[2] if len(sys.argv) > 2 else None
            add_date_to_master(date_arg)
        elif sys.argv[1] == "--range":
            start = datetime.strptime(sys.argv[2], "%Y-%m-%d")
            end = datetime.strptime(sys.argv[3], "%Y-%m-%d")
            dates = []
            current = start
            while current <= end:
                dates.append(current.strftime("%Y-%m-%d"))
                current += timedelta(days=1)
            for d in dates:
                add_date_to_master(d)
        elif sys.argv[1] == "--rebuild":
            generate_full_presentation()
        else:
            for d in sys.argv[1:]:
                add_date_to_master(d)
    else:
        add_date_to_master()
