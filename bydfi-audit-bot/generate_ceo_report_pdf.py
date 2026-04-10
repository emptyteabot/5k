from __future__ import annotations

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
OUTPUT_DIR = ROOT / "output" / "pdf"
OUTPUT_PDF = OUTPUT_DIR / "ceo_backfill_report.pdf"
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_NAME = "MicrosoftYaHei"


TITLE = "入职以来补交汇报"
SUBTITLE = "决策支持、专项推进与机制重建"
META = "岗位：CEO 助理 | 形式：补交汇报 PDF"


SECTIONS: list[tuple[str, list[str]]] = [
    (
        "说明",
        [
            "前期未按日提交，是我在管理动作上的缺口。过去这段时间，我的工作重心没有放在碎片化流水汇报上，而是集中在更有杠杆的工作上：为 CEO 做信息过滤与报告支持，推进 Event-Bypass 黑客松项目，以及推动客服 AI 应用与翻译旧账专项。",
        ],
    ),
    (
        "一、阶段性主线",
        [
            "决策支持：围绕 CEO 关注的问题持续整理重点事项、异常点和待拍板问题，提升信息上收效率和可用性。",
            "基建探索：推进 Event-Bypass 项目，目标是缩短业务需求从提出到配置落地之间的链路成本。",
            "一线提效：针对客服组在 Claude 使用中的实际问题进行答疑和纠偏，推动 AI 工具从“会用”走向“能解决业务问题”。",
            "历史债务推进：主导旧账翻译任务推进，推动长期遗留事项从分散堆积转为可管理、可执行专项。",
        ],
    ),
    (
        "二、按入职顺序补交",
        [
            "入职第 1 天：完成入职对接，快速建立对公司核心业务线、主要协作关系和当前重点事项的整体认识，并明确 CEO 助理岗位不应停留在事务传递，而应承担信息过滤、问题暴露和跨部门推进职责。",
            "入职第 2 天：开始梳理 CEO 报告的结构和汇报口径，判断哪些事项值得上收、哪些异常需要优先暴露，将汇报目标从“描述过程”转成“支持决策”。",
            "入职第 3 天：深入了解重点业务和跨部门推进情况，识别协作链路中的信息断层、推进滞后和责任不清问题，为后续 CEO 简报输出和专项推进建立问题底图。",
            "入职第 4 天：开始持续产出 CEO 支持材料，把分散信息收束为重点事项、风险点和待拍板问题，减少管理噪音，提高判断效率。",
            "入职第 5 至 6 天：围绕黑客松项目推进 Event-Bypass，梳理需求表达、配置生成和落地路径，打磨方案和原型，目标是让项目既具备展示价值，也具备后续业务化落地的可能。",
            "入职第 7 至 8 天：为客服组解答 Claude 在实际应用中的问题，处理使用误差、回答偏差和落地障碍，并持续跟进使用反馈，沉淀更贴近业务的使用方式，减少重复试错和低质量沟通。",
            "入职第 9 天：主导旧账翻译任务推进，梳理术语、流程、协作接口和推进节奏，把长期遗留事项转成可管理、可推进的专项。",
            "入职第 10 天至今：汇总前期工作，重新校准后续汇报机制，准备将输出固定为更高频、更聚焦的日报形式，不再停留于个人流水。",
        ],
    ),
    (
        "三、当前阶段判断",
        [
            "这段时间我主要在做三类高杠杆工作：CEO 决策支持、专项推进、组织提效。",
            "相比单纯事务承接，我更希望把助理岗位做成信息过滤器、执行推进器和问题暴露口，而不是被动传话。",
            "下一阶段，我会把这些工作进一步沉淀为稳定的日报节奏和更清晰的专项推进机制。",
        ],
    ),
    (
        "四、后续机制",
        [
            "从今日起，日报恢复为日更，固定围绕四项输出：昨日关键推进、当前风险或卡点、今日重点动作、需您拍板事项。",
            "重大异常将不等日报，单独上报。",
        ],
    ),
]


def register_font() -> None:
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH), subfontIndex=0))


def build_pdf() -> Path:
    register_font()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCN",
        parent=styles["Title"],
        fontName=FONT_NAME,
        fontSize=21,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleCN",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=10.5,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
        spaceAfter=18,
    )
    section_style = ParagraphStyle(
        "SectionCN",
        parent=styles["Heading2"],
        fontName=FONT_NAME,
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#111827"),
        spaceBefore=10,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "BodyCN",
        parent=styles["BodyText"],
        fontName=FONT_NAME,
        fontSize=10.5,
        leading=17,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=6,
    )

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title=TITLE,
        author="OpenAI Codex",
    )

    story = [
        Paragraph(TITLE, title_style),
        Paragraph(SUBTITLE, subtitle_style),
        Paragraph(META, subtitle_style),
        Spacer(1, 4),
    ]

    for heading, bullets in SECTIONS:
        story.append(Paragraph(heading, section_style))
        for item in bullets:
            story.append(Paragraph(f"• {item}", body_style))
        story.append(Spacer(1, 4))

    doc.build(story)
    return OUTPUT_PDF


if __name__ == "__main__":
    path = build_pdf()
    print(path)
