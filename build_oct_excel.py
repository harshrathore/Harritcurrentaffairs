"""Build the October 2026 current-affairs Excel workbook (7 headings + chart)."""
import json
import os
from collections import Counter
from datetime import date

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.data_source import AxDataSource, StrRef
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.marker import DataPoint
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

SRC = r"D:\Default Project\data\PIB\excel\oct_classified.json"
OUT = r"D:\Default Project\data\PIB\excel\Current_Affairs_October_2026_Segregated.xlsx"

CATS = ["Indian", "International", "Space", "Defense", "Economic", "Prizes", "Games"]

META = {
    "Indian":        ("Indian Current Affairs", "C00000", "FBE5E5",
                      "National governance, polity, schemes, states, society, health, education"),
    "International": ("International Current Affairs", "2E75B6", "E4EEF9",
                      "World affairs, diplomacy, bilateral visits, UN and global organisations"),
    "Space":         ("Space Current Affairs", "7030A0", "EEE4F7",
                      "ISRO, satellites, launch vehicles, missions, astronomy and space science"),
    "Defense":       ("Defense Current Affairs", "375623", "E6EFDF",
                      "Armed forces, DRDO, missiles, warships, security and strategic affairs"),
    "Economic":      ("Economic Current Affairs", "BF8F00", "FFF2CC",
                      "Economy, GDP, RBI, banking, markets, trade, budget, industry and schemes"),
    "Prizes":        ("Prizes & Awards", "C55A11", "FCE4D6",
                      "Awards, honours, Nobel and Padma awards, literary and film prizes"),
    "Games":         ("Games & Sports", "00B050", "E2F0D9",
                      "Sports events, tournaments, Asian Games, medals and athletes"),
}

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
TITLE_FONT = Font(name="Calibri", size=22, bold=True, color="FFFFFF")
SUB_FONT = Font(name="Calibri", size=11, color="D9E2F3")
BODY_FONT = Font(name="Calibri", size=10)
BOLD = Font(name="Calibri", size=10, bold=True)
LINK_FONT = Font(name="Calibri", size=10, color="0563C1", underline="single")
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def parse_date(s):
    try:
        y, m, d = s.split("-")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[row].height = 30


def build_summary(wb, rows):
    ws = wb.active
    ws.title = "Summary"
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:F1")
    ws["A1"] = "CURRENT AFFAIRS  —  OCTOBER 2026"
    ws["A1"].font = TITLE_FONT
    ws["A1"].fill = PatternFill("solid", fgColor="1F3864")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 46

    ws.merge_cells("A2:F2")
    ws["A2"] = "Segregated by exam headings  |  Indian • International • Space • Defense • Economic • Prizes • Games"
    ws["A2"].font = Font(name="Calibri", size=11, italic=True, color="1F3864")
    ws["A2"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 24

    ws.merge_cells("A3:F3")
    ws["A3"] = (f"Coverage: 01–31 October 2026   |   Sources: PIB + GKToday   |   "
                f"Total articles: {len(rows):,} (duplicates removed)")
    ws["A3"].font = Font(name="Calibri", size=10, color="595959")
    ws["A3"].alignment = Alignment(horizontal="center")

    hdr = 5
    heads = ["Heading", "Articles", "Share", "What it covers", "Open sheet"]
    for i, h in enumerate(heads, 1):
        ws.cell(row=hdr, column=i, value=h)
    style_header(ws, hdr, 5)

    counts = Counter(r["category"] for r in rows)
    total = len(rows)
    start = hdr + 1
    for i, cat in enumerate(CATS):
        r = start + i
        title, color, light, desc = META[cat]
        ws.cell(row=r, column=1, value=title)
        ws.cell(row=r, column=2, value=counts[cat])
        ws.cell(row=r, column=3, value=counts[cat] / total).number_format = "0.0%"
        ws.cell(row=r, column=4, value=desc)
        ws.cell(row=r, column=26, value=cat)         # short name for chart
        link = ws.cell(row=r, column=5, value="Open →")
        link.hyperlink = f"#'{cat}'!A1"
        link.font = LINK_FONT
        link.alignment = Alignment(horizontal="center")

        ws.cell(row=r, column=1).font = Font(name="Calibri", size=10, bold=True, color=color)
        ws.cell(row=r, column=1).fill = PatternFill("solid", fgColor=light)
        for c in range(1, 6):
            ws.cell(row=r, column=c).border = BORDER
            if c in (2, 3):
                ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
            else:
                ws.cell(row=r, column=c).alignment = Alignment(vertical="center", wrap_text=(c == 4))
        ws.row_dimensions[r].height = 26

    tr = start + len(CATS)
    ws.cell(row=tr, column=1, value="TOTAL")
    ws.cell(row=tr, column=2, value=total)
    ws.cell(row=tr, column=3, value=1).number_format = "0.0%"
    for c in range(1, 6):
        cell = ws.cell(row=tr, column=c)
        cell.font = Font(name="Calibri", size=11, bold=True)
        cell.fill = PatternFill("solid", fgColor="D9E2F3")
        cell.border = BORDER
        cell.alignment = Alignment(horizontal="center" if c in (2, 3, 5) else "left")

    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 11
    ws.column_dimensions["C"].width = 9
    ws.column_dimensions["D"].width = 72
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].hidden = True

    chart = BarChart()
    chart.type = "col"
    chart.style = 10
    chart.title = "October 2026 — Articles by Heading"
    chart.y_axis.title = "Number of Articles"
    chart.x_axis.title = None
    data = Reference(ws, min_col=2, min_row=hdr, max_row=start + len(CATS) - 1)
    cats = Reference(ws, min_col=26, min_row=start, max_row=start + len(CATS) - 1)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    # openpyxl defaults categories to numeric refs; force text labels
    chart._charts[0].cat = AxDataSource(
        strRef=StrRef(f=f"'Summary'!$Z${start}:$Z${start + len(CATS) - 1}")
    )
    chart.x_axis.axPos = "b"
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.x_axis.tickLblPos = "low"
    chart.legend = None
    dl = DataLabelList()
    dl.showVal = True
    dl.showSerName = False
    dl.showCatName = False
    dl.showLegendKey = False
    dl.showPercent = False
    dl.dLblPos = "outEnd"
    chart.dataLabels = dl
    chart.gapWidth = 50
    chart.height = 11.5
    chart.width = 23
    series = chart.series[0]
    for i, cat in enumerate(CATS):
        pt = DataPoint(idx=i)
        pt.graphicalProperties.solidFill = META[cat][1]
        pt.graphicalProperties.line.solidFill = META[cat][1]
        series.dPt.append(pt)
    ws.add_chart(chart, "A16")

    ws.print_area = "A1:M42"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    return ws


def write_rows(ws, rows, start_row, with_heading):
    headers = (["S.No", "Heading", "Date", "Title", "Key Points / Summary",
                "Source", "Ministry / Department", "Link"]
               if with_heading else
               ["S.No", "Date", "Title", "Key Points / Summary",
                "Source", "Ministry / Department", "Link"])
    for i, h in enumerate(headers, 1):
        ws.cell(row=start_row, column=i, value=h)
    style_header(ws, start_row, len(headers))
    ws.freeze_panes = f"A{start_row + 1}"
    ws.auto_filter.ref = (f"A{start_row}:"
                          f"{get_column_letter(len(headers))}{start_row + len(rows)}")

    for n, rec in enumerate(rows, 1):
        r = start_row + n
        cat = rec["category"]
        values = ([n, META[cat][0], parse_date(rec["date"]), rec["title"], rec["summary"],
                   rec["source"], rec["ministry"], "Open"]
                  if with_heading else
                  [n, parse_date(rec["date"]), rec["title"], rec["summary"],
                   rec["source"], rec["ministry"], "Open"])
        for c, v in enumerate(values, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=c in (4, 5, 7) if with_heading
                                       else c in (3, 4, 6))

        # date
        dcol = 3 if with_heading else 2
        ws.cell(row=r, column=dcol).number_format = "dd-mmm-yyyy"
        ws.cell(row=r, column=dcol).alignment = Alignment(horizontal="center", vertical="top")

        # category colour strip
        if with_heading:
            cc = ws.cell(row=r, column=2)
            cc.fill = PatternFill("solid", fgColor=META[cat][2])
            cc.font = Font(name="Calibri", size=10, bold=True, color=META[cat][1])

        # numbered / source centred
        ws.cell(row=r, column=1).alignment = Alignment(horizontal="center", vertical="top")
        scol = 6 if with_heading else 5
        ws.cell(row=r, column=scol).alignment = Alignment(horizontal="center", vertical="top")

        lcol = 8 if with_heading else 7
        lc = ws.cell(row=r, column=lcol)
        lc.hyperlink = rec["link"]
        lc.font = LINK_FONT
        lc.alignment = Alignment(horizontal="center", vertical="top")

        # row height from summary length
        lines = max(1, len(rec["summary"]) // 78 + 1)
        ws.row_dimensions[r].height = min(15 * lines + 4, 78)

    return headers


def build_master(wb, rows):
    ws = wb.create_sheet("All Current Affairs")
    ws.sheet_view.showGridLines = False
    ws.merge_cells("A1:H1")
    ws["A1"] = f"October 2026 — All Current Affairs ({len(rows):,} articles)"
    ws["A1"].font = TITLE_FONT
    ws["A1"].fill = PatternFill("solid", fgColor="1F3864")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    ws.merge_cells("A2:H2")
    ws["A2"] = ("Use the Heading filter to view one section, or open the separate heading sheets below. "
                "Sorted by heading, then date.")
    ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="595959")
    ws["A2"].alignment = Alignment(horizontal="center")

    write_rows(ws, rows, 3, with_heading=True)
    widths = [7, 17, 12, 52, 82, 10, 34, 10]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.print_title_rows = "3:3"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    return ws


def build_category(wb, cat, rows):
    title, color, light, desc = META[cat]
    ws = wb.create_sheet(cat)
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = color

    ws.merge_cells("A1:G1")
    ws["A1"] = f"{title.upper()}  —  OCTOBER 2026"
    ws["A1"].font = Font(name="Calibri", size=18, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor=color)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 38

    ws.merge_cells("A2:G2")
    ws["A2"] = f"{len(rows):,} articles   |   {desc}"
    ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="404040")
    ws["A2"].alignment = Alignment(horizontal="center")

    write_rows(ws, rows, 3, with_heading=False)
    # recolour header with category colour
    for c in range(1, 8):
        ws.cell(row=3, column=c).fill = PatternFill("solid", fgColor=color)

    widths = [7, 12, 55, 88, 10, 36, 10]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.print_title_rows = "3:3"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    return ws


def main():
    rows = json.load(open(SRC, encoding="utf-8"))
    rows.sort(key=lambda r: (CATS.index(r["category"]), r["date"], r["title"].lower()))

    wb = Workbook()
    build_summary(wb, rows)
    build_master(wb, rows)
    for cat in CATS:
        subset = [r for r in rows if r["category"] == cat]
        build_category(wb, cat, subset)

    wb.properties.title = "October 2026 Current Affairs — Segregated"
    wb.properties.creator = "Harrit Current Affairs"
    wb.save(OUT)
    print("saved:", OUT)
    print("size MB:", round(os.path.getsize(OUT) / 1024 / 1024, 2))
    for cat in CATS:
        print(f"  {cat:15s} {sum(1 for r in rows if r['category'] == cat):5d}")


if __name__ == "__main__":
    main()
