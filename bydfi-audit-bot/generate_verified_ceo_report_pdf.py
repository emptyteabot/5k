from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parent
REPORT_MD = ROOT / "data" / "reports" / "verified_ceo_report_20260402.md"
REPORT_PDF = ROOT / "data" / "reports" / "verified_ceo_report_20260402.pdf"
DOWNLOAD_PDF = Path(r"C:\Users\cyh\Documents\Downloads\final_report.pdf")
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_NAME = "MicrosoftYaHei"


def register_font() -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH), subfontIndex=0))


def build_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleCN",
            parent=styles["Title"],
            fontName=FONT_NAME,
            fontSize=22,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=8,
        ),
        "meta": ParagraphStyle(
            "MetaCN",
            parent=styles["Normal"],
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475569"),
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "H1CN",
            parent=styles["Heading1"],
            fontName=FONT_NAME,
            fontSize=15,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "H2CN",
            parent=styles["Heading2"],
            fontName=FONT_NAME,
            fontSize=12.2,
            leading=18,
            textColor=colors.HexColor("#1d4ed8"),
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "BodyCN",
            parent=styles["BodyText"],
            fontName=FONT_NAME,
            fontSize=9.6,
            leading=15,
            textColor=colors.HexColor("#111827"),
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "BulletCN",
            parent=styles["BodyText"],
            fontName=FONT_NAME,
            fontSize=9.4,
            leading=15,
            textColor=colors.HexColor("#111827"),
            leftIndent=10,
            firstLineIndent=-8,
            spaceAfter=3,
        ),
    }


def escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\t", "    ")
    )


def add_header_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(doc.leftMargin, A4[1] - 10 * mm, "BYDFI CEO 手工核验报告")
    canvas.drawRightString(A4[0] - doc.rightMargin, 8 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


def parse_markdown(styles: dict[str, ParagraphStyle]):
    story = []
    lines = REPORT_MD.read_text(encoding="utf-8-sig").splitlines()
    title_seen = False

    meta_line = (
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        "口径：仅保留可核验一手证据，不把自动链路失败伪装成业务进展"
    )

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            story.append(Spacer(1, 3))
            continue

        if line.startswith("# "):
            text = escape(line[2:].strip())
            if not title_seen:
                story.append(Paragraph(text, styles["title"]))
                story.append(Paragraph(escape(meta_line), styles["meta"]))
                title_seen = True
            else:
                story.append(Paragraph(text, styles["h1"]))
            continue

        if line.startswith("## "):
            story.append(Paragraph(escape(line[3:].strip()), styles["h1"]))
            continue

        if line.startswith("### "):
            story.append(Paragraph(escape(line[4:].strip()), styles["h2"]))
            continue

        if line.startswith("- "):
            story.append(Paragraph(f"• {escape(line[2:].strip())}", styles["bullet"]))
            continue

        story.append(Paragraph(escape(line), styles["body"]))

    return story


def build_pdf() -> Path:
    register_font()
    REPORT_PDF.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(REPORT_PDF),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
        title="BYDFI CEO 手工核验报告",
        author="OpenAI Codex",
    )

    styles = build_styles()
    story = parse_markdown(styles)
    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    DOWNLOAD_PDF.write_bytes(REPORT_PDF.read_bytes())
    return REPORT_PDF


if __name__ == "__main__":
    path = build_pdf()
    print(str(path))
