from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent
BASE_SCRIPT = ROOT / "generate_ceo_report_evidence_pdf.py"
OUT_REPO = ROOT / "data" / "reports" / "至4.2报告.pdf"
OUT_DESKTOP = Path(r"C:\Users\cyh\Desktop\至4.2报告.pdf")
OUT_DOWNLOADS = Path(r"C:\Users\cyh\Documents\Downloads\final_report.pdf")


def load_base():
    spec = importlib.util.spec_from_file_location("ceo_report_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_styles(font_name: str) -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()

    def build(name: str, parent: str, **kwargs) -> ParagraphStyle:
        style = ParagraphStyle(name, parent=styles[parent], fontName=font_name, **kwargs)
        style.wordWrap = "CJK"
        return style

    return {
        "title": build(
            "title42",
            "Title",
            fontSize=22,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
        ),
        "subtitle": build(
            "subtitle42",
            "BodyText",
            fontSize=10.2,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475569"),
        ),
        "section": build(
            "section42",
            "Heading1",
            fontSize=13.2,
            leading=17,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=2,
        ),
        "subsection": build(
            "subsection42",
            "Heading2",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#1d4ed8"),
        ),
        "body": build(
            "body42",
            "BodyText",
            fontSize=9.2,
            leading=13.2,
            textColor=colors.HexColor("#111827"),
        ),
        "small": build(
            "small42",
            "BodyText",
            fontSize=8.2,
            leading=11.2,
            textColor=colors.HexColor("#475569"),
        ),
        "tiny": build(
            "tiny42",
            "BodyText",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#64748b"),
        ),
    }


def footer_factory(base):
    def on_page(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(base.FONT_NAME, 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(doc.leftMargin, 10 * mm, "至4.2报告")
        canvas.drawRightString(A4[0] - doc.rightMargin, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    return on_page


def add_heading(story: list, text: str, style: ParagraphStyle, spacer: float = 3) -> None:
    story.append(Paragraph(text, style))
    story.append(Spacer(1, spacer))


def add_bullets(story: list, items: list[str], style: ParagraphStyle, gap: float = 1.5) -> None:
    for item in items:
        story.append(Paragraph(f"• {item}", style))
        story.append(Spacer(1, gap))


def add_table(
    story: list,
    rows: list[list[object]],
    widths: list[float],
    font_name: str,
    body_size: float = 8.7,
    lead: float = 11.2,
    padding: float = 4,
    alt_rows: bool = True,
) -> None:
    table = Table(rows, colWidths=widths, repeatRows=1)
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), body_size),
        ("LEADING", (0, 0), (-1, -1), lead),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
    ]
    if alt_rows:
        commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]))
    table.setStyle(TableStyle(commands))
    story.append(table)
    story.append(Spacer(1, 5))


def make_status_rows(snapshot: dict, guard: dict) -> list[list[str]]:
    return [
        ["更新截止", snapshot["latest_timestamp"]],
        ["今日新增入库", str(snapshot["today_records"])],
        ["证据守卫", guard["overall_status"]],
        ["关键边界", "今日新增主要是 CEO 要求截图，不是业务事实自动刷新。 [S01,S02]"],
    ]


def make_summary_cards(findings: list[tuple[str, str, str, str]]) -> list[str]:
    cards = []
    for item in findings[:3]:
        headline, evidence, why, src = item
        cards.append(f"<b>{headline}</b><br/>证据：{evidence}<br/>管理含义：{why} [{src}]")
    return cards


def make_focus_blocks(blocks: list[dict]) -> list[tuple[str, dict]]:
    lookup = {block["name"]: block for block in blocks}
    return [
        ("SEO / 增长", lookup["SEO / 增长"]),
        ("中心 / 性能", lookup["中心 / 技术 / 性能"]),
        ("CEX 版本", lookup["CEX 产品 / 版本计划"]),
        ("MoonX", lookup["MoonX / 社媒"]),
        ("韩国招商", lookup["韩国招商 / 运营"]),
    ]


def make_req_rows(req_rows: list[list[str]]) -> list[list[str]]:
    rows = [["CEO 要求", "当前处理状态", "剩余缺口"]]
    for req, status, src, gap in req_rows:
        rows.append([req, f"{status} [{src}]", gap])
    return rows


def make_owner_rows(personal_rows: list[list[str]]) -> list[list[str]]:
    selected = []
    for row in personal_rows:
        if row[0] in {"Tony", "Owen", "Liam", "Rsii"}:
            selected.append([row[0], row[1], row[2], row[4]])
    return [["责任人样本", "已确认事实", "当前缺口", "证据"]] + selected


def compact_blocked(blocked: list[str]) -> list[str]:
    return [
        "不能宣称自动化日报/周报链路已恢复健康。 [S02]",
        "不能把 CEX 需求文档或 owner 分工直接当作上线结果。 [S04,S07-S10]",
        "不能把 AI 二次总结当成一手证据。 [S02]",
        blocked[3],
    ]


def split_refs(refs: list, per_page: int = 10) -> list[list]:
    return [refs[i : i + per_page] for i in range(0, len(refs), per_page)]


def make_ref_cell(ref, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(
        (
            f"<b>{ref.code} {ref.title}</b><br/>"
            f"<font color='#64748b'>{ref.kind} | {ref.when}</font><br/>"
            f"{ref.locator}<br/>"
            f"{ref.note}"
        ),
        styles["tiny"],
    )


def add_focus_cards(story: list, focus_blocks: list[tuple[str, dict]], styles: dict[str, ParagraphStyle]) -> None:
    for label, block in focus_blocks:
        content = (
            f"<b>{label}</b><br/>"
            f"<b>当前状态：</b>{block['good'][0]}<br/>"
            f"<b>未闭环风险：</b>{block['bad'][0]}<br/>"
            f"<b>建议动作：</b>{block['action']} [{block['sources']}]"
        )
        box = Table([[Paragraph(content, styles["body"])]], colWidths=[182 * mm])
        box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(box)
        story.append(Spacer(1, 4))


def add_owner_cards(story: list, personal_rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> None:
    for name, done, gap, _, evidence in personal_rows:
        if name not in {"Tony", "Owen", "Liam", "Rsii"}:
            continue
        content = (
            f"<b>{name}</b><br/>"
            f"<b>已确认事实：</b>{done}<br/>"
            f"<b>当前缺口：</b>{gap} [{evidence}]"
        )
        box = Table([[Paragraph(content, styles["small"])]], colWidths=[88 * mm])
        box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.45, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(box)
        story.append(Spacer(1, 4))


def build_appendix_page(story: list, refs: list, styles: dict[str, ParagraphStyle], base) -> None:
    cells = [make_ref_cell(ref, styles) for ref in refs]
    half = math.ceil(len(cells) / 2)
    left = cells[:half]
    right = cells[half:]
    row_count = max(len(left), len(right))
    rows: list[list[object]] = [["左栏", "右栏"]]
    for idx in range(row_count):
        rows.append(
            [
                left[idx] if idx < len(left) else Paragraph("", styles["tiny"]),
                right[idx] if idx < len(right) else Paragraph("", styles["tiny"]),
            ]
        )
    add_table(
        story,
        rows,
        [91 * mm, 91 * mm],
        base.FONT_NAME,
        body_size=7.4,
        lead=9.6,
        padding=4,
        alt_rows=False,
    )


def build() -> Path:
    base = load_base()
    base.register_font()

    guard = base.latest_evidence_guard()
    snapshot = base.db_snapshot()
    refs = base.sources()
    findings = base.executive_findings()
    blocks = base.department_blocks()
    req_rows = base.req_rows()
    personal_rows = base.personal_rows()
    next_actions = base.next_actions()

    styles = make_styles(base.FONT_NAME)

    OUT_REPO.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT_REPO),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )

    story: list = []

    story.append(Paragraph("至4.2报告", styles["title"]))
    story.append(
        Paragraph(
            "截至 2026-04-02，当天新增入库主要是 CEO 要求截图，不是业务事实自动刷新；自动链路仍为 fail，本稿是人工核验后的证据定稿。 [S01,S02]",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 7))

    add_table(
        story,
        [["字段", "状态"], *make_status_rows(snapshot, guard)],
        [32 * mm, 150 * mm],
        base.FONT_NAME,
        body_size=8.8,
        lead=11.4,
    )

    add_heading(story, "1. 三条关键判断", styles["section"])
    for card in make_summary_cards(findings):
        box = Table([[Paragraph(card, styles["body"])]], colWidths=[182 * mm])
        box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#93c5fd")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(box)
        story.append(Spacer(1, 4))

    add_heading(story, "2. CEO 今日可直接下发的动作", styles["section"])
    add_bullets(story, next_actions, styles["body"], gap=1.8)

    add_heading(story, "3. 证据边界", styles["section"])
    add_bullets(
        story,
        [
            "不能宣称自动化日报/周报链路已恢复健康。 [S02]",
            "不能把需求文档、owner 分工或版本计划直接写成上线结果。 [S04,S07-S10]",
            "不能把 AI 二次总结当成一手证据。 [S02]",
        ],
        styles["body"],
        gap=1.8,
    )

    story.append(PageBreak())
    add_heading(story, "4. 重点风险板", styles["section"])
    story.append(
        Paragraph(
            "只保留截至 4.2 仍需要 CEO 介入的高风险线，不再把同一结论在不同章节重复三遍。",
            styles["small"],
        )
    )
    story.append(Spacer(1, 4))
    add_focus_cards(story, make_focus_blocks(blocks), styles)

    add_heading(story, "5. CEO 要求对应情况", styles["section"])
    add_table(
        story,
        make_req_rows(req_rows),
        [31 * mm, 76 * mm, 75 * mm],
        base.FONT_NAME,
        body_size=8.5,
        lead=10.8,
        padding=4,
    )

    story.append(PageBreak())
    add_heading(story, "6. 当前不能下的结论", styles["section"])
    add_bullets(story, compact_blocked(base.blocked_conclusions()), styles["body"], gap=1.8)
    story.append(Spacer(1, 5))

    add_heading(story, "7. 责任人样本（仅支撑判断）", styles["section"])
    story.append(
        Paragraph(
            "这部分不是正文主线，只保留与 MoonX / 交付闭环直接相关的 4 个样本，避免把 CEO 报告写成逐人流水账。",
            styles["small"],
        )
    )
    story.append(Spacer(1, 4))
    add_owner_cards(story, personal_rows, styles)

    appendix_pages = split_refs(refs, per_page=10)
    for page_index, ref_page in enumerate(appendix_pages, start=1):
        story.append(PageBreak())
        add_heading(story, f"附录 A{page_index}. 关键来源索引", styles["section"])
        story.append(
            Paragraph(
                "按正文引用顺序排。正文只保留 S01-S17 证据码，完整来源压缩在附录，避免主稿被索引拖垮。",
                styles["small"],
            )
        )
        story.append(Spacer(1, 4))
        build_appendix_page(story, ref_page, styles, base)

    on_page = footer_factory(base)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    OUT_DESKTOP.write_bytes(OUT_REPO.read_bytes())
    OUT_DOWNLOADS.write_bytes(OUT_REPO.read_bytes())
    return OUT_DESKTOP


if __name__ == "__main__":
    print(str(build()))
