from __future__ import annotations

import re
from pathlib import Path

import pypdfium2 as pdfium
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf"
IMAGE_OUT = ROOT / "output" / "images"
FONT_REGULAR = Path(r"C:\Windows\Fonts\NotoSansJP-VF.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\YuGothB.ttc")

NAVY = colors.HexColor("#132544")
BLUE = colors.HexColor("#2867E8")
CYAN = colors.HexColor("#35C5E8")
PALE_BLUE = colors.HexColor("#EDF5FF")
PALE_CYAN = colors.HexColor("#EAFBFF")
PALE_YELLOW = colors.HexColor("#FFF8DE")
TEXT = colors.HexColor("#172033")
MUTED = colors.HexColor("#5E6B82")
LINE = colors.HexColor("#DCE4F0")
GREEN = colors.HexColor("#087B63")


def register_fonts() -> tuple[str, str]:
    regular = "NotoSansJP"
    bold = "NotoSansJP-Bold"
    pdfmetrics.registerFont(TTFont(regular, str(FONT_REGULAR)))
    try:
        pdfmetrics.registerFont(TTFont(bold, str(FONT_BOLD)))
    except Exception:
        bold = regular
    return regular, bold


REGULAR, BOLD = register_fonts()


def clean_inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r'<font color="#2867E8">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


def styles():
    base = getSampleStyleSheet()
    common = dict(fontName=REGULAR, textColor=TEXT, wordWrap="CJK")
    return {
        "cover_eyebrow": ParagraphStyle("cover_eyebrow", parent=base["Normal"], fontName=BOLD, fontSize=10, leading=14, textColor=CYAN, spaceAfter=10),
        "cover_title": ParagraphStyle("cover_title", parent=base["Title"], fontName=BOLD, fontSize=29, leading=39, textColor=colors.white, wordWrap="CJK", spaceAfter=16),
        "cover_sub": ParagraphStyle("cover_sub", parent=base["Normal"], fontName=REGULAR, fontSize=11, leading=19, textColor=colors.HexColor("#DDEAFF"), wordWrap="CJK"),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=BOLD, fontSize=19, leading=27, textColor=NAVY, wordWrap="CJK", spaceBefore=11, spaceAfter=9, keepWithNext=True),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=BOLD, fontSize=14, leading=21, textColor=BLUE, wordWrap="CJK", spaceBefore=10, spaceAfter=7, keepWithNext=True),
        "body": ParagraphStyle("body", parent=base["BodyText"], **common, fontSize=9.5, leading=16, spaceAfter=7),
        "bullet": ParagraphStyle("bullet", parent=base["BodyText"], **common, fontSize=9.3, leading=15, leftIndent=12, firstLineIndent=-8, bulletIndent=2, spaceAfter=4),
        "number": ParagraphStyle("number", parent=base["BodyText"], **common, fontSize=9.3, leading=15, leftIndent=15, firstLineIndent=-12, spaceAfter=4),
        "caption": ParagraphStyle("caption", parent=base["Normal"], fontName=REGULAR, fontSize=7.5, leading=11, textColor=MUTED, wordWrap="CJK"),
        "callout": ParagraphStyle("callout", parent=base["BodyText"], fontName=REGULAR, fontSize=9.5, leading=16, textColor=NAVY, wordWrap="CJK", leftIndent=5, rightIndent=5),
        "table": ParagraphStyle("table", parent=base["BodyText"], fontName=REGULAR, fontSize=8.5, leading=13, textColor=TEXT, wordWrap="CJK"),
    }


ST = styles()


def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    if doc.page > 1:
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, height - 15 * mm, width - 18 * mm, height - 15 * mm)
        canvas.setFont(BOLD, 8)
        canvas.setFillColor(NAVY)
        canvas.drawString(18 * mm, height - 11 * mm, "レベナビ")
        canvas.setFont(REGULAR, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(width - 18 * mm, height - 11 * mm, doc.title)
        canvas.drawCentredString(width / 2, 10 * mm, str(doc.page - 1))
    canvas.restoreState()


class ManualDoc(BaseDocTemplate):
    def __init__(self, filename: Path, title: str):
        super().__init__(
            str(filename),
            pagesize=A4,
            title=title,
            author="レベナビ運営",
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=22 * mm,
            bottomMargin=17 * mm,
        )
        self.title = title
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        self.addPageTemplates(PageTemplate(id="manual", frames=[frame], onPage=header_footer))


def cover(title: str, label: str, subtitle: str, edition: str):
    panel = Table(
        [[
            Paragraph(label, ST["cover_eyebrow"]),
        ], [
            Paragraph(clean_inline(title), ST["cover_title"]),
        ], [
            Paragraph(clean_inline(subtitle), ST["cover_sub"]),
        ]],
        colWidths=[158 * mm],
        rowHeights=[10 * mm, None, None],
    )
    panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("BOX", (0, 0), (-1, -1), 0.8, CYAN),
        ("LEFTPADDING", (0, 0), (-1, -1), 12 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12 * mm),
        ("TOPPADDING", (0, 0), (-1, 0), 7 * mm),
        ("TOPPADDING", (0, 1), (-1, 1), 5 * mm),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 14 * mm),
    ]))
    edition_box = Table([[Paragraph(clean_inline(edition), ST["caption"])]], colWidths=[158 * mm])
    edition_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    return [Spacer(1, 15 * mm), panel, Spacer(1, 12 * mm), edition_box, PageBreak()]


def callout(text: str, color=PALE_CYAN):
    box = Table([[Paragraph(clean_inline(text), ST["callout"])]], colWidths=[158 * mm])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("LINEBEFORE", (0, 0), (0, -1), 4, CYAN if color == PALE_CYAN else colors.HexColor("#F2B84B")),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    return KeepTogether([box, Spacer(1, 3 * mm)])


def markdown_story(text: str, checklist: bool = False):
    lines = text.splitlines()
    story = []
    idx = 1  # skip document H1; cover already contains it
    pending_table: list[list[str]] = []

    def flush_table():
        nonlocal pending_table
        if not pending_table:
            return
        rows = pending_table
        pending_table = []
        if len(rows) >= 2 and all(re.fullmatch(r"\s*:?-+:?\s*", cell) for cell in rows[1]):
            rows = [rows[0]] + rows[2:]
        cells = []
        for row_index, row in enumerate(rows):
            cells.append([
                Paragraph(
                    f'<font color="#FFFFFF"><b>{clean_inline(cell.strip())}</b></font>'
                    if row_index == 0 else clean_inline(cell.strip()),
                    ST["table"],
                )
                for cell in row
            ])
        widths = [45 * mm] + [113 * mm / max(1, len(cells[0]) - 1)] * (len(cells[0]) - 1)
        table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), BOLD),
            ("GRID", (0, 0), (-1, -1), 0.5, LINE),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ]))
        story.append(KeepTogether([table, Spacer(1, 4 * mm)]))

    while idx < len(lines):
        raw = lines[idx].rstrip()
        idx += 1
        if raw.startswith("|") and raw.endswith("|"):
            pending_table.append([item.strip() for item in raw.strip("|").split("|")])
            continue
        flush_table()
        line = raw.strip()
        if not line:
            story.append(Spacer(1, 2 * mm))
        elif line.startswith("## "):
            story.append(Paragraph(clean_inline(line[3:]), ST["h1"]))
        elif line.startswith("### "):
            story.append(Paragraph(clean_inline(line[4:]), ST["h2"]))
        elif re.match(r"^\d+\. ", line):
            number, body = line.split(". ", 1)
            story.append(Paragraph(f"<b>{number}.</b> {clean_inline(body)}", ST["number"]))
        elif line.startswith("- [x] "):
            story.append(Paragraph(f'<font color="#087B63">●</font> {clean_inline(line[6:])}', ST["bullet"]))
        elif line.startswith("- [ ] "):
            story.append(Paragraph(f'<font color="#8793A8">○</font> {clean_inline(line[6:])}', ST["bullet"]))
        elif line.startswith("- "):
            story.append(Paragraph(f'<font color="#2867E8">●</font> {clean_inline(line[2:])}', ST["bullet"]))
        elif line.startswith("公開URL："):
            story.append(callout(line, PALE_BLUE))
        elif "重要な注意" in line or line.startswith("公開画面と基本機能"):
            story.append(callout(line, PALE_YELLOW))
        else:
            story.append(Paragraph(clean_inline(line), ST["body"]))
    flush_table()
    return story


def build(source: str, output: str, label: str, subtitle: str, edition: str, checklist: bool = False):
    source_path = ROOT / source
    output_path = OUT / output
    text = source_path.read_text(encoding="utf-8")
    title = text.splitlines()[0].lstrip("# ").strip()
    doc = ManualDoc(output_path, title)
    story = cover(title, label, subtitle, edition)
    story.extend(markdown_story(text, checklist=checklist))
    doc.build(story)


def render_pages(pdf_name: str, folder_name: str):
    target = IMAGE_OUT / folder_name
    target.mkdir(parents=True, exist_ok=True)
    document = pdfium.PdfDocument(str(OUT / pdf_name))
    for index, page in enumerate(document):
        image = page.render(scale=2.0).to_pil()
        image.save(target / f"page-{index + 1:02d}.png", optimize=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    build(
        "docs/CLIENT_GUIDE.md",
        "revenavi-client-guide.pdf",
        "はじめての方へ",
        "画面を開くところから、毎日の見方まで。順番どおりに進められる、やさしい操作説明です。",
        "クライアント向け｜2026年8月版",
    )
    build(
        "docs/OPERATOR_MANUAL.md",
        "revenavi-operator-manual.pdf",
        "運営担当者用",
        "申込受付、決済、データ取得、問い合わせ、障害対応を安全に進めるための手順書です。",
        "社内運営用｜2026年8月版",
    )
    build(
        "CHECKLIST.md",
        "revenavi-completion-checklist.pdf",
        "公開・営業準備",
        "現在できていることと、営業開始前に必ず終える作業をひと目で確認できます。",
        "進捗確認用｜2026年8月28日更新",
        checklist=True,
    )
    render_pages("revenavi-client-guide.pdf", "client-guide")
    render_pages("revenavi-operator-manual.pdf", "operator-manual")
    render_pages("revenavi-completion-checklist.pdf", "completion-checklist")


if __name__ == "__main__":
    main()
