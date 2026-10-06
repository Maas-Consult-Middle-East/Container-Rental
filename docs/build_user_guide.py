from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "user_guide.md"
OUTPUT = ROOT / "BADR_Container_Management_User_Guide.docx"

NAVY = "17365D"
PALE_BLUE = "EAF2F8"
PALE_GRAY = "F4F6F7"
GRID = "D9D9D9"
BLACK = RGBColor(0, 0, 0)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=100, start=120, bottom=100, end=120) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = borders.find(qn(f"w:{edge}"))
        if tag is None:
            tag = OxmlElement(f"w:{edge}")
            borders.append(tag)
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), "6")
        tag.set(qn("w:color"), GRID)


def keep_with_next(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    if p_pr.find(qn("w:keepNext")) is None:
        p_pr.append(OxmlElement("w:keepNext"))


def add_field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, end])


def add_inline(paragraph, text: str) -> None:
    pieces = re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text)
    for piece in pieces:
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**"):
            run = paragraph.add_run(piece[2:-2])
            run.bold = True
        elif piece.startswith("`") and piece.endswith("`"):
            run = paragraph.add_run(piece[1:-1])
            run.font.name = "Courier New"
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(55, 55, 55)
        else:
            paragraph.add_run(piece)


def style_document(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.68)
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.78)
    section.header_distance = Inches(0.3)
    section.footer_distance = Inches(0.3)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = BLACK
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.12
    normal.paragraph_format.keep_together = True

    title = styles["Title"]
    title.font.name = "Aptos Display"
    title.font.size = Pt(30)
    title.font.bold = True
    title.font.color.rgb = BLACK
    title.paragraph_format.space_after = Pt(10)

    for name, size, before, after in (
        ("Heading 1", 20, 18, 8),
        ("Heading 2", 15, 15, 6),
        ("Heading 3", 12, 12, 4),
        ("Heading 4", 10.5, 9, 3),
    ):
        style = styles[name]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = BLACK
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    if "Code Block" not in styles:
        code = styles.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
        code.font.name = "Courier New"
        code.font.size = Pt(9.5)
        code.font.color.rgb = RGBColor(45, 45, 45)
        code.paragraph_format.left_indent = Inches(0.25)
        code.paragraph_format.space_before = Pt(4)
        code.paragraph_format.space_after = Pt(7)


def add_header_footer(doc: Document) -> None:
    section = doc.sections[0]
    header = section.header.paragraphs[0]
    header.text = "BADR Container Management"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in header.runs:
        run.font.name = "Aptos"
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor(80, 80, 80)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run("BADR Container  |  Page ")
    run.font.name = "Aptos"
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(80, 80, 80)
    add_field(footer, "PAGE")


def add_cover(doc: Document) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Inches(1.25)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("BADR")
    run.bold = True
    run.font.name = "Aptos Display"
    run.font.size = Pt(18)
    run.font.color.rgb = BLACK

    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("Container Management")

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(18)
    run = subtitle.add_run("Detailed User and Workflow Guide")
    run.font.name = "Aptos Display"
    run.font.size = Pt(16)
    run.font.color.rgb = BLACK

    summary = doc.add_paragraph()
    summary.alignment = WD_ALIGN_PARAGRAPH.CENTER
    summary.paragraph_format.left_indent = Inches(0.65)
    summary.paragraph_format.right_indent = Inches(0.65)
    summary.paragraph_format.space_before = Pt(24)
    add_inline(
        summary,
        "Operating manual for container rentals, reservations, contracts, movements, trips, returns, billing, commissions, fleet maintenance, reporting, and administration in ERPNext.",
    )

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.paragraph_format.space_before = Inches(0.8)
    r = meta.add_run("Application: container\nPlatform: Frappe and ERPNext\nBusiness: BADR Container")
    r.font.name = "Aptos"
    r.font.size = Pt(10.5)
    r.font.color.rgb = RGBColor(65, 65, 65)

    doc.add_page_break()


def add_contents(doc: Document, headings: list[str]) -> None:
    doc.add_heading("Contents", level=1)
    intro = doc.add_paragraph("This guide is organized around setup, daily work, financial integration, controls, and detailed reference material.")
    intro.paragraph_format.space_after = Pt(10)
    for heading in headings:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        p.add_run(heading)
    doc.add_page_break()


def add_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    cols = len(rows[0])
    table = doc.add_table(rows=1, cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.style = "Table Grid"
    set_table_borders(table)

    widths = {
        2: [2.05, 4.75],
        3: [1.55, 1.75, 3.5],
        4: [1.25, 1.25, 1.55, 2.75],
    }.get(cols, [6.8 / cols] * cols)

    for col, text in enumerate(rows[0]):
        cell = table.rows[0].cells[col]
        cell.width = Inches(widths[col])
        set_cell_shading(cell, NAVY)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        add_inline(p, text)
        for run in p.runs:
            run.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.font.size = Pt(9.5)

    for index, row in enumerate(rows[1:], start=1):
        cells = table.add_row().cells
        for col, text in enumerate(row):
            cell = cells[col]
            cell.width = Inches(widths[col])
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if index % 2 == 0:
                set_cell_shading(cell, PALE_BLUE)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if len(text) < 24 else WD_ALIGN_PARAGRAPH.LEFT
            add_inline(p, text)
            for run in p.runs:
                run.font.size = Pt(9.2)

    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    after = doc.add_paragraph()
    after.paragraph_format.space_after = Pt(2)


def parse_markdown(doc: Document, text: str) -> None:
    lines = text.splitlines()
    in_code = False
    code_lines: list[str] = []
    index = 0
    skipped_title = False
    skipped_subtitle = False
    page_break_headings = {
        "Before daily use",
        "Invoices and payments",
        "Dashboard and reports",
        "Complete report directory",
        "Common end-to-end scenarios",
        "Quick transaction reference",
    }

    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                in_code = False
                if code_lines and code_lines[0].startswith("flowchart"):
                    p = doc.add_paragraph(style="Code Block")
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.add_run(
                        "Customer → Container Type → Empty Container → Optional Reservation → Active Contract → Rental Operations → Pull → Return → Completed Contract\n"
                        "Active Contract → Sales Invoice → Payment Entry"
                    )
                else:
                    p = doc.add_paragraph(style="Code Block")
                    p.add_run("\n".join(code_lines))
            index += 1
            continue

        if in_code:
            code_lines.append(stripped)
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-+", lines[index + 1]):
            table_lines = [stripped]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            rows = [[cell.strip() for cell in row.strip("|").split("|")] for row in table_lines]
            add_table(doc, rows)
            continue

        if stripped.startswith("# "):
            skipped_title = True
            index += 1
            continue
        if stripped.startswith("## ") and skipped_title and not skipped_subtitle:
            skipped_subtitle = True
            index += 1
            continue

        heading_match = re.match(r"^(#{2,4})\s+(.+)$", stripped)
        if heading_match:
            level = len(heading_match.group(1)) - 1
            heading = heading_match.group(2)
            if heading in page_break_headings and len(doc.paragraphs) > 4:
                doc.add_page_break()
            doc.add_heading(heading, level=level)
            index += 1
            continue

        numbered = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if numbered:
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.space_after = Pt(2.5)
            add_inline(p, numbered.group(2))
            index += 1
            continue

        bullet = re.match(r"^-\s+(.+)$", stripped)
        if bullet:
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(2.5)
            add_inline(p, bullet.group(1))
            index += 1
            continue

        if not stripped:
            index += 1
            continue

        p = doc.add_paragraph()
        add_inline(p, stripped)
        index += 1


def main() -> None:
    if len(sys.argv) > 1:
        output = Path(sys.argv[1]).resolve()
    else:
        output = OUTPUT
    source_text = SOURCE.read_text(encoding="utf-8")
    headings = [
        match.group(1)
        for match in re.finditer(r"^## (.+)$", source_text, flags=re.MULTILINE)
        if match.group(1) != "Detailed User and Workflow Guide"
    ]

    doc = Document()
    style_document(doc)
    add_header_footer(doc)
    add_cover(doc)
    add_contents(doc, headings)
    parse_markdown(doc, source_text)

    props = doc.core_properties
    props.title = "BADR Container Management Detailed User and Workflow Guide"
    props.subject = "Container rental operations in ERPNext"
    props.author = "BADR Container"
    props.keywords = "ERPNext, Frappe, container rental, operations, fleet, accounting"
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    print(output)


if __name__ == "__main__":
    main()
