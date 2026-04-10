from __future__ import annotations

import re
import shutil
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import generate_ceo_verified_report_pdf as base


ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "audit_records.sqlite3"
TMP_EXPORT_DIR = ROOT / "tmp_export_docs"

OUT_REPO = ROOT / "data" / "reports" / "至4.2报告.pdf"
OUT_DESKTOP = Path(r"C:\Users\cyh\Desktop\至4.2报告.pdf")
OUT_DESKTOP_ALT = Path(r"E:\UserData\cyh\Desktop\至4.2报告.pdf")
OUT_DOWNLOADS = Path(r"C:\Users\cyh\Documents\Downloads\final_report.pdf")
OUT_DESKTOP_ALT_FINAL = Path(r"E:\UserData\cyh\Desktop\final_report.pdf")
OUT_TEXT_ALT = Path(r"E:\UserData\cyh\Desktop\kater_message.txt")
OUT_TEXT = Path(r"C:\Users\cyh\Desktop\kater_message.txt")

LOCAL_TZ = timezone(timedelta(hours=8))
MEETING_CUTOFF_DATE = "2026-03-17"
MEETING_KEYWORDS = ("会议", "周会", "复盘", "日会", "月会", "招商会")
NOISE_TITLES = {"Jenny", "Kater", "Miles", "Claude分析机器人", "审计机器人"}


TOP_SUMMARY = [
    "先说结论：当前版本可作为‘执行推进简报’，不建议直接作为 CEO 终版拍板材料。原因不是没内容，而是证据覆盖不均衡、自动链路未恢复、部分群素材仍缺口明显。",
    "MoonX 仍是当前唯一产线最清晰的一条线。交付连续，主矛盾不在方向，而在提现联调、界面验收和活动排期这几个尾项能不能一周内清零。",
    "SEO 与韩国运营仍是假推进风险最高的两条线。一个是指标距离目标仍大，一个是活动中途改规则已经伤到市场信任；后续只能收带负责人、时间点和硬结果的验收汇报。",
    "CEX 与中心技术的问题不是没做事，而是版本推进、压测验收、事故反馈和数据回传没有被同一套门禁收口。动作继续增加，噪音只会继续变大。",
    "4月1日翻译协同线已经从“是否能做”进入“是否放行”。多语言历史缺口补齐链路已具备执行条件，当前卡点收敛到签核与白名单放行，不应再按方向性项目汇报。",
]

MOONX_TODO = [
    "Tony：盯死提现流程联调进度，当前剩余尾项最明确。",
    "Lori：盯 Web 预测界面验收和 App 尾项收口，避免设计完成但上线卡住。",
    "Owen：盯编码规范优化收尾，防止后续因为修 bug 影响节奏。",
    "Rsii：盯上线活动排期，当前宣发节奏仍慢于产品研发进度。",
]

NEXT_ACTIONS = [
    "SEO 与韩国运营后续只收结果型汇报，不再接受只有方向、没有验收值的过程汇报。",
    "CEX 版本项统一要求四个字段：负责人、时间点、验收标准、当前结果，缺一项都不算闭环。",
    "MoonX 本周只盯尾项清单，不再泛泛讨论整体状态。",
    "翻译协同线按签核结果与放行节点验收，不再接受“还在研究”“还在同步”式汇报。",
]

LATEST_SIGNALS = [
    "血战到底群在 4月1日 AI 翻译协同纪要中已经把多语言历史缺口（3500+）自动化补齐链路推进到可执行状态，团队已切入白名单放行模式。",
    "当前卡点不再是研发是否可做，而是 Stone、Christina 与法务签核能否按节点收口；只要签核不过，这条线就不能算闭环。",
    "执行节点已进入待确认状态，这条线现在需要的是签核结果与放行回执，不是再做一轮泛化汇报。",
    "群覆盖缺口仍需补齐：三部门效能优化需求群当前在库内命中为 0；产研周报发送群、MoonX业务大群命中样本偏少，本版结论应视为‘阶段可信’而非‘全量可信’。",
]


@dataclass(frozen=True)
class MeetingSource:
    date: str
    title: str
    note: str


MANUAL_REFERENCE_ROWS = [
    MeetingSource(
        "2026-04-01",
        "血战到底群｜4月1日 AI翻译协同纪要",
        "群通知触发的协同纪要；多语言历史缺口 3500+ 自动化补齐链路已具备执行条件；当前为白名单放行；待 Stone / Christina / 法务签核。",
    ),
]


@dataclass(frozen=True)
class GroupRule:
    name: str
    patterns: tuple[str, ...]


GROUP_RULES = [
    GroupRule("血战到底", ("血战到底", "翻译协同")),
    GroupRule("产研周报发送群", ("产研周报", "周报发送群")),
    GroupRule("BYDFi·MoonX业务大群", ("MoonX业务大群", "MoonX")),
    GroupRule("BYDFi & Codeforce 全面合作群", ("Codeforce", "全面合作")),
    GroupRule("三部门效能优化需求", ("三部门效能优化需求", "效能优化需求")),
    GroupRule("永续研发任务", ("永续研发任务", "研发任务话题群")),
]


def clean_text(text: str) -> str:
    text = re.sub(r"\[[^\]]+\]", "", text or "")
    replacements = {
        "owner": "负责人",
        "ETA": "时间点",
        "UI": "界面",
        "web": "Web",
        "redis": "Redis",
        "xxljob": "xxl-job",
        "App ": "App ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    for prefix in ("已验证进展：", "问题与风险：", "管理动作：", "风险信号：", "已验证交付：", "在途事项："):
        text = text.replace(prefix, "")
    text = text.replace("`", "")
    return " ".join(text.replace("\n", " ").split())


def pretty_title(title: str) -> str:
    mapping = {
        "SEO 与增长": "SEO 与增长",
        "韩区招商与运营": "韩国运营",
        "中心技术与现货支撑": "中心技术与 CEX",
        "客服": "客服",
        "MoonX 与社媒": "MoonX",
    }
    return mapping.get(title, title)


def pretty_source_title(title: str) -> str:
    replacements = {
        "CEO_现场抓取全量报告_20260330": "3月30日管理汇总底稿",
        "3.8.9版本--1.30": "CEX 版本计划",
        "【迭代】永续优化V1.1": "永续优化计划",
        "【需求】跟单包赔券": "跟单包赔券需求",
        "【需求】智能比例跟单": "智能比例跟单需求",
        "【需求】支持USDC合约": "USDC 合约需求",
        "【迭代】体验金V3.0": "体验金 V3.0",
        "【需求】Web合约网格": "Web 合约网格需求",
        "今日要求：每个会议记录都要形成结论并指出部门问题与建议": "4月2日最新管理要求",
        "组织建议：先搜集分类存储，再统一分析，形成技能化流程": "分析流程要求",
        "时效要求：日报需在开会前同步，保证每天自动更新": "日报时效要求",
        "质量要求：减少幻觉，重点信息需人工核对后同步": "质量与核对要求",
    }
    return replacements.get(title, title)


def contains_meeting_word(text: str) -> bool:
    return bool(text) and any(keyword in text for keyword in MEETING_KEYWORDS)


def parse_mmdd(text: str) -> tuple[int, int] | None:
    match = re.search(r"(\d{1,2})\.(\d{1,2})", text or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def business_date_from_text(text: str) -> str | None:
    mmdd = parse_mmdd(text)
    if not mmdd:
        return None
    month, day = mmdd
    return f"2026-{month:02d}-{day:02d}"


def strip_date_prefix(text: str) -> str:
    return re.sub(r"^\d{1,2}\.\d{1,2}\s*", "", clean_text(text or ""))


def normalize_title(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").replace("\u200b", "").replace("​", ""))


def normalize_note(text: str) -> str:
    return clean_text(text).replace("、会议详情：", "、").replace("会议详情：", "")


def canonical_meeting_key(text: str) -> str:
    normalized = normalize_title(strip_date_prefix(text))
    return re.sub(r"[()（）\[\]【】\-_:：,，.。/\\|]+", "", normalized)


def is_weak_meeting_title(text: str) -> bool:
    candidate = clean_text(strip_date_prefix(text))
    if not candidate:
        return True
    compact = canonical_meeting_key(candidate).lower()
    if len(compact) <= 4:
        return True
    weak_titles = {
        "\u4f1a\u8bae",
        "\u5468\u4f1a",
        "\u65e5\u4f1a",
        "\u6708\u4f1a",
        "\u4f1a\u8bae\u603b\u7ed3",
        "\u4f1a\u8bae\u7eaa\u8981",
        "\u4f1a\u8bae\u8bb0\u5f55",
        "\u5404\u90e8\u95e8okr\u8fdb\u5ea6\u590d\u76d8\u4f1a",
    }
    return compact in weak_titles


def allow_section_for_note(section_text: str, title_text: str) -> bool:
    section = clean_text(section_text)
    if not section:
        return False
    if "http://" in section or "https://" in section:
        return False
    if len(section) > 40:
        return False
    return canonical_meeting_key(section) != canonical_meeting_key(title_text)


def parse_iso_to_local(iso_text: str) -> datetime:
    fixed = iso_text.replace("Z", "+00:00")
    return datetime.fromisoformat(fixed).astimezone(LOCAL_TZ)


def format_cn_date(date_text: str) -> str:
    year, month, day = date_text.split("-")
    return f"{int(month)}月{int(day)}日"


def format_cn_dates(dates: list[str]) -> str:
    if not dates:
        return ""
    return "、".join(format_cn_date(date_text) for date_text in dates)


def choose_meeting_title(meeting_title: str, section_title: str) -> str:
    for candidate in (meeting_title, section_title):
        candidate = clean_text(candidate)
        if not candidate or candidate in NOISE_TITLES:
            continue
        if contains_meeting_word(candidate):
            return candidate
    return ""


def extract_heading_candidates(content: str, main_title: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for raw_line in content.splitlines():
        line = normalize_note(raw_line)
        if not line:
            continue
        if len(line) > 34:
            continue
        if not contains_meeting_word(line):
            continue
        if line in {"会议总结", "会议回顾"}:
            continue
        if clean_text(line) == clean_text(main_title):
            continue
        key = normalize_title(line)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(line)
        if len(candidates) >= 5:
            break
    return candidates


def collect_export_meeting_sources() -> list[MeetingSource]:
    sources: list[MeetingSource] = []
    if not TMP_EXPORT_DIR.exists():
        return sources

    for path in sorted(TMP_EXPORT_DIR.glob("*.txt")):
        raw_text = path.read_text(encoding="utf-8", errors="ignore")
        lines = [clean_text(line) for line in raw_text.splitlines() if clean_text(line)]
        if not lines:
            continue
        main_title = next((line for line in lines[:12] if contains_meeting_word(line)), "")
        if not contains_meeting_word(main_title):
            continue
        date_match = re.search(r"(\d{1,2})\.(\d{1,2})", main_title)
        if not date_match:
            date_match = re.search(r"(\d{1,2})\.(\d{1,2})", path.stem)
        if not date_match:
            continue

        month = int(date_match.group(1))
        day = int(date_match.group(2))
        date_text = f"2026-{month:02d}-{day:02d}"
        if date_text < MEETING_CUTOFF_DATE:
            continue

        headings = extract_heading_candidates(raw_text, main_title)
        note = "、".join(headings) if headings else "会议底稿导出文件"
        sources.append(MeetingSource(date_text, main_title, note))
    return sources


def collect_db_meeting_sources() -> list[MeetingSource]:
    if not DB.exists():
        return []

    groups: dict[tuple[str, str], dict[str, object]] = defaultdict(
        lambda: {"depts": set(), "sections": set(), "title": "", "dated_title": ""}
    )
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT dept, meeting_title, section_title, meeting_time
        FROM dept_meeting_history
        WHERE meeting_time >= ?
        ORDER BY meeting_time ASC, id ASC
        """,
        (f"{MEETING_CUTOFF_DATE}T00:00:00+00:00",),
    ).fetchall()
    conn.close()

    for dept, meeting_title, section_title, meeting_time in rows:
        title = choose_meeting_title(meeting_title, section_title)
        if not title:
            continue
        date_text = (
            business_date_from_text(meeting_title)
            or business_date_from_text(section_title)
            or parse_iso_to_local(meeting_time).date().isoformat()
        )
        if date_text < MEETING_CUTOFF_DATE:
            continue
        title_key = canonical_meeting_key(title)
        bucket = groups[(date_text, title_key)]
        if business_date_from_text(title):
            bucket["dated_title"] = title
        elif not bucket["title"]:
            bucket["title"] = title
        if dept and dept not in {"综合"}:
            bucket["depts"].add(clean_text(dept))
        if section_title:
            clean_section = clean_text(section_title)
            if (
                clean_section
                and clean_section not in NOISE_TITLES
                and allow_section_for_note(clean_section, title)
            ):
                bucket["sections"].add(clean_section)

    sources: list[MeetingSource] = []
    for (date_text, _title_key), bucket in sorted(groups.items()):
        display_title = bucket["dated_title"] or bucket["title"] or ""
        if not display_title:
            continue
        if is_weak_meeting_title(display_title) and not bucket["sections"]:
            continue
        parts: list[str] = []
        if bucket["depts"]:
            parts.append("部门：" + " / ".join(sorted(bucket["depts"])))
        if bucket["sections"]:
            parts.append("主题：" + "、".join(sorted(bucket["sections"])))
        note = "；".join(parts) if parts else "结构化会议归档"
        sources.append(MeetingSource(date_text, display_title, note))
    return sources


def collect_meeting_sources() -> list[MeetingSource]:
    merged: dict[tuple[str, str], MeetingSource] = {}

    def add_source(source: MeetingSource) -> None:
        key = (source.date, canonical_meeting_key(source.title))
        existing = merged.get(key)
        if existing is None:
            merged[key] = source
            return
        current_score = (1 if business_date_from_text(existing.title) else 0, len(existing.note), len(existing.title))
        new_score = (1 if business_date_from_text(source.title) else 0, len(source.note), len(source.title))
        if new_score > current_score:
            merged[key] = source

    for source in collect_export_meeting_sources():
        add_source(source)
    for source in collect_db_meeting_sources():
        add_source(source)

    return sorted(merged.values(), key=lambda item: (item.date, item.title))


def collect_reference_rows() -> list[MeetingSource]:
    rows: list[MeetingSource] = list(MANUAL_REFERENCE_ROWS)
    meeting_keys = {(item.date, canonical_meeting_key(item.title)) for item in collect_meeting_sources()}
    for item in base.EVIDENCE_INDEX:
        raw_title = clean_text(item.title)
        if item.title in {
            "CEO_现场抓取全量报告_20260330",
            "组织建议：先搜集分类存储，再统一分析，形成技能化流程",
        }:
            continue
        if contains_meeting_word(raw_title) and (item.date, canonical_meeting_key(raw_title)) in meeting_keys:
            continue
        rows.append(MeetingSource(item.date, pretty_source_title(raw_title), clean_text(item.note)))
    return rows


def make_styles() -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()

    def build(name: str, parent: str, **kwargs) -> ParagraphStyle:
        style = ParagraphStyle(name, parent=styles[parent], fontName=base.FONT_NAME, **kwargs)
        style.wordWrap = "CJK"
        return style

    return {
        "title": build("title", "Title", fontSize=20, leading=26, alignment=TA_CENTER, textColor=colors.HexColor("#0f172a")),
        "subtitle": build("subtitle", "BodyText", fontSize=10, leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#475569")),
        "section": build("section", "Heading2", fontSize=12.8, leading=17, textColor=colors.HexColor("#0f172a")),
        "subsection": build("subsection", "Heading3", fontSize=11.1, leading=15, textColor=colors.HexColor("#0f766e")),
        "body": build("body", "BodyText", fontSize=9.35, leading=14, textColor=colors.HexColor("#1f2937")),
        "small": build("small", "BodyText", fontSize=8.5, leading=12, textColor=colors.HexColor("#475569")),
    }


def on_page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(base.FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(doc.leftMargin, 8 * mm, "至4.2报告")
    canvas.drawRightString(A4[0] - doc.rightMargin, 8 * mm, f"第{canvas.getPageNumber()}页")
    canvas.restoreState()


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(base.escape(text), style)


def bullet(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(f"&bull; {base.escape(text)}", style)


def add_heading(story: list, text: str, style: ParagraphStyle, gap: float = 4) -> None:
    story.append(para(text, style))
    story.append(Spacer(1, gap))


def add_bullets(story: list, items: list[str], style: ParagraphStyle, gap: float = 1.5) -> None:
    for item in items:
        story.append(bullet(item, style))
        story.append(Spacer(1, gap))


def add_table(story: list, rows: list[list[object]], widths: list[float], header_color: str) -> None:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), base.FONT_NAME),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 5))


def coverage_rows(styles: dict[str, ParagraphStyle]) -> list[list[object]]:
    rows: list[list[object]] = [
        [para("本次内容", styles["body"]), para("处理方式", styles["body"])]
    ]
    items = [
        ("会议记录分析", "逐条形成结论，结合部门历史看进展、问题和建议。"),
        ("周报系统", "同时看部门现状和个人执行，不只停留在部门层面。"),
        ("CEX 进度", "结合版本计划、需求安排和个人周报交叉判断推进情况与风险点。"),
        ("MoonX", "单独拆出专题，看产品、设计、后端和社媒四条线。"),
        ("日报时效", "保留为明确要求，后续按固定节奏持续补齐。"),
        ("翻译专项", "纳入 4 月 1 日协同纪要，只对执行条件、签核门禁和放行节点下结论。"),
        ("覆盖缺口", "三部门效能优化需求群在当前库命中为 0；产研周报发送群与MoonX业务大群样本偏少，需继续补证。"),
    ]
    for left, right in items:
        rows.append([para(left, styles["body"]), para(right, styles["body"])])
    return rows


def source_rows(styles: dict[str, ParagraphStyle]) -> list[list[object]]:
    rows: list[list[object]] = [[para("日期", styles["body"]), para("材料", styles["body"]), para("用途", styles["body"])]]
    all_items = collect_meeting_sources() + collect_reference_rows()
    all_items.sort(key=lambda item: (item.date, item.title), reverse=True)
    for item in all_items:
        rows.append([para(item.date, styles["small"]), para(item.title, styles["small"]), para(item.note, styles["small"])])
    return rows


def group_coverage_rows(styles: dict[str, ParagraphStyle]) -> list[list[object]]:
    targets = [
        "血战到底",
        "产研周报发送群",
        "BYDFi·MoonX业务大群",
        "BYDFi & Codeforce 全面合作群",
        "三部门效能优化需求",
        "永续研发任务",
    ]
    rows: list[list[object]] = [[para("群/来源", styles["body"]), para("命中记录", styles["body"]), para("最新时间", styles["body"]), para("判定", styles["body"])]]
    if not DB.exists():
        for t in targets:
            rows.append([para(t, styles["small"]), para("0", styles["small"]), para("暂无", styles["small"]), para("需补证", styles["small"])])
        return rows

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    for t in targets:
        cnt = cur.execute(
            "SELECT COUNT(*) FROM audit_records WHERE source_title LIKE ? OR parsed_text LIKE ?",
            (f"%{t}%", f"%{t}%"),
        ).fetchone()[0]
        latest = cur.execute(
            "SELECT MAX(message_timestamp) FROM audit_records WHERE source_title LIKE ? OR parsed_text LIKE ?",
            (f"%{t}%", f"%{t}%"),
        ).fetchone()[0]
        verdict = "可用" if cnt >= 3 else ("样本偏少" if cnt > 0 else "缺口")
        rows.append([
            para(t, styles["small"]),
            para(str(cnt), styles["small"]),
            para(clean_text(latest or "暂无"), styles["small"]),
            para(verdict, styles["small"]),
        ])
    conn.close()
    return rows


def ceo_action_rows(styles: dict[str, ParagraphStyle]) -> list[list[object]]:
    rows: list[list[object]] = [[para("动作", styles["body"]), para("Owner", styles["body"]), para("截止", styles["body"]), para("验收口径", styles["body"])]]
    actions = [
        ("邀请码+奖励派发合并P1", "Rsii / Ella", "T+2天", "邀请码错误率 <0.1%，奖励派发 P95 <10min"),
        ("Token验签代码合入+复测", "Kevin / Scanner", "T+3天", "代码合入 + 复测报告"),
        ("SEO Schema上线与索引验收", "Flash / Lorena", "T+3天", "commit + 线上截图 + GSC 数据"),
        ("6个P0需求强制排期", "Miya / Jung", "T+2天", "每个P0必须有 owner / ETA / 上线窗"),
        ("MoonX尾项清零", "Tony / Lori / Owen / Rsii", "T+7天", "提现/UI/规范/活动四项全部给出验收结果"),
        ("翻译协同线签核放行", "Stone / Christina / 法务", "次日", "签核结果 + 放行结果 + 执行回执"),
        ("日报链路恢复门禁", "数据侧负责人", "T+2天", "增量成功 + backfill成功 + run lineage 可追溯"),
    ]
    for a in actions:
        rows.append([para(a[0], styles["small"]), para(a[1], styles["small"]), para(a[2], styles["small"]), para(a[3], styles["small"])])
    return rows


def build_meeting_scope_line() -> str:
    meeting_sources = collect_meeting_sources()
    unique_dates = sorted({item.date for item in meeting_sources})
    if not unique_dates:
        return "本版附件按已归档底稿自动汇总；血战到底群4月1日协同纪要与4月2日最新管理要求已单列纳入依据材料。"
    return f"本版附件按已归档底稿自动汇总，会议底稿覆盖 {format_cn_dates(unique_dates)}；血战到底群4月1日协同纪要与4月2日最新管理要求已单列纳入依据材料。"


def build_story(now_text: str) -> list:
    styles = make_styles()
    story: list = []

    story.append(para("BYDFi 截至4月2日管理简报（V3终版）", styles["title"]))
    story.append(para("本版定位：CEO 可读可拍板；明确区分已确认事实与不可确认项，避免误判。", styles["subtitle"]))
    story.append(para(f"整理时间：{now_text} | 材料范围：会议纪要、部门周报、个人周报、版本计划、血战到底群4月1日协同纪要、4月2日最新管理要求", styles["subtitle"]))
    story.append(Spacer(1, 6))

    add_heading(story, "A. CEO本周拍板事项（只看这个）", styles["section"])
    add_table(story, ceo_action_rows(styles), [44 * mm, 34 * mm, 22 * mm, 82 * mm], "#7c2d12")

    add_heading(story, "B. 已确认事实", styles["section"])
    add_bullets(story, TOP_SUMMARY, styles["body"], gap=1.8)

    add_heading(story, "C. 不可确认项（防误判）", styles["section"])
    unknowns = [
        "自动增量/回填链路当前未恢复到可审计状态，不能宣称“日报系统已稳定自动化”。",
        "三部门效能优化需求群当前库内命中为 0；该条线只能挂起，不应下结论。",
        "产研周报发送群、MoonX业务大群样本偏少，趋势判断仅可作参考，不可作最终绩效结论。",
        "未看到完整 run lineage 前，不做“全链路闭环已完成”判断。",
    ]
    add_bullets(story, unknowns, styles["body"], gap=1.8)

    add_heading(story, "D. 群覆盖缺口表", styles["section"])
    add_table(story, group_coverage_rows(styles), [48 * mm, 18 * mm, 62 * mm, 42 * mm], "#334155")

    add_heading(story, "截至4.2新增信号", styles["section"])
    add_bullets(story, LATEST_SIGNALS, styles["body"], gap=1.8)

    add_heading(story, "本次覆盖范围", styles["section"])
    story.append(para("以下内容只保留本次需要回答的核心问题，不写系统日志，不写内部过程。", styles["small"]))
    story.append(Spacer(1, 3))
    add_table(story, coverage_rows(styles), [40 * mm, 140 * mm], "#0f766e")
    story.append(para(build_meeting_scope_line(), styles["small"]))
    story.append(Spacer(1, 4))

    add_heading(story, "会议与部门判断", styles["section"])
    for sec in base.DEPARTMENT_SECTIONS:
        title = pretty_title(sec["title"])
        if title == "MoonX":
            continue
        progress = clean_text(sec["progress"])
        issues = clean_text(sec["issues"])
        actions = clean_text(sec["actions"])
        if title == "客服":
            issues = "当前已确认的是报表字段修复和补发动作，下一步重点不是继续扩写结论，而是把服务效率、用户反馈和补发结果形成清晰回传。"
            actions = "短期先围绕字段修复、补发对象、下周验收项做闭环，不再扩成大而全的客服评分。"
        block = [
            para(title, styles["subsection"]),
            bullet(f"现状：{progress}", styles["body"]),
            bullet(f"风险：{issues}", styles["body"]),
            bullet(f"建议：{actions}", styles["body"]),
            Spacer(1, 3),
        ]
        story.append(KeepTogether(block))

    add_heading(story, "MoonX 尾项清单", styles["section"])
    add_bullets(story, MOONX_TODO, styles["body"], gap=1.8)

    add_heading(story, "CEX 进度、风险与建议", styles["section"])
    cex_items = [
        "版本计划已经明确显示，合约跟单、合约网格和安全中心都有顺延事项。这些延期不是推断，是当前排期里已经写明的管理信号。",
        "CEX 的需求分工相对清楚，前端、后端、后台和测试责任已经明确，但真正应该盯的是上线后的验收结果，而不是只看分工表。",
        "当前更容易确认的闭环，集中在 MoonX 和局部 CEX 界面优化项；大型 CEX 版本项仍需要把上线结果、压测结果和回归情况统一收口。",
        "后续版本汇报统一固定为四个字段：负责人、时间点、验收标准、当前结果。缺任何一项，都不应写成进展正常。",
    ]
    for item in cex_items:
        story.append(bullet(item, styles["body"]))
        story.append(Spacer(1, 1.8))
    story.append(Spacer(1, 3))

    add_heading(story, "MoonX 专项判断", styles["section"])
    for sec in base.DEPARTMENT_SECTIONS:
        if pretty_title(sec["title"]) == "MoonX":
            add_bullets(
                story,
                [
                    f"当前状态：{clean_text(sec['progress'])}",
                    f"当前风险：{clean_text(sec['issues'])}",
                    f"建议动作：{clean_text(sec['actions'])}",
                ],
                styles["body"],
                gap=1.8,
            )
            break

    add_heading(story, "本周推进要求", styles["section"])
    add_bullets(story, NEXT_ACTIONS, styles["body"], gap=1.8)
    add_bullets(story, ["翻译专项本周只盯签核、放行和执行节点，不再把已具备执行条件的事项写成方向性讨论。"], styles["body"], gap=1.8)

    add_heading(story, "依据材料", styles["section"])
    story.append(para("以下保留截至4月2日前已归档的会议底稿、版本资料、个人周报与血战到底群最新协同纪要，按时间倒序汇总，供直接追溯。", styles["small"]))
    story.append(Spacer(1, 4))
    add_table(story, source_rows(styles), [24 * mm, 56 * mm, 100 * mm], "#1d4ed8")

    return story


def build_body_text() -> str:
    lines = [
        "老板，以上为截至4月2日的核心卡点提纯与干预建议。",
        "",
        "1. MoonX 是当前唯一推进最清晰的业务线。多名核心成员已有连续交付，当前卡点集中在提现流程、界面验收和活动排期，建议本周只盯最后一公里的验收清单。",
        "2. SEO 与韩国运营是假推进风险最高的两条线。SEO 核心指标仍明显低于目标，韩国区活动中途改规则已经造成口碑损耗，后续只接收带负责人、时间点和硬数据的结果汇报。",
        "3. CEX 与中心技术有动作，但闭环不足。版本推进、压测验收、事故反馈和数据回传需要放进同一张管理表，否则过程越多，噪音越大。",
        "4. 血战到底群里的翻译协同线在 4 月 1 日已经进入待签核放行状态。多语言历史缺口补齐链路已具备执行条件，当前只需要盯签核结果与放行回执。",
        "",
        "各部门及个人的详细交付底稿见附件。",
    ]
    return "\n".join(lines)


def build_pdf() -> Path:
    base.register_font()
    OUT_REPO.parent.mkdir(parents=True, exist_ok=True)
    now_text = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")

    doc = SimpleDocTemplate(
        str(OUT_REPO),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="BYDFi 截至4月2日管理简报",
        author="OpenAI Codex",
    )
    story = build_story(now_text)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    body_text = build_body_text()
    OUT_TEXT.write_text(body_text, encoding="utf-8")
    if OUT_TEXT_ALT.parent.exists():
        OUT_TEXT_ALT.write_text(body_text, encoding="utf-8")

    shutil.copyfile(OUT_REPO, OUT_DESKTOP)
    shutil.copyfile(OUT_REPO, OUT_DOWNLOADS)
    if OUT_DESKTOP_ALT.parent.exists():
        shutil.copyfile(OUT_REPO, OUT_DESKTOP_ALT)
    if OUT_DESKTOP_ALT_FINAL.parent.exists():
        shutil.copyfile(OUT_REPO, OUT_DESKTOP_ALT_FINAL)
    return OUT_DESKTOP_ALT if OUT_DESKTOP_ALT.parent.exists() else OUT_DESKTOP


if __name__ == "__main__":
    print(str(build_pdf()))
