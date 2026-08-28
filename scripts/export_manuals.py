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
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.utils import ImageReader
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
CLIENT_ASSETS = ROOT / "docs" / "manual-assets" / "client-guide"
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


def draw_wrapped(canvas, text: str, x: float, y_top: float, width: float, size: float = 8.5, leading: float = 13, color=TEXT, bold: bool = False):
    style = ParagraphStyle(
        "visual-note",
        fontName=BOLD if bold else REGULAR,
        fontSize=size,
        leading=leading,
        textColor=color,
        wordWrap="CJK",
    )
    paragraph = Paragraph(clean_inline(text), style)
    _, height = paragraph.wrap(width, 200 * mm)
    paragraph.drawOn(canvas, x, y_top - height)
    return height


def visual_header(canvas, title: str, step: str):
    page_width, page_height = (A4[1], A4[0])
    canvas.setFillColor(NAVY)
    canvas.rect(0, page_height - 20 * mm, page_width, 20 * mm, stroke=0, fill=1)
    canvas.setFillColor(CYAN)
    canvas.setFont(BOLD, 8)
    canvas.drawString(12 * mm, page_height - 8 * mm, step)
    canvas.setFillColor(colors.white)
    canvas.setFont(BOLD, 18)
    canvas.drawString(12 * mm, page_height - 16 * mm, title)
    canvas.setFillColor(colors.HexColor("#C9D8F4"))
    canvas.setFont(REGULAR, 7.5)
    canvas.drawRightString(page_width - 12 * mm, page_height - 12 * mm, "レベナビ｜画面でわかる使い方")


def visual_screen_page(canvas, title: str, step: str, image_name: str, notes: list[str], markers: list[tuple[float, float]], tip: str):
    page_width, page_height = (A4[1], A4[0])
    visual_header(canvas, title, step)
    image = ImageReader(str(CLIENT_ASSETS / image_name))
    image_width, image_height = image.getSize()
    screen_x, screen_y = 10 * mm, 27 * mm
    screen_box_width, screen_box_height = 205 * mm, 156 * mm
    ratio = min(screen_box_width / image_width, screen_box_height / image_height)
    draw_width, draw_height = image_width * ratio, image_height * ratio
    draw_y = screen_y + (screen_box_height - draw_height) / 2
    canvas.setFillColor(MUTED)
    canvas.setFont(REGULAR, 7)
    canvas.drawString(screen_x, page_height - 24.5 * mm, "画面例｜表示している数値は説明用です")
    canvas.setFillColor(colors.white)
    canvas.roundRect(screen_x - 1.5 * mm, draw_y - 1.5 * mm, draw_width + 3 * mm, draw_height + 3 * mm, 3 * mm, stroke=0, fill=1)
    canvas.setStrokeColor(LINE)
    canvas.roundRect(screen_x - 1.5 * mm, draw_y - 1.5 * mm, draw_width + 3 * mm, draw_height + 3 * mm, 3 * mm, stroke=1, fill=0)
    canvas.drawImage(image, screen_x, draw_y, width=draw_width, height=draw_height, preserveAspectRatio=True, mask="auto")

    for index, (nx, ny) in enumerate(markers, start=1):
        target_x = screen_x + nx * draw_width
        target_y = draw_y + (1 - ny) * draw_height
        badge_x = target_x + 3.5 * mm
        badge_y = target_y + 3.5 * mm
        canvas.setStrokeColor(colors.white)
        canvas.setLineWidth(3)
        canvas.line(badge_x - 2 * mm, badge_y - 2 * mm, target_x, target_y)
        canvas.setStrokeColor(BLUE)
        canvas.setLineWidth(1.4)
        canvas.line(badge_x - 2 * mm, badge_y - 2 * mm, target_x, target_y)
        canvas.setFillColor(BLUE)
        canvas.setStrokeColor(colors.white)
        canvas.circle(badge_x, badge_y, 4.3 * mm, stroke=1, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont(BOLD, 8.5)
        canvas.drawCentredString(badge_x, badge_y - 2.7, str(index))

    notes_x = 224 * mm
    notes_width = 62 * mm
    notes_y = page_height - 31 * mm
    for index, note in enumerate(notes, start=1):
        canvas.setFillColor(PALE_BLUE if index % 2 else colors.white)
        canvas.setStrokeColor(LINE)
        note_height = 17 * mm if len(note) < 38 else 21 * mm
        canvas.roundRect(notes_x, notes_y - note_height, notes_width, note_height - 2 * mm, 2.5 * mm, stroke=1, fill=1)
        canvas.setFillColor(BLUE)
        canvas.circle(notes_x + 6 * mm, notes_y - 7 * mm, 3.5 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont(BOLD, 7.5)
        canvas.drawCentredString(notes_x + 6 * mm, notes_y - 8.8 * mm, str(index))
        draw_wrapped(canvas, note, notes_x + 12 * mm, notes_y - 3.5 * mm, notes_width - 15 * mm, size=7.7, leading=11.5)
        notes_y -= note_height

    canvas.setFillColor(PALE_YELLOW)
    canvas.setStrokeColor(colors.HexColor("#F2D37C"))
    canvas.roundRect(notes_x, 27 * mm, notes_width, 18 * mm, 2.5 * mm, stroke=1, fill=1)
    canvas.setFillColor(colors.HexColor("#8A5A00"))
    canvas.setFont(BOLD, 7.5)
    canvas.drawString(notes_x + 4 * mm, 40 * mm, "覚えておくこと")
    draw_wrapped(canvas, tip, notes_x + 4 * mm, 37 * mm, notes_width - 8 * mm, size=7.2, leading=10.5, color=colors.HexColor("#6B4A00"))
    canvas.showPage()


def build_client_visual():
    output_path = OUT / "revenavi-client-guide.pdf"
    page_width, page_height = (A4[1], A4[0])
    canvas = pdfcanvas.Canvas(str(output_path), pagesize=(page_width, page_height), pageCompression=1)
    canvas.setTitle("レベナビ 画面でわかる使い方")
    canvas.setAuthor("レベナビ運営")

    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, page_width, page_height, stroke=0, fill=1)
    canvas.setFillColor(CYAN)
    canvas.setFont(BOLD, 10)
    canvas.drawString(20 * mm, page_height - 30 * mm, "はじめての方へ")
    canvas.setFillColor(colors.white)
    canvas.setFont(BOLD, 31)
    canvas.drawString(20 * mm, page_height - 55 * mm, "レベナビ")
    canvas.setFont(BOLD, 23)
    canvas.drawString(20 * mm, page_height - 70 * mm, "画面でわかる使い方")
    canvas.setFillColor(colors.HexColor("#DDEAFF"))
    canvas.setFont(REGULAR, 11)
    canvas.drawString(20 * mm, page_height - 86 * mm, "実際のアプリ画面に、押す場所と見る場所を直接示しました。")
    canvas.setFillColor(colors.HexColor("#243A61"))
    canvas.roundRect(20 * mm, 30 * mm, 255 * mm, 62 * mm, 7 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont(BOLD, 13)
    canvas.drawString(32 * mm, 75 * mm, "この冊子の使い方")
    canvas.setFont(REGULAR, 10)
    canvas.drawString(32 * mm, 61 * mm, "① 画面の青い番号を見つける")
    canvas.drawString(32 * mm, 49 * mm, "② 右側の同じ番号の説明を読む")
    canvas.drawString(32 * mm, 37 * mm, "③ 上から順番に操作する")
    canvas.setFillColor(CYAN)
    canvas.circle(232 * mm, 60 * mm, 16 * mm, stroke=0, fill=1)
    canvas.setFillColor(NAVY)
    canvas.setFont(BOLD, 24)
    canvas.drawCentredString(232 * mm, 56 * mm, "1")
    canvas.setFillColor(colors.HexColor("#AFC5E9"))
    canvas.setFont(REGULAR, 8)
    canvas.drawString(20 * mm, 16 * mm, "クライアント向け｜2026年8月版")
    canvas.showPage()

    visual_screen_page(canvas, "ログインする", "STEP 1", "login.png", [
        "パスワードで入るときは、こちらを選びます。",
        "メールのリンクだけで入ることもできます。",
        "登録したメールアドレスを入力します。",
        "パスワードを入れ、青い「ログイン」を押します。",
        "忘れたときは、ここから新しいパスワードを設定できます。",
    ], [(0.43, 0.25), (0.60, 0.25), (0.50, 0.36), (0.50, 0.52), (0.63, 0.61)], "メールは、最初に登録したアドレスを使います。")

    visual_screen_page(canvas, "まず概要を見る", "STEP 2", "dashboard-overview.png", [
        "左のメニューで、見たい画面を切り替えます。",
        "右上の日付を変えると、その日の情報になります。",
        "競合の平均価格です。空室がある宿だけで計算します。",
        "この日の参考ランクと販売価格です。",
        "「部屋なし」の競合数です。需要が強い目安になります。",
        "下には、ランクの理由と大きな価格変化が出ます。",
    ], [(0.12, 0.25), (0.89, 0.08), (0.33, 0.34), (0.60, 0.34), (0.90, 0.34), (0.58, 0.74)], "最初は「概要」だけ見れば大丈夫です。")

    visual_screen_page(canvas, "参考価格の理由を確認する", "STEP 3", "dashboard-proposal.png", [
        "選んだ日付と、参考ランクが表示されます。",
        "空室がある競合施設の平均最安値を基にしています。",
        "登録した販売価格表から、最も近いランクを示します。",
        "値上げ・値下げ・部屋なしの変化を確認します。",
    ], [(0.24, 0.36), (0.34, 0.62), (0.23, 0.48), (0.77, 0.49)], "これは参考情報です。価格が自動で書き換わることはありません。")

    visual_screen_page(canvas, "競合の価格を比べる", "STEP 4", "dashboard-comparison.png", [
        "左側に、登録した競合施設が並びます。",
        "上の日付ごとに、その日の最安値を比べます。",
        "赤は値上げ、青は値下げです。",
        "グレーの「満室」は、予約できる部屋がない状態です。",
    ], [(0.12, 0.55), (0.49, 0.23), (0.53, 0.55), (0.82, 0.55)], "「履歴なし」は故障ではありません。毎日取得すると比較できるようになります。")

    visual_screen_page(canvas, "カレンダーで先の日付を見る", "STEP 5", "dashboard-calendar.png", [
        "月の見出しを押すと、開いたり閉じたりできます。",
        "日付ごとに、参考ランクと販売価格が出ます。",
        "赤い背景は競合価格の上昇、青は低下の目安です。",
        "各競合の価格や「部屋なし」も日付の中で確認できます。",
        "通常プランでは3か月または6か月を表示できます。",
    ], [(0.20, 0.15), (0.92, 0.35), (0.14, 0.53), (0.93, 0.46), (0.49, 0.81)], "日付を押すと、その日の参考価格の理由へ移動します。")

    visual_screen_page(canvas, "販売ランクと競合施設を設定する", "STEP 6", "settings.png", [
        "A〜Dの販売価格を入力します。Aが最も高い価格です。",
        "必要ならE・Fなどのランクを追加できます。",
        "比較する宿の名前と予約サイトURLを入力します。",
        "通常プランでは3施設まで登録できます。",
        "最後に必ず「変更を保存」を押します。",
    ], [(0.39, 0.26), (0.09, 0.43), (0.49, 0.62), (0.89, 0.53), (0.91, 0.95)], "URLは、じゃらん・楽天トラベルなどの宿のページをそのまま貼り付けます。")

    visual_screen_page(canvas, "毎日の確認は3分で終わります", "STEP 7", "dashboard-overview.png", [
        "ログインしたら、まず競合平均価格を見ます。",
        "次に、参考ランクと部屋なし件数を見ます。",
        "気になる日はカレンダーから選びます。",
        "理由を読んで、実際の販売価格を決めます。",
    ], [(0.35, 0.34), (0.75, 0.35), (0.14, 0.30), (0.38, 0.72)], "迷ったときは、設定を変えずに運営担当へご連絡ください。")

    canvas.save()


def render_pages(pdf_name: str, folder_name: str):
    target = IMAGE_OUT / folder_name
    target.mkdir(parents=True, exist_ok=True)
    document = pdfium.PdfDocument(str(OUT / pdf_name))
    for index, page in enumerate(document):
        image = page.render(scale=2.0).to_pil()
        image.save(target / f"page-{index + 1:02d}.png", optimize=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    build_client_visual()
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
