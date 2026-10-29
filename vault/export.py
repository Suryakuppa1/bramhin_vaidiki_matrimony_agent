"""Word and Excel downloads for Vault results. These files include phone numbers."""
from __future__ import annotations

import io
from datetime import datetime

from display import format_profile_text, profile_sections

COLUMNS = [
    ("name", "Name"),
    ("gender", "Gender"),
    ("age", "Age"),
    ("dob", "DOB"),
    ("birthplace", "Birthplace"),
    ("location", "Present place"),
    ("father_name", "Father"),
    ("mother_name", "Mother"),
    ("phone", "Phone"),
    ("gotram", "Gotram"),
    ("saka", "Saka"),
    ("nakshatram", "Nakshatram"),
    ("padam", "Padam"),
    ("rashi", "Rashi"),
    ("birthtime", "Birth time"),
    ("education", "Education"),
    ("source_file", "Source file"),
]


def _cell(value: object) -> str:
    if value is None or str(value).strip() == "":
        return "Not provided"
    text = str(value).strip()
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def to_xlsx(records: list[dict], summary: str = "") -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    book = Workbook()
    info = book.active
    info.title = "Overview"
    info["A1"] = "WEDDING VAULT"
    info["A1"].font = Font(bold=True, size=18, color="6E2436")
    info["A3"] = "Generated"
    info["B3"] = datetime.now().strftime("%d %b %Y %I:%M %p")
    info["A4"] = "Chosen fields"
    info["B4"] = summary or "All stored profiles"
    info["A5"] = "Profiles"
    info["B5"] = len(records)
    info["A7"] = "This file includes phone numbers. Share it only with people allowed to see these profiles."
    info.column_dimensions["A"].width = 22
    info.column_dimensions["B"].width = 72
    info["B4"].alignment = Alignment(wrap_text=True)

    ws = book.create_sheet("Profiles")
    ws.append([label for _key, label in COLUMNS])
    header_fill = PatternFill("solid", fgColor="7C3142")
    for cell in ws[1]:
        cell.font = Font(color="FFF8F2", bold=True, size=10)
        cell.fill = header_fill
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for index, record in enumerate(records, 2):
        ws.append([_cell(record.get(key)) for key, _label in COLUMNS])
        fill = PatternFill("solid", fgColor="FFF6F2" if index % 2 == 0 else "FFFFFF")
        for cell in ws[index]:
            cell.fill = fill
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for column, width in enumerate([24, 12, 8, 14, 18, 18, 24, 24, 28, 16, 18, 14, 10, 14, 14, 22, 24], 1):
        ws.column_dimensions[get_column_letter(column)].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{max(1, len(records) + 1)}"
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


def to_docx(records: list[dict], summary: str = "") -> bytes:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    title = doc.add_heading("Wedding Vault", 0)
    for run in title.runs:
        run.font.color.rgb = RGBColor(0x6E, 0x24, 0x36)
    doc.add_paragraph(summary or "All stored profiles")
    doc.add_paragraph(f"Profiles: {len(records)}    Generated: {datetime.now():%d %B %Y}")
    note = doc.add_paragraph(
        "Each profile is a biodata sheet. Phone numbers are included. "
        "Share this file only with people allowed to see it."
    )
    note.runs[0].font.size = Pt(10)
    note.runs[0].font.color.rgb = RGBColor(0x6B, 0x53, 0x48)
    if not records:
        doc.add_paragraph("No profiles matched these fields.")
    for index, profile in enumerate(records, 1):
        name = str(profile.get("name") or "").strip() or "Name unavailable"
        heading = doc.add_heading(f"{index}. {name}", level=1)
        for run in heading.runs:
            run.font.color.rgb = RGBColor(0x6E, 0x24, 0x36)
        for section_name, rows in profile_sections(profile, include_phone=True):
            sub = doc.add_heading(section_name, level=2)
            for run in sub.runs:
                run.font.color.rgb = RGBColor(0xA0, 0x6A, 0x3A)
                run.font.size = Pt(12)
            table = doc.add_table(rows=0, cols=2)
            table.style = "Table Grid"
            for label, value in rows:
                cells = table.add_row().cells
                cells[0].text = label
                cells[1].text = value
        # Plain sheet as well, so the file matches the on-screen layout even if styles differ.
        if not profile_sections(profile, include_phone=True):
            doc.add_paragraph(format_profile_text(profile, index=index, include_phone=True))
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()
