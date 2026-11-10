"""Verify the generated October 2026 Excel workbook."""
import json
import os

from openpyxl import load_workbook

XLSX = r"D:\Default Project\data\PIB\excel\Current_Affairs_October_2026_Segregated.xlsx"
SRC = r"D:\Default Project\data\PIB\excel\oct_classified.json"
CATS = ["Indian", "International", "Space", "Defense", "Economic", "Prizes", "Games"]

wb = load_workbook(XLSX)
print("sheets:", wb.sheetnames)
print("size MB:", round(os.path.getsize(XLSX) / 1024 / 1024, 2))

summ = wb["Summary"]
print("summary rows:")
for r in range(5, 14):
    vals = [summ.cell(row=r, column=c).value for c in range(1, 4)]
    if vals[0]:
        print("  ", vals)
print("charts on summary:", len(summ._charts))

rows = json.load(open(SRC, encoding="utf-8"))
counts = {c: sum(1 for x in rows if x["category"] == c) for c in CATS}
print("source counts:", counts, "total", len(rows))

ok = True
for cat in CATS:
    ws = wb[cat]
    # header row 3, data from row 4
    n = 0
    r = 4
    while ws.cell(row=r, column=1).value is not None:
        if ws.cell(row=r, column=7).hyperlink is None:
            print("  missing link", cat, r)
            ok = False
            break
        n += 1
        r += 1
    status = "OK" if n == counts[cat] else "MISMATCH"
    if n != counts[cat]:
        ok = False
    print(f"{cat:15s} rows={n:5d} expected={counts[cat]:5d} {status}")

master = wb["All Current Affairs"]
n = 0
r = 4
while master.cell(row=r, column=1).value is not None:
    n += 1
    r += 1
print("master rows:", n, "expected:", len(rows), "OK" if n == len(rows) else "MISMATCH")
print("ALL CHECKS PASS" if ok and n == len(rows) else "CHECK FAILED")
