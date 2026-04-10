from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "audit_records.sqlite3"
REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_PDF = REPORTS_DIR / "final_report_verified_20260402.pdf"
OUTPUT_MD = REPORTS_DIR / "final_report_verified_20260402.md"
OUTPUT_JSON = REPORTS_DIR / "final_report_verified_20260402.json"
DOWNLOADS_COPY = Path(r"C:\Users\cyh\Documents\Downloads\final_report_verified_20260402.pdf")
DESKTOP_COPY = Path(r"C:\Users\cyh\Desktop\final_report_verified_20260402.pdf")
OLD_REPORT_PATH = Path(r"C:\Users\cyh\Documents\Downloads\final_report.pdf")
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_NAME = "MicrosoftYaHei"


@dataclass(frozen=True)
class EvidenceRef:
    ref_id: str
    title: str
    timestamp: str
    note: str


def register_font() -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH), subfontIndex=0))


def iso_to_cn(value: str) -> str:
    if not value:
        return ""
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    return dt.astimezone(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def fetch_scalar(cur: sqlite3.Cursor, sql: str, params: tuple = ()) -> int | str | None:
    row = cur.execute(sql, params).fetchone()
    return row[0] if row else None


def load_metrics() -> dict[str, object]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    metrics = {
        "audit_records": fetch_scalar(cur, "SELECT COUNT(*) FROM audit_records"),
        "source_documents": fetch_scalar(cur, "SELECT COUNT(*) FROM source_documents"),
        "dept_meeting_history": fetch_scalar(cur, "SELECT COUNT(*) FROM dept_meeting_history"),
        "inbound_messages": fetch_scalar(cur, "SELECT COUNT(*) FROM inbound_messages"),
        "audit_runs": fetch_scalar(cur, "SELECT COUNT(*) FROM audit_runs"),
        "latest_message_timestamp": fetch_scalar(cur, "SELECT MAX(message_timestamp) FROM audit_records"),
        "short_history_count": fetch_scalar(cur, "SELECT COUNT(*) FROM dept_meeting_history WHERE length(content) <= 40"),
        "today_manual_requirements": fetch_scalar(
            cur,
            "SELECT COUNT(*) FROM audit_records WHERE message_timestamp = ? AND reporter_name = 'Kater'",
            ("2026-04-02T08:55:11.795441+00:00",),
        ),
    }
    conn.close()
    return metrics


def load_autopilot_state() -> dict[str, object]:
    path = REPORTS_DIR / "autopilot_state.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def old_report_provenance() -> dict[str, object]:
    return {
        "exists": OLD_REPORT_PATH.exists(),
        "size_bytes": OLD_REPORT_PATH.stat().st_size if OLD_REPORT_PATH.exists() else 0,
        "created_at": OLD_REPORT_PATH.stat().st_mtime if OLD_REPORT_PATH.exists() else 0,
        "description": (
            "旧版 Downloads/final_report.pdf 为 14 页 HeadlessChrome 打印产物，PDF 元信息显示标题为 "
            "`rpt.html`，正文包含大量未逐条引用的一揽子管理判断。"
        ),
    }


def build_payload() -> dict[str, object]:
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    metrics = load_metrics()
    autopilot = load_autopilot_state()

    refs = [
        EvidenceRef("audit_records#7932", "今日要求：每个会议记录都要形成结论并指出部门问题与建议", "2026-04-02T08:55:11.795441+00:00", "CEO 当日新增硬要求"),
        EvidenceRef("audit_records#7934", "时效要求：日报需在开会前同步，保证每天自动更新", "2026-04-02T08:55:11.795441+00:00", "CEO 对时效的明确要求"),
        EvidenceRef("audit_records#7935", "质量要求：减少幻觉，重点信息需人工核对后同步", "2026-04-02T08:55:11.795441+00:00", "CEO 对质量和人工核对的明确要求"),
        EvidenceRef("dept_meeting_history#172", "3.26 SEO 会议总结 / 社媒周会", "2026-03-26T06:44:56.432746+00:00", "SEO 真实会议记录，含指标与本周动作"),
        EvidenceRef("audit_records#255", "3.8.9版本--1.30 / 永续优化V1.1", "2026-03-31T10:28:01.541817+00:00", "CEX 版本计划，含顺延与上线状态"),
        EvidenceRef("audit_records#735", "【迭代】永续优化V1.1", "2026-03-25T10:00:18.538232+00:00", "CEX 版本计划消息入口，含 owner 分配"),
        EvidenceRef("audit_records#755", "【需求】跟单包赔券", "2026-03-25T10:00:18.538232+00:00", "CEX 需求，前后端/后台/测试 owner 明确"),
        EvidenceRef("audit_records#786", "【需求】智能比例跟单", "2026-03-25T10:00:18.538232+00:00", "CEX 需求，owner 与 PRD 链接明确"),
        EvidenceRef("audit_records#801", "【需求】支持USDC合约", "2026-03-25T10:00:18.538232+00:00", "CEX 需求，owner 明确，范围复杂"),
        EvidenceRef("audit_records#803", "【迭代】体验金V3.0", "2026-03-25T10:00:18.538232+00:00", "CEX 迭代，owner 明确"),
        EvidenceRef("audit_records#816", "【需求】web合约网格", "2026-03-25T10:00:18.538232+00:00", "CEX 需求，owner 明确"),
        EvidenceRef("audit_records#3287", "Tony 本周工作 03.23~03.26", "2026-03-27T14:56:00+00:00", "CEX + MoonX 个人周报"),
        EvidenceRef("audit_records#3286", "Ascen 本周工作 03.23-03.27", "2026-03-27T12:42:00+00:00", "MoonX App 周报"),
        EvidenceRef("audit_records#3290", "Owen 本周工作 03.23~03.27", "2026-03-30T03:42:00+00:00", "MoonX 周报"),
        EvidenceRef("audit_records#3288", "Liam 本周周报 03.23~03.27", "2026-03-27T15:39:00+00:00", "MoonX 后端周报"),
        EvidenceRef("audit_records#3289", "Lori 本周 MoonX-UI 工作内容", "2026-03-28T07:34:00+00:00", "MoonX UI 周报"),
        EvidenceRef("audit_records#3340", "Saber 招商产品周报 03.23-03.27", "2026-03-29T17:17:00+00:00", "MoonX/活动产品周报"),
        EvidenceRef("audit_records#3294", "Rsii 本周工作 0323-0329", "2026-03-31T01:22:00+00:00", "MoonX 社媒运营周报"),
        EvidenceRef("audit_records#233", "Night 本周工作 03.16~03.22", "2026-03-22T17:17:00+00:00", "MoonX Polymarket 周报"),
        EvidenceRef("audit_records#2340", "Yohan: 周报要结合 CEX 中心版本计划", "2026-03-27T08:07:00+00:00", "周报系统的业务要求"),
        EvidenceRef("audit_records#2374", "unknown: CEX 表一条记录理论上对应一个研发话题群", "2026-03-29T08:11:00+00:00", "当前链路缺失的跨源映射要求"),
        EvidenceRef("data/reports/autopilot_state.json", "autopilot_state.json", "", "自动化链路健康状态"),
        EvidenceRef("data/reports/evidence_guard_2026-04-02T165537_0800.md", "Evidence Guard Audit", "", "当前证据守卫结论"),
    ]

    payload = {
        "title": "BYDFI CEO 要求对齐报告（事实校验版）",
        "subtitle": "替代 2026-03-30 旧版 final_report.pdf 的可追溯版本",
        "generated_at": generated_at,
        "repo_root": str(ROOT),
        "metrics": metrics,
        "autopilot_state": autopilot,
        "old_report": old_report_provenance(),
        "refs": [ref.__dict__ for ref in refs],
        "sections": {
            "executive_summary": [
                "这不是一份可以宣称“全链路日报自动恢复”的验收报告。当前可确认的是：CEO 在 2026-04-02 新增的四条要求已经入库；MoonX 是当前一手周报证据最密集、最可分析的业务线；CEX 存在可直接看到的排期顺延与需求堆积，但还不能对全量延期做封口判断。",
                "当前不能负责地下结论：血战到底逐会议结论、全公司部门排名、所有延期已确认。原因不是措辞保守，而是证据链不到位：`audit_runs=0`，自动链路在 2026-03-31 20:18:37 +08:00 仍显示 degraded，`dept_meeting_history` 中仍有 23 条内容长度不超过 40 的弱记录。",
                "旧版 `Downloads/final_report.pdf` 的来源不是当前这套可追溯脚本，而是 HeadlessChrome 从本地 `rpt.html` 打印出来的 14 页 PDF；其中存在大段未逐条引用的管理判断，本报告不把旧版叙事当证据复用。",
            ],
            "requirement_rows": [
                ["血战到底：每个会议记录形成结论", "未满足", "只有 CEO 当日要求入库（audit_records#7932），没有干净的一手“血战到底”会议包可逐条下结论。", "先补原始会议记录，再分析。"],
                ["周报系统：部门 + 个人分析", "部分满足", "可直接引用 SEO 会议记录（dept_meeting_history#172）和 MoonX 多份个人周报。", "短历史记录与跨源映射仍不足。"],
                ["CEX：进度 + 风险 + 优化", "部分满足", "版本文档和需求文档齐全，周报能证明局部进展。", "无法把每条版本计划稳定映射到话题群和验收结果。"],
                ["MoonX：单独分析", "较高满足", "有连续个人周报与部门会议信号，可做可信的单线分析。", "仍缺统一发布门槛。"],
                ["开会前日报自动更新", "未满足", "autopilot_state.json 显示 2026-03-31 链路 timeout / retry / backfill fail。", "先修链路，再谈自动同步。"],
                ["降低幻觉，重点信息人工核对", "本报告已执行", "本报告只采用明确引用的一手记录，不复用 AI 二次总结做结论。", "后续仍需补 run lineage。"],
            ],
            "stream_findings": {
                "blood": [
                    "当前快照不足以支撑“血战到底”逐会议结论。能确定的只有 CEO 已在 2026-04-02 明确要求此业务线必须结合部门历史做结论、优缺点与建议（audit_records#7932）。",
                    "旧系统里确实混入了与“血战到底”相关的 AI 汇总记录，但这些记录本身就被 Evidence Guard 标记为高风险做法，不应再直接作为 CEO 定稿依据。",
                    "结论：本次报告对“血战到底”只能给出数据缺口和补齐动作，不能假装已经完成会议级穿透分析。",
                ],
                "weekly": [
                    "SEO 部门存在一手会议信号，但当前状态更像“指标监控齐全、关键闭环未完成”。3.26 SEO 会议记录直接写出：整站索引率 38.5%，目标 55%；PSEO 索引率 29%；新内容 72 小时索引率完成度 5%；LCP 二期、schema 字段、sitemap 优化计划在本周落地（dept_meeting_history#172）。",
                    "这说明 SEO 不缺问题识别，缺的是把未来时态动作变成已验收动作。报告里不能把“本周落地”直接写成“已闭环”。",
                    "MoonX 周报层面的个人执行信号明显更干净：多条记录明确写了完成度、未完成项和下周计划，足够支撑“个人执行信号”，但仍不足以做 HR 式优劣排名。",
                ],
                "cex": [
                    "CEX 直接可证实的第一风险是排期顺延已经写在版本文档里，而不是我臆测出来的。`永续优化V1.1` 明确标注：合约跟单与合约网格顺延至 3.9.1 / 3.20，安全中心顺延至 4.20 / 3.9.4；V3.8.9 与 V3.9.4 的上线状态均显示“待开发”（audit_records#255, #735）。",
                    "第二个事实是需求层 owner 并不缺。跟单包赔券、智能比例跟单、USDC 合约、体验金 V3.0、WEB 合约网格等条目都已经把前端、后端、后台、测试 owner 写出来了（audit_records#755, #786, #801, #803, #816）。问题不在于没人负责，而在于当前快照没把“需求 -> 话题群 -> 验收结果”串成闭环。",
                    "第三个事实是局部交付确实存在。Tony 的 03.23~03.26 周报里，CEX 条目“优化 K 线委托点击时其他委托不显示和不可操作”为 100%（audit_records#3287）。所以当前不能把 CEX 写成“完全没推进”，那也是胡说。",
                    "结论：CEX 当前最真实的状态是“计划层和 owner 层已经存在，局部交付存在，但全量版本追踪与验收追踪没有打通”。",
                ],
                "moonx": [
                    "MoonX 是当前最能做出可信分析的业务线，因为直接周报密度高、完成度表达清晰、下周计划也明确。Ascen 报了 6 个 MoonX App 动作全部 100%，并给出下周两个接口开发项（audit_records#3286）。Liam 报了 5 个后端动作全部 100%，下周继续补接口（audit_records#3288）。Owen 报了 7 个完成项、1 个进行中 50%，且写明下周继续跟进预测市场与 K 线修复（audit_records#3290）。",
                    "但 MoonX 不是“可以放心发喜报”。Tony 的提现流程只有 80%（audit_records#3287）；Lori 的 Web 链上预测 UI 验收只有 50%，App 链上预测设计 90%（audit_records#3289）；Owen 的预测市场编码规范优化 50%（audit_records#3290）；Night 仍在做 Polymarket 二期接口与订单 WS（audit_records#233）；Saber 还有预测活动文档整理与内部评审待完成（audit_records#3340）。",
                    "运营侧也不是空话。Rsii 的周报给了明确量化结果：本周 29 条推文、特斯拉活动 616 报名 / 151 有效交易 / 94 获奖、3 月新增 44 个 KOL 其中本周新增 16 个、渠道有效增粉 2945（audit_records#3294）。这是能上 CEO 桌面的业务量化信号。",
                    "结论：MoonX 当前不是“停滞”，而是“交付密集但发布准备分散”。真正的风险在于产品、前端、后端、UI、运营都在推进，但缺一张统一的上线 readiness 清单。",
                ],
            },
            "personal_rows": [
                ["Ascen", "MoonX App", "6 个动作 100%，并给出下周接口开发计划", "无明确延期项，但仍处于功能继续扩张阶段", "高", "audit_records#3286"],
                ["Owen", "MoonX", "7 个完成项；预测市场编码规范优化 50%", "仍有进行中项，需收口", "高", "audit_records#3290"],
                ["Liam", "MoonX 后端", "5 个后端动作 100%，下周继续补接口", "未见验收结果截图，仅有周报文本", "中", "audit_records#3288"],
                ["Lori", "MoonX UI", "多项 Web UI 100%，但验收 50%，App 设计 90%", "前端/UI readiness 未完全收口", "高", "audit_records#3289"],
                ["Tony", "CEX + MoonX", "CEX 1 项 100%，MoonX / 预测市场多项 100%，提现 80%", "跨两条业务线，部分动作未完成", "高", "audit_records#3287"],
                ["Saber", "MoonX / 活动产品", "多项评审 100%，奖池预览 UI 90%", "文档与评审仍在推进", "高", "audit_records#3340"],
                ["Rsii", "MoonX 社媒运营", "给出推文、报名、有效交易、获奖、增粉、KOL 指标", "核心活动仍在上线预热期", "高", "audit_records#3294"],
                ["Night", "MoonX / Polymarket", "多项完成，二期接口与订单 WS 进行中", "上线节点依赖后续对接", "高", "audit_records#233"],
            ],
            "department_rows": [
                ["SEO", "问题识别足够具体，但 KPI 差距仍大，多个关键动作仍是未来时态。", "索引率 38.5% vs 55%；PSEO 29%；72h 索引率完成度 5%。", "下份报告必须绑定 commit / 上线截图 / 指标变化。", "dept_meeting_history#172"],
                ["CEX / 中心", "计划文档与 owner 分配完整，但全链路验收闭环薄弱。", "版本文档明确出现顺延；需求文档 owner 完整；局部周报能证明个别交付。", "每条版本计划必须绑定话题群、owner、ETA、验收值。", "audit_records#255, #735, #755, #786, #801, #803, #816, #3287"],
                ["MoonX", "执行密度最高，但 readiness 被拆散在多个角色、多个 50%-90% 的未完项上。", "Ascen / Owen / Liam / Lori / Tony / Saber / Rsii / Night 多条周报。", "建立统一上线门槛：功能完成、联调完成、UI 验收完成、运营素材完成。", "audit_records#3286, #3290, #3288, #3289, #3287, #3340, #3294, #233"],
            ],
            "unknowns": [
                "不能给“血战到底已经逐会议分析完毕”的结论，因为当前快照没有干净的一手会议包。",
                "不能给“全公司谁效率最好/最差”的结论，因为当前证据主要集中在 MoonX 和局部 CEX，且 `audit_runs=0`。",
                "不能给“所有延期已确认”的结论，因为当前缺少完整的需求 -> 话题群 -> 验收结果映射链。",
                "不能给“日报自动化已恢复”的结论，因为 autopilot 在 2026-03-31 仍是 degraded / failed。",
            ],
            "actions": [
                "P0：把 CEO 明确要求的四条业务线做成固定证据桶，先补“血战到底”原始会议记录，再分析，不要再让 AI 总结回写主证据表。",
                "P0：恢复增量链路并写入 run lineage。没有 run_id / source_ids / prompt_hash 的报告，一律只能当内部草稿。",
                "P1：CEX 每条版本计划强制绑定四个字段：话题群链接、owner、ETA、验收值。否则只算需求堆积，不算推进。",
                "P1：MoonX 在下次开会前补一张统一 readiness 清单，把 50%-90% 的跨角色未完成项收口到一个 owner。",
                "P1：SEO 下次汇报必须从“指标叙述”切到“动作验收”，把 schema / sitemap / LCP 对应的 commit、上线时间和指标回看放进去。",
            ],
        },
    }
    return payload


def escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def build_markdown(payload: dict[str, object]) -> str:
    metrics = payload["metrics"]
    autopilot = payload["autopilot_state"]
    lines = [
        f"# {payload['title']}",
        "",
        payload["subtitle"],
        "",
        f"- 生成时间: {payload['generated_at']}",
        f"- 证据库: {DB_PATH}",
        f"- audit_records: {metrics['audit_records']}",
        f"- source_documents: {metrics['source_documents']}",
        f"- dept_meeting_history: {metrics['dept_meeting_history']}",
        f"- inbound_messages: {metrics['inbound_messages']}",
        f"- audit_runs: {metrics['audit_runs']}",
        f"- 最新业务记录时间: {metrics['latest_message_timestamp']}",
        f"- 弱历史记录数(长度<=40): {metrics['short_history_count']}",
        f"- autopilot 最后心跳: {autopilot.get('heartbeat_at', '')}",
        "",
        "## 一句话结论",
    ]
    lines.extend(f"- {item}" for item in payload["sections"]["executive_summary"])
    lines.extend(["", "## CEO 要求映射"])
    for row in payload["sections"]["requirement_rows"]:
        lines.extend(
            [
                f"### {row[0]}",
                f"- 当前状态: {row[1]}",
                f"- 证据: {row[2]}",
                f"- 当前阻塞: {row[3]}",
                "",
            ]
        )
    lines.append("## 业务线判断")
    for key, heading in [
        ("blood", "血战到底"),
        ("weekly", "周报系统"),
        ("cex", "CEX"),
        ("moonx", "MoonX"),
    ]:
        lines.append(f"### {heading}")
        lines.extend(f"- {item}" for item in payload["sections"]["stream_findings"][key])
        lines.append("")
    lines.append("## 个人执行信号")
    for row in payload["sections"]["personal_rows"]:
        lines.extend(
            [
                f"### {row[0]} / {row[1]}",
                f"- 已证实动作: {row[2]}",
                f"- 风险项: {row[3]}",
                f"- 可信度: {row[4]}",
                f"- 来源: {row[5]}",
                "",
            ]
        )
    lines.append("## 部门反馈")
    for row in payload["sections"]["department_rows"]:
        lines.extend(
            [
                f"### {row[0]}",
                f"- 当前情况: {row[1]}",
                f"- 核心证据: {row[2]}",
                f"- 建议动作: {row[3]}",
                f"- 来源: {row[4]}",
                "",
            ]
        )
    lines.append("## 不可下结论项")
    lines.extend(f"- {item}" for item in payload["sections"]["unknowns"])
    lines.extend(["", "## 下一步动作"])
    lines.extend(f"- {item}" for item in payload["sections"]["actions"])
    lines.extend(["", "## 关键引文索引"])
    for ref in payload["refs"]:
        lines.append(f"- {ref['ref_id']} | {ref['title']} | {ref['timestamp']} | {ref['note']}")
    lines.append("")
    return "\n".join(lines)


def build_pdf(payload: dict[str, object]) -> Path:
    register_font()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCN",
        parent=styles["Title"],
        fontName=FONT_NAME,
        fontSize=20,
        leading=26,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleCN",
        parent=styles["BodyText"],
        fontName=FONT_NAME,
        fontSize=10,
        leading=15,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10,
    )
    h1 = ParagraphStyle(
        "H1CN",
        parent=styles["Heading1"],
        fontName=FONT_NAME,
        fontSize=14,
        leading=20,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=6,
    )
    h2 = ParagraphStyle(
        "H2CN",
        parent=styles["Heading2"],
        fontName=FONT_NAME,
        fontSize=11.5,
        leading=17,
        textColor=colors.HexColor("#111827"),
        spaceBefore=8,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "BodyCN",
        parent=styles["BodyText"],
        fontName=FONT_NAME,
        fontSize=9.6,
        leading=14.5,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=4,
    )
    tiny = ParagraphStyle(
        "TinyCN",
        parent=styles["BodyText"],
        fontName=FONT_NAME,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#475569"),
        spaceAfter=2,
    )

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=str(payload["title"]),
        author="OpenAI Codex",
    )

    metrics = payload["metrics"]
    autopilot = payload["autopilot_state"]
    sections = payload["sections"]
    story = [
        Paragraph(escape(str(payload["title"])), title_style),
        Paragraph(escape(str(payload["subtitle"])), subtitle_style),
        Paragraph(
            escape(
                f"生成时间：{payload['generated_at']} | 数据边界：audit_records={metrics['audit_records']} / "
                f"source_documents={metrics['source_documents']} / dept_meeting_history={metrics['dept_meeting_history']} / "
                f"audit_runs={metrics['audit_runs']}"
            ),
            subtitle_style,
        ),
    ]

    story.append(Paragraph("1. 一句话结论", h1))
    for item in sections["executive_summary"]:
        story.append(Paragraph(f"• {escape(item)}", body))

    story.append(Paragraph("2. 旧版报告逆向结果", h1))
    story.append(
        Paragraph(
            "• 旧版 `Downloads/final_report.pdf` 是 14 页 HeadlessChrome 打印产物，PDF 元信息标题为 `rpt.html`；"
            "它不是当前 evidence-guard 约束下的可追溯定稿。",
            body,
        )
    )
    story.append(
        Paragraph(
            "• 本版报告不复用旧版里的泛化管理判断，只复用本地数据库、会议记录和周报中的可核对事实。",
            body,
        )
    )

    story.append(Paragraph("3. 证据边界", h1))
    boundary_rows = [
        ["指标", "值"],
        ["audit_records", str(metrics["audit_records"])],
        ["source_documents", str(metrics["source_documents"])],
        ["dept_meeting_history", str(metrics["dept_meeting_history"])],
        ["inbound_messages", str(metrics["inbound_messages"])],
        ["audit_runs", str(metrics["audit_runs"])],
        ["最新业务记录时间", str(metrics["latest_message_timestamp"])],
        ["弱历史记录数(长度<=40)", str(metrics["short_history_count"])],
        ["autopilot 最后心跳", str(autopilot.get("heartbeat_at", ""))],
        ["autopilot 链路结论", "2026-03-31 发生 timeout / retry / backfill fail，当前不满足自动日报验收"],
    ]
    boundary_table = Table(boundary_rows, colWidths=[52 * mm, 118 * mm])
    boundary_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#94a3b8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    story.extend([boundary_table, Spacer(1, 4)])

    story.append(Paragraph("4. CEO 要求映射", h1))
    req_rows = [["要求", "状态", "当前可证实情况", "阻塞"]]
    req_rows.extend(sections["requirement_rows"])
    req_table = Table(req_rows, colWidths=[42 * mm, 18 * mm, 68 * mm, 42 * mm])
    req_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.extend([req_table, Spacer(1, 5)])

    story.append(Paragraph("5. 业务线判断", h1))
    for key, heading in [
        ("blood", "5.1 血战到底"),
        ("weekly", "5.2 周报系统"),
        ("cex", "5.3 CEX"),
        ("moonx", "5.4 MoonX"),
    ]:
        story.append(Paragraph(heading, h2))
        for item in sections["stream_findings"][key]:
            story.append(Paragraph(f"• {escape(item)}", body))

    story.append(Paragraph("6. 个人执行信号（仅基于直接周报，不做 HR 评价）", h1))
    personal_rows = [["姓名", "业务线", "已证实动作", "风险项", "可信度", "来源"]]
    personal_rows.extend(sections["personal_rows"])
    personal_table = Table(personal_rows, colWidths=[16 * mm, 24 * mm, 64 * mm, 44 * mm, 10 * mm, 22 * mm])
    personal_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 7.6),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7c3aed")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.extend([personal_table, Spacer(1, 5)])

    story.append(Paragraph("7. 部门反馈", h1))
    dept_rows = [["部门", "当前情况", "核心证据", "建议动作", "来源"]]
    dept_rows.extend(sections["department_rows"])
    dept_table = Table(dept_rows, colWidths=[18 * mm, 50 * mm, 52 * mm, 36 * mm, 24 * mm])
    dept_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 7.8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b45309")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.extend([dept_table, Spacer(1, 5)])

    story.append(Paragraph("8. 不可下结论项", h1))
    for item in sections["unknowns"]:
        story.append(Paragraph(f"• {escape(item)}", body))

    story.append(Paragraph("9. 下一步动作", h1))
    for item in sections["actions"]:
        story.append(Paragraph(f"• {escape(item)}", body))

    story.append(Paragraph("10. 关键引文索引", h1))
    for ref in payload["refs"]:
        story.append(
            Paragraph(
                escape(f"{ref['ref_id']} | {ref['title']} | {ref['timestamp']} | {ref['note']}"),
                tiny,
            )
        )

    doc.build(story)
    return OUTPUT_PDF


def write_outputs(payload: dict[str, object]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_MD.write_text(build_markdown(payload), encoding="utf-8")
    pdf_path = build_pdf(payload)
    shutil.copy2(pdf_path, DOWNLOADS_COPY)
    shutil.copy2(pdf_path, DESKTOP_COPY)
    return pdf_path


def main() -> int:
    payload = build_payload()
    pdf_path = write_outputs(payload)
    print(json.dumps({"pdf": str(pdf_path), "markdown": str(OUTPUT_MD), "json": str(OUTPUT_JSON)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
