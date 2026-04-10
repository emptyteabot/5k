from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(r"C:\repo")
DB = ROOT / "data" / "audit_records.sqlite3"
REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_REPO = REPORTS_DIR / "final_report_fact_20260402.pdf"
OUTPUT_DOWNLOADS = Path(r"C:\Users\cyh\Documents\Downloads\final_report.pdf")
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_NAME = "MicrosoftYaHeiFact"


@dataclass(frozen=True)
class DepartmentFinding:
    department: str
    confidence: str
    verified_progress: list[str]
    verified_risks: list[str]
    suggested_actions: list[str]
    evidence: list[str]


@dataclass(frozen=True)
class PersonalSignal:
    name: str
    area: str
    delivered: str
    in_progress: str
    risk: str
    evidence: str


def register_font() -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH), subfontIndex=0))


def styles() -> StyleSheet1:
    sheet = getSampleStyleSheet()
    sheet.add(
        ParagraphStyle(
            name="FactTitle",
            parent=sheet["Title"],
            fontName=FONT_NAME,
            fontSize=20,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
        )
    )
    sheet.add(
        ParagraphStyle(
            name="FactSubtitle",
            parent=sheet["BodyText"],
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475569"),
        )
    )
    sheet.add(
        ParagraphStyle(
            name="FactH1",
            parent=sheet["Heading1"],
            fontName=FONT_NAME,
            fontSize=14,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=6,
            spaceAfter=6,
        )
    )
    sheet.add(
        ParagraphStyle(
            name="FactH2",
            parent=sheet["Heading2"],
            fontName=FONT_NAME,
            fontSize=11.5,
            leading=17,
            textColor=colors.HexColor("#111827"),
            spaceBefore=5,
            spaceAfter=4,
        )
    )
    sheet.add(
        ParagraphStyle(
            name="FactBody",
            parent=sheet["BodyText"],
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=15,
            textColor=colors.HexColor("#1f2937"),
        )
    )
    sheet.add(
        ParagraphStyle(
            name="FactSmall",
            parent=sheet["BodyText"],
            fontName=FONT_NAME,
            fontSize=8.5,
            leading=13,
            textColor=colors.HexColor("#475569"),
        )
    )
    sheet.add(
        ParagraphStyle(
            name="FactBullet",
            parent=sheet["BodyText"],
            fontName=FONT_NAME,
            fontSize=9.4,
            leading=14,
            leftIndent=10,
            firstLineIndent=-8,
            textColor=colors.HexColor("#1f2937"),
        )
    )
    sheet.add(
        ParagraphStyle(
            name="FactCallout",
            parent=sheet["BodyText"],
            fontName=FONT_NAME,
            fontSize=9.3,
            leading=14,
            textColor=colors.HexColor("#0f172a"),
        )
    )
    return sheet


def escape_text(text: str) -> str:
    return escape(text).replace("\n", "<br/>")


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape_text(text), style)


def bullet(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape_text(f"- {text}"), style)


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    page_label = f"BYDFi CEO fact report | page {doc.page}"
    canvas.drawRightString(A4[0] - 14 * mm, 10 * mm, page_label)
    canvas.restoreState()


def load_latest_guard() -> dict:
    files = sorted(REPORTS_DIR.glob("evidence_guard_*.json"), key=lambda item: item.stat().st_mtime)
    if not files:
        return {}
    return json.loads(files[-1].read_text(encoding="utf-8-sig"))


def db_metrics() -> dict[str, str | int]:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    latest_ts = cur.execute("SELECT MAX(message_timestamp) FROM audit_records").fetchone()[0]
    audit_records = cur.execute("SELECT COUNT(*) FROM audit_records").fetchone()[0]
    source_documents = cur.execute("SELECT COUNT(*) FROM source_documents").fetchone()[0]
    meeting_history = cur.execute("SELECT COUNT(*) FROM dept_meeting_history").fetchone()[0]
    audit_runs = cur.execute("SELECT COUNT(*) FROM audit_runs").fetchone()[0]
    manual_today = cur.execute(
        """
        SELECT COUNT(*)
        FROM audit_records
        WHERE source_type='manual_meeting_from_chat_screenshot'
          AND substr(message_timestamp, 1, 10)='2026-04-02'
        """
    ).fetchone()[0]
    conn.close()
    return {
        "latest_ts": latest_ts or "unknown",
        "audit_records": audit_records,
        "source_documents": source_documents,
        "meeting_history": meeting_history,
        "audit_runs": audit_runs,
        "manual_today": manual_today,
    }


def autopilot_state() -> dict:
    state_path = REPORTS_DIR / "autopilot_state.json"
    if not state_path.exists():
        return {}
    return json.loads(state_path.read_text(encoding="utf-8-sig"))


def requirement_rows() -> list[list[str]]:
    return [
        [
            "每个会议记录都要形成结论",
            "已覆盖",
            "正文按部门逐条给出已验证进展、问题、建议；不再用空泛全局口号代替。",
        ],
        [
            "部门 + 个人双维分析",
            "已覆盖",
            "正文同时给部门穿透和个人执行信号；个人部分只基于原始周报/原始消息。",
        ],
        [
            "CEX 要结合周报/版本推进/话题群",
            "部分覆盖",
            "已结合 3.25-3.27 会议与个人周报，但当前库里没有完整 run lineage 和全量版本基线，延期只能谨慎判断。",
        ],
        [
            "MoonX 可单独出分析",
            "已覆盖",
            "正文单列 MoonX 专项，并给出个人执行信号。",
        ],
        [
            "日报在开会前同步",
            "已识别，非本 PDF 交付本体",
            "该要求属于系统运行时效，不是一次性 PDF 可直接完成的事实；正文已明确识别为后续自动推送要求。",
        ],
        [
            "翻译词条先功能词、再行业关键词、再文章翻译",
            "证据不足，未强写",
            "截图里有明确要求，但当前文件夹没有足够翻译原始材料，不强塞进正文。",
        ],
        [
            "文件 -> 数据库 -> MCP -> Skill",
            "部分覆盖",
            "文件和数据库已存在；MCP/Skill 仍是建设方向，不冒充已落地。",
        ],
    ]


def department_findings() -> list[DepartmentFinding]:
    return [
        DepartmentFinding(
            department="SEO / 增长",
            confidence="高",
            verified_progress=[
                "3 月 26 日会议已明确清理高比例无效曝光，questions 模块已做 No index 处理，Cointalk 索引率达到 81%。",
                "LCP 二期、schema 字段、sitemap 优化被明确标注为本周落地项。",
                "相较 3 月 17 日，整站索引率从 35% 提到 38.5%，但仍远低于 55% 目标。",
            ],
            verified_risks=[
                "PSEO 页面约 13 万，但索引率只有 29%，点击仍然很低，两个月内难靠自然惯性翻盘。",
                "新内容 72 小时索引率完成度只有 5%，说明内容新增和收录提速没有真正闭环。",
                "AB 测试已经带来流量倒退，当前策略更接近维稳，不是加速。",
            ],
            suggested_actions=[
                "把 LCP、schema、sitemap、热点页生成四项拆成单独工程任务，绑定负责人、发布日期、验收人。",
                "停止只报流量表象，新增指标必须同时附带索引率和转化指向，否则 SEO 会继续用监控替代交付。",
            ],
            evidence=["[S3] 3.17 SEO项目周会", "[S4] 3.26 会议总结 / SEO项目组周会"],
        ),
        DepartmentFinding(
            department="招商 / 运营 / 活动治理",
            confidence="高",
            verified_progress=[
                "韩国市场本周新增 2 家大型新代理，仍在洽谈活动合作细节。",
                "本周注册、充值、交易量环比提升；对敲用户已批量处理，代理异常佣金也已扣除。",
            ],
            verified_risks=[
                "活动方案临时改动后，部分代理直接认为平台失信，出现充值后立即转出、注册量下滑。",
                "标记价格异常和 PNL 不更新曾触发用户大量投诉，直接伤害平台稳定性口碑。",
                "实时监控和止损指标还停留在会议要求，没有看到已落地的自动播报机制。",
            ],
            suggested_actions=[
                "活动上线前必须先有实时数据看板和止损阈值，不允许先发活动再补监控。",
                "对韩国代理的补偿和口径修复要单列负责人，否则代理信任损耗会比活动收益更贵。",
            ],
            evidence=["[S2] 3.25 会议总结 / 韩国招商周会"],
        ),
        DepartmentFinding(
            department="客服 / 用户体验",
            confidence="中",
            verified_progress=[
                "原报税报表缺少 PNL 字段的问题已经修复上线，客服已可正常导出。",
            ],
            verified_risks=[
                "需要重新统计不满用户并补发含 PNL 的报税资料，说明问题并非修复即结束，用户侧善后还未闭环。",
                "客服会议正文在本地抽取里被截断，培训优化、VIP 识别、AI 模型测试安排缺少完整原始细节，不能继续拔高结论。",
            ],
            suggested_actions=[
                "对已受影响用户建立补发完成清单和时间点，不要只写“已修复”。",
                "客服相关 AI 项只要没有验收结果，就一律视为在途，不上升为部门能力结论。",
            ],
            evidence=["[S4] 3.26 会议总结 / 客服单周会"],
        ),
        DepartmentFinding(
            department="技术平台 / CEX / 性能保障",
            confidence="高",
            verified_progress=[
                "3 月 27 日中心会议显示：中心业务 28 个需求完成 15 个，10 个业务监控优化已上线，平均耗时下降 50%。",
                "现货业务 P0/P1 需求各 4 个均按期上线，现货引擎改造已完成待合入测试。",
                "Tony 的周报显示 CEX K 线委托交互问题已完成，属于可验证的单点交付。",
            ],
            verified_risks=[
                "永续下单 4K 压测验收未通过，Open API 下单 3K 未验收，8 倍流量冲击仍有积压。",
                "大数据技术改造的资产接口管理后台接近测试完成，但前端尚未启动，存在后端先跑、前端未接的脱节。",
                "风控提币、3 月 25 日上线的活动派奖仍无数据反馈，说明部分功能已上线但回收不到经营结果。",
            ],
            suggested_actions=[
                "压测结果必须转为硬门禁，没有通过就不能在管理层报告里写成“性能保障推进中”。",
                "对资产接口管理后台、活动派奖反馈补齐 owner、ETA、验收口径，否则只是在堆进行中状态。",
            ],
            evidence=["[S5] 3.27 会议总结 / 中心会议", "[S8] Tony 周报 2026-03-27"],
        ),
        DepartmentFinding(
            department="MoonX / 社媒 / 预测市场",
            confidence="高",
            verified_progress=[
                "MoonX 线条的执行密度最高：App 架构、后端、UI、社媒四条线都有原始周报，且多数任务完成度在 100%。",
                "Ascen 完成预测市场模块基础架构、列表筛选、交易弹窗、账户创建与资产页接入；Owen 完成多个预测市场后端接口与问题修复。",
                "Rsii 在 3 月 23 日到 3 月 29 日期间完成 29 条推文、活动奖励派发、16 个新增 KOL 报名和 2945 有效增粉。",
            ],
            verified_risks=[
                "Tony 的提现流程仍是 80%；Owen 的编码规范优化是 50%；Lori 的 Web 链上预测 UI 验收只有 50%，App 设计 90%。",
                "MoonX 当前问题不是没人做，而是前后端、设计、宣发还有多处收口未完成，离“可统一上线”仍差一轮联调和验收。",
            ],
            suggested_actions=[
                "把预测市场上线改成统一清单：前端验收、接口联调、设计验收、宣发素材、活动预告必须一起过线。",
                "MoonX 可以单独出专项报告，但不能只报完成率，还要加上线闸门和剩余风险。",
            ],
            evidence=[
                "[S6] Ascen 周报 2026-03-27",
                "[S7] Owen 周报 2026-03-30",
                "[S8] Tony 周报 2026-03-27",
                "[S9] Lori 周报 2026-03-28",
                "[S10] Liam 周报 2026-03-27",
                "[S11] Rsii 周报 2026-03-31",
            ],
        ),
    ]


def personal_signals() -> list[PersonalSignal]:
    return [
        PersonalSignal(
            name="Ascen",
            area="MoonX App",
            delivered="预测市场基础架构、列表筛选、交易弹窗、账户创建、资产页接入全部标 100%。",
            in_progress="下周进入交易下单接口和订单列表/取消订单开发。",
            risk="当前是功能骨架完成，不等于交易闭环完成；需要后端联调和验收结果。",
            evidence="[S6]",
        ),
        PersonalSignal(
            name="Owen",
            area="MoonX 后端",
            delivered="地址标签、授权接口、赎回流程、持仓金额与待领取金额、ES 查询优化等多项已完成。",
            in_progress="预测市场编码规范优化 50%，下周继续问题跟进和 K 线修复。",
            risk="还有规范优化和后续修复项，说明系统性收口未结束。",
            evidence="[S7]",
        ),
        PersonalSignal(
            name="Tony",
            area="CEX + MoonX + 预测市场前端",
            delivered="CEX K 线交互修复 100%，MoonX Bot 标识 100%，预测市场资产页/充值流程 100%。",
            in_progress="预测市场提现流程 80%，下周进入接口联调和盈利领取流程。",
            risk="提现仍未闭环，不能把整条预测市场链路写成已完成。",
            evidence="[S8]",
        ),
        PersonalSignal(
            name="Lori",
            area="MoonX UI",
            delivered="Web 端多个预测市场与交易展示项 100%，盈利地址和流动性池设计完成。",
            in_progress="Web 链上预测 UI 验收 50%，App 链上预测设计 90%。",
            risk="设计完成不等于前端通过验收；UI 仍然卡在最后一段。",
            evidence="[S9]",
        ),
        PersonalSignal(
            name="Liam",
            area="MoonX 后端",
            delivered="稳定币兑换数据库、后台管理接口、Redis 缓存、市价/限价交易均标 100%。",
            in_progress="下周继续完成稳定币兑换其余接口。",
            risk="当前是单人周报自报，尚未看到统一验收或上线回执。",
            evidence="[S10]",
        ),
        PersonalSignal(
            name="Rsii",
            area="MoonX 社媒 / 增长",
            delivered="29 条推文、S4 活动奖励派发、16 个新增 KOL 报名、2945 有效增粉。",
            in_progress="继续做一季度数据汇总、预测市场预告和渠道拓展。",
            risk="增长动作密集，但与预测市场正式上线的联动节奏仍在调整中。",
            evidence="[S11]",
        ),
        PersonalSignal(
            name="Crads",
            area="技术支持 / 基础设施",
            delivered="新 VPN 打通 Kibana/Grafana 生产环境，xxljob 更新上线，后台域名多层安全验证上线，行情域名限速已切换拦截。",
            in_progress="继续研究 ES/Kibana 版本更新、教程映射文档和渗透需求调整。",
            risk="多项工作是支持型上线，业务收益回收和长期稳定性还需要后续验证。",
            evidence="[S12]",
        ),
    ]


def source_index() -> list[list[str]]:
    return [
        ["S1", "audit_records 7932-7935", "2026-04-02", "CEO 聊天截图补录：会议结论、部门/个人分析、日报时效、减少幻觉、文件到 Skill 的方向。"],
        ["S2", "source_documents 2365", "2026-03-25", "3.25 会议总结：韩国招商周会、现货+用户会议。"],
        ["S3", "source_documents 55", "2026-03-17", "3.17 SEO项目周会，用作 SEO 趋势对照。"],
        ["S4", "source_documents 259 / audit_records 3514", "2026-03-26", "3.26 会议总结：SEO 项目组周会、客服单周会、社媒周会、SEO+增长会议。"],
        ["S5", "source_documents 2366 / audit_records 3515", "2026-03-27", "3.27 会议总结：中心会议、单周组长汇报、风控审核双周会、产品部门周会。"],
        ["S6", "audit_records 3286", "2026-03-27", "Ascen 周报：MoonX App 预测市场。"],
        ["S7", "audit_records 3290", "2026-03-30", "Owen 周报：MoonX 后端 / 预测市场。"],
        ["S8", "audit_records 3287", "2026-03-27", "Tony 周报：CEX / MoonX App / 预测市场。"],
        ["S9", "audit_records 3289", "2026-03-28", "Lori 周报：MoonX UI。"],
        ["S10", "audit_records 3288", "2026-03-27", "Liam 周报：MoonX 后端。"],
        ["S11", "audit_records 3294", "2026-03-31", "Rsii 周报：MoonX 社媒与活动。"],
        ["S12", "audit_records 3360", "2026-03-27", "Crads 周报：技术支持 / 基础设施。"],
        ["S13", "audit_records 233 / 211", "2026-03-22 / 2026-03-15", "Night 周报：MoonX Polymarket，对预测市场后台连续性提供补充。"],
        ["S14", "data/reports/autopilot_state.json", "2026-03-31", "自动链路状态：incremental/backfill 失败。"],
        ["S15", "audit_records table metrics + latest evidence_guard json", "2026-04-02", "本地证据边界：记录总量、audit_runs=0、今日新增人工补录 4 条。"],
    ]


def add_section_title(story: list, text: str, st: StyleSheet1) -> None:
    story.append(p(text, st["FactH1"]))


def add_subtitle(story: list, text: str, st: StyleSheet1) -> None:
    story.append(p(text, st["FactH2"]))


def add_bullets(story: list, items: Iterable[str], st: StyleSheet1) -> None:
    for item in items:
        story.append(bullet(item, st["FactBullet"]))


def build() -> Path:
    register_font()
    st = styles()
    metrics = db_metrics()
    guard = load_latest_guard()
    autopilot = autopilot_state()
    now_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DOWNLOADS.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(OUTPUT_REPO),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="BYDFi CEO Fact Report",
        author="OpenAI Codex",
    )
    story: list = []

    story.append(p("BYDFi CEO事实版报告", st["FactTitle"]))
    story.append(
        p(
            f"生成时间：{now_local} | 报告边界：2026-03-23 至 2026-04-02 | 目标：满足 CEO 最新要求，但不再复写旧版的无证据判断",
            st["FactSubtitle"],
        )
    )
    story.append(Spacer(1, 6))

    callout_rows = [
        [p("这份报告与旧版的区别", st["FactCallout"])],
        [
            p(
                "1) 只写能在本地文件或 SQLite 中直接定位到的事实。 2) 把资料缺口写出来，不拿缺口硬凑结论。 "
                "3) 个人部分只作为执行信号，不做 HR 式性格评价。",
                st["FactCallout"],
            )
        ],
    ]
    callout = Table(callout_rows, colWidths=[182 * mm])
    callout.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#60a5fa")),
                ("INNERPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(callout)
    story.append(Spacer(1, 8))

    add_section_title(story, "1. 数据边界", st)
    boundary_points = [
        f"本地 SQLite 当前共有 audit_records={metrics['audit_records']}，source_documents={metrics['source_documents']}，dept_meeting_history={metrics['meeting_history']}，audit_runs={metrics['audit_runs']}。[S15]",
        f"当前库中最新记录时间是 {metrics['latest_ts']}。2026-04-02 这一天新增的 4 条记录全部来自 CEO 聊天截图的手工补录，不是自动抓取的新业务事实。[S1][S15]",
        f"自动链路最近一次心跳停在 {autopilot.get('heartbeat_at', 'unknown')}；增量和回填都失败，最近失败原因分别指向找不到 run_incremental_cycle.py / run_history_backfill.py。[S14]",
        f"最新 evidence guard 状态为 {guard.get('overall_status', 'unknown')}。这意味着当前报告可用于方向决策和任务拆解，不应被解读为“自动化链路已恢复健康”。[S14][S15]",
    ]
    add_bullets(story, boundary_points, st)
    story.append(Spacer(1, 4))

    add_section_title(story, "2. CEO 最新要求映射", st)
    req_table = Table(
        requirement_rows(),
        colWidths=[44 * mm, 28 * mm, 110 * mm],
        repeatRows=1,
    )
    req_table._argW[0:0] = []  # keep mypy quiet about private attribute usage
    req_table = Table(
        [["要求", "状态", "落实方式 / 仍缺什么"]] + requirement_rows(),
        colWidths=[44 * mm, 28 * mm, 110 * mm],
        repeatRows=1,
    )
    req_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8.6),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(req_table)
    story.append(Spacer(1, 6))

    add_section_title(story, "3. 本周最重要的管理结论", st)
    top_findings = [
        "第一，数据链路仍然坏着。今天能确认的新东西主要是 CEO 自己补进来的要求，不是系统自动捕获的新业务实况。[S1][S14][S15]",
        "第二，SEO 不是完全没动，而是“监控和整理动作明显多于真正把指标拉回目标的工程动作”。索引率略有改善，但离目标仍远，72 小时新内容索引率更差。[S3][S4]",
        "第三，MoonX 是当前执行最密集、最像在推进的一条线，但它也还没到可庆祝阶段，仍卡在提现、UI 验收、联调和上线收口。[S6][S7][S8][S9][S10][S11]",
        "第四，招商/活动侧不是缺工作量，而是缺活动规则稳定性和数据监控。活动一变更，代理信任和注册质量马上受到反噬。[S2]",
        "第五，技术平台/CEX 的单点交付存在，但压测、反馈回收、前后端衔接仍有明显短板，尤其是高并发验收没有过线。[S5][S8]",
    ]
    add_bullets(story, top_findings, st)
    story.append(Spacer(1, 4))

    add_section_title(story, "4. 部门穿透分析", st)
    for finding in department_findings():
        add_subtitle(story, f"{finding.department} | 可信度：{finding.confidence}", st)
        story.append(p("已验证进展", st["FactSmall"]))
        add_bullets(story, finding.verified_progress, st)
        story.append(p("已验证问题 / 风险", st["FactSmall"]))
        add_bullets(story, finding.verified_risks, st)
        story.append(p("建议动作", st["FactSmall"]))
        add_bullets(story, finding.suggested_actions, st)
        story.append(p("证据：" + "；".join(finding.evidence), st["FactSmall"]))
        story.append(Spacer(1, 5))

    add_section_title(story, "5. 个人执行信号", st)
    story.append(
        p(
            "说明：以下内容只代表原始周报里可验证的执行信号，不代表绩效定性。只要没有测试回执、上线回执或统一验收，就不能把“100%”直接解释成业务闭环。",
            st["FactSmall"],
        )
    )
    personal_rows = [["人员", "范围", "已验证交付", "在途事项 / 风险", "证据"]]
    for signal in personal_signals():
        personal_rows.append(
            [
                signal.name,
                signal.area,
                signal.delivered,
                f"{signal.in_progress} {signal.risk}",
                signal.evidence,
            ]
        )
    personal_table = Table(personal_rows, colWidths=[18 * mm, 26 * mm, 66 * mm, 64 * mm, 16 * mm], repeatRows=1)
    personal_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                ("LEADING", (0, 0), (-1, -1), 10.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14532d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(personal_table)
    story.append(Spacer(1, 6))

    add_section_title(story, "6. MoonX 专项结论", st)
    moonx_points = [
        "MoonX 这条线最像一个真正能拉出专项报告的业务单元，因为它同时有 App、后端、UI、社媒四类原始周报，且同一周内可以互相印证。[S6][S7][S8][S9][S10][S11]",
        "当前最扎实的部分是预测市场与稳定币兑换相关开发，多个成员都给出了明确完成项；最薄弱的部分是上线收口，包括提现流程、UI 验收、设计收尾、宣发排期。[S7][S8][S9][S10][S11]",
        "因此 MoonX 可以单列成报告，但不能写成“已准备就绪”。更准确的说法是：开发推进密度高，进入联调和上线治理阶段。[S6][S7][S8][S9][S10]",
    ]
    add_bullets(story, moonx_points, st)
    story.append(Spacer(1, 4))

    add_section_title(story, "7. 当前不能负责任下结论的部分", st)
    unknowns = [
        "不能给出“自动化报告链路已恢复”的结论，因为 autopilot 仍是 fail-closed，audit_runs 依然为 0。[S14][S15]",
        "不能给出“确定延期”的全面判断，因为当前库里没有完整版本基线、owner、ETA、验收口径的统一映射。[S2][S4][S5]",
        "不能把个人周报里的完成度直接翻译成绩效优劣，因为大部分只是本人汇报，缺少测试和上线回执。[S6][S7][S8][S9][S10][S11][S12]",
        "不能强写翻译专项结论，因为当前文件夹中没有足够的翻译原始材料，只有 CEO 的流程要求。[S1]",
        "客服、产品、风控若干会议正文在本地抽取中存在截断，能够写到的只有前半段已清晰落盘的部分，后半段宁缺毋滥。[S2][S4][S5]",
    ]
    add_bullets(story, unknowns, st)
    story.append(Spacer(1, 4))

    add_section_title(story, "8. 接下来 7 天最该盯的动作", st)
    next_actions = [
        "补齐数据链路。先修复 incremental/backfill 的入口脚本和 run lineage，再谈自动日报，否则每天都在用人工补丁装自动化。[S14][S15]",
        "SEO 四项工程动作直接点名 owner 和发布日期：LCP、schema、sitemap、热点页生成。没有日期的项目，管理层视为未开工。[S3][S4]",
        "对韩国活动建立实时看板和止损线，把“代理信任”当经营资产来管，不要再在活动改规则后被动解释。[S2]",
        "把 MoonX 上线改成跨团队闸门，不再让前端、后端、UI、社媒各自报 100% 然后在上线前互相等。[S6][S7][S8][S9][S10][S11]",
        "技术平台把压测结果变成红线，不通过就不接受“性能优化进行中”的周报说法。[S5]",
    ]
    add_bullets(story, next_actions, st)
    story.append(Spacer(1, 4))

    add_section_title(story, "9. 证据索引", st)
    index_table = Table(
        [["编号", "来源", "日期", "说明"]] + source_index(),
        colWidths=[12 * mm, 42 * mm, 28 * mm, 100 * mm],
        repeatRows=1,
    )
    index_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8.0),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(index_table)

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    OUTPUT_DOWNLOADS.write_bytes(OUTPUT_REPO.read_bytes())
    return OUTPUT_DOWNLOADS


if __name__ == "__main__":
    final_path = build()
    print(str(final_path))
