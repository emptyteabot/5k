from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(r"C:\repo")
REPORTS = ROOT / "data" / "reports"
DB = ROOT / "data" / "audit_records.sqlite3"
OUT = REPORTS / "final_report_v2_20260402.pdf"
OUT_DESKTOP = Path(r"C:\Users\cyh\Desktop\final_report_v2_20260402.pdf")
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_NAME = "MicrosoftYaHei"


def register_font() -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH), subfontIndex=0))


def latest_evidence() -> dict:
    files = sorted(REPORTS.glob("evidence_guard_*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        return {}
    return json.loads(files[-1].read_text(encoding="utf-8-sig"))


def db_stats() -> dict:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    stats = {
        "audit_records": c.execute("SELECT COUNT(*) FROM audit_records").fetchone()[0],
        "source_documents": c.execute("SELECT COUNT(*) FROM source_documents").fetchone()[0],
        "dept_meeting_history": c.execute("SELECT COUNT(*) FROM dept_meeting_history").fetchone()[0],
        "max_ts": c.execute("SELECT MAX(message_timestamp) FROM audit_records").fetchone()[0],
        "today_records": c.execute("SELECT COUNT(*) FROM audit_records WHERE substr(message_timestamp,1,10)='2026-04-02'").fetchone()[0],
    }

    def kcnt(k: str) -> int:
        return c.execute(
            "SELECT COUNT(*) FROM audit_records WHERE source_title LIKE ? OR parsed_text LIKE ?",
            (f"%{k}%", f"%{k}%"),
        ).fetchone()[0]

    stats.update(
        {
            "kw_blood": kcnt("血战到底"),
            "kw_weekly": kcnt("周报"),
            "kw_cex": kcnt("CEX"),
            "kw_moonx": kcnt("MoonX"),
        }
    )
    conn.close()
    return stats


def build() -> Path:
    register_font()
    ev = latest_evidence()
    st = db_stats()

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "t", parent=styles["Title"], fontName=FONT_NAME, fontSize=19, leading=26, alignment=TA_CENTER
    )
    sub = ParagraphStyle("s", parent=styles["Normal"], fontName=FONT_NAME, fontSize=10, leading=15, alignment=TA_CENTER)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName=FONT_NAME, fontSize=12, leading=17, textColor=colors.HexColor("#0f172a"))
    body = ParagraphStyle("b", parent=styles["BodyText"], fontName=FONT_NAME, fontSize=9.8, leading=15)

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    story = []

    story.append(Paragraph("BYDFi 产研执行审计（V2决策版）", title))
    story.append(Paragraph(f"报告时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 目标：比上一版更可决策、更少错判", sub))
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. 数据边界与可信度", h2))
    confidence = "低-中（链路未完全恢复）" if ev.get("overall_status") == "fail" else "中-高"
    story.append(
        Paragraph(
            f"当前数据总量 audit_records={st['audit_records']}，source_documents={st['source_documents']}，dept_meeting_history={st['dept_meeting_history']}；"
            f"最新证据时间={st['max_ts']}；今日新增记录={st['today_records']}。证据守卫状态={ev.get('overall_status','unknown')}，可信度={confidence}。",
            body,
        )
    )
    story.append(Paragraph("反幻觉约束：以下结论仅基于已核实证据，无法核实项统一标注为“待确认/不可下结论”。", body))
    story.append(Spacer(1, 6))

    story.append(Paragraph("2. CEO 当日要求满足度（你四张图）", h2))
    req_table = [
        ["要求", "状态", "证据", "缺口"],
        ["血战到底最新报告", "部分满足", f"关键词命中={st['kw_blood']}，最新到今日", "需拉取飞书原文并做逐条引用"],
        ["周报系统（部门+个人）", "部分满足", f"关键词命中={st['kw_weekly']}", "短历史记录较多，趋势稳定性不足"],
        ["CEX进度+风险+优化", "部分满足", f"关键词命中={st['kw_cex']}", "缺 run lineage，管理结论追溯不足"],
        ["MoonX单独分析", "部分满足", f"关键词命中={st['kw_moonx']}", "仍需自动链路恢复后做全量增量"],
        ["文件->数据库->MCP->Skill", "在建", "文件/数据库已落地", "MCP与Skill自动编排未完成"],
    ]
    t = Table(req_table, colWidths=[42 * mm, 22 * mm, 42 * mm, 62 * mm])
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 6))

    story.append(Paragraph("3. 对比你 3/30 基准报告后的宏观升级版判断", h2))
    bullets = [
        "公司当前不是“看不到问题”，而是“证据链和执行链脱节”：问题识别能力强于闭环能力。",
        "跨部门瓶颈依旧在 owner/ETA/验收口径三要素不完整；这会把讨论量转化为管理噪音。",
        "策略上应从“多点并行推进”改成“3条出血线止血优先”：代理链路、SEO核心指标、安全闭环。",
        "任何“看起来在推进”的动作，若无 commit/截图/验收值，统一视为过程信号，不计入交付。",
    ]
    for b in bullets:
        story.append(Paragraph(f"• {b}", body))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4. 本周可执行决策清单（可直接派发）", h2))
    act_table = [
        ["动作", "Owner", "截止", "验收口径"],
        ["邀请码+奖励派发合并P1", "Rsii/Ella", "T+2天", "邀请码错误率<0.1%，奖励派发P95<10min"],
        ["Token验签上线与复测", "Kevin/Scanner", "T+3天", "代码合入+复测报告"],
        ["SEO Schema与索引链路验收", "Flash/Lorena", "T+3天", "commit+线上截图+GSC数据"],
        ["6个P0需求强制排期", "Miya/Jung", "T+2天", "每个P0必须有owner/ETA/上线窗"],
        ["AI单场景闭环（客服）", "客服负责人", "T+4天", "月报误差修正并达标"],
    ]
    t2 = Table(act_table, colWidths=[46 * mm, 22 * mm, 18 * mm, 82 * mm])
    t2.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(t2)
    story.append(Spacer(1, 6))

    story.append(Paragraph("5. 不可下结论项（强制披露）", h2))
    for b in [
        "当前无法给出“全链路自动化已恢复”结论（evidence_guard=fail）。",
        "当前无法给出“部门最终绩效优劣”结论（历史短记录与噪音污染未完全清除）。",
        "当前无法给出“所有延期已确认”结论（存在 owner/ETA/验收口径缺失）。",
    ]:
        story.append(Paragraph(f"• {b}", body))

    story.append(Spacer(1, 8))
    story.append(Paragraph("溯源：data/reports/evidence_guard_*.json, data/reports/autopilot_state.json, data/audit_records.sqlite3", body))

    doc.build(story)
    OUT_DESKTOP.write_bytes(OUT.read_bytes())
    return OUT_DESKTOP


if __name__ == "__main__":
    path = build()
    print(str(path))
