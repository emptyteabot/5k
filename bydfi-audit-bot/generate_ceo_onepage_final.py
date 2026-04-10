from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak

ROOT = Path(r"C:\repo")
DB = ROOT / "data" / "audit_records.sqlite3"
OUT_REPO = ROOT / "data" / "reports" / "至4.2报告.pdf"
OUT_DESKTOP = Path(r"C:\Users\cyh\Desktop\至4.2报告.pdf")
OUT_DOWNLOAD = Path(r"C:\Users\cyh\Documents\Downloads\final_report.pdf")
OUT_MSG = Path(r"C:\Users\cyh\Desktop\kater_message.txt")

FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_NAME = "MicrosoftYaHei"
LOCAL_TZ = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class GroupRule:
    name: str
    patterns: tuple[str, ...]


GROUP_RULES = [
    GroupRule("血战到底", ("血战到底", "翻译协同")),
    GroupRule("BYDFi & Codeforce 全面合作群", ("Codeforce", "全面合作")),
    GroupRule("BYDFi·MoonX业务大群", ("MoonX业务大群", "MoonX")),
    GroupRule("产研周报发送群", ("产研周报", "周报发送群")),
    GroupRule("永续研发任务", ("永续研发任务", "研发任务话题群")),
    GroupRule("三部门效能优化需求", ("三部门效能优化需求", "效能优化需求")),
]


def register_font() -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH), subfontIndex=0))


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(esc(text), style)


def q_group(cur: sqlite3.Cursor, patterns: tuple[str, ...]) -> tuple[int, str | None]:
    where = " OR ".join(["source_title LIKE ? OR parsed_text LIKE ?" for _ in patterns])
    params: list[str] = []
    for p in patterns:
        params.extend([f"%{p}%", f"%{p}%"])
    cnt = cur.execute(f"SELECT COUNT(*) FROM audit_records WHERE {where}", params).fetchone()[0]
    latest = cur.execute(f"SELECT MAX(message_timestamp) FROM audit_records WHERE {where}", params).fetchone()[0]
    return cnt, latest


def collect_data() -> dict:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    meta = {
        "audit_records": cur.execute("SELECT COUNT(*) FROM audit_records").fetchone()[0],
        "source_documents": cur.execute("SELECT COUNT(*) FROM source_documents").fetchone()[0],
        "meeting_rows": cur.execute("SELECT COUNT(*) FROM dept_meeting_history").fetchone()[0],
        "latest_ts": cur.execute("SELECT MAX(message_timestamp) FROM audit_records").fetchone()[0],
    }

    groups = []
    for rule in GROUP_RULES:
        cnt, latest = q_group(cur, rule.patterns)
        if cnt >= 3:
            status = "可用"
        elif cnt > 0:
            status = "样本偏少"
        else:
            status = "缺口"
        groups.append({"name": rule.name, "count": cnt, "latest": latest or "暂无", "status": status})

    conn.close()
    return {"meta": meta, "groups": groups}


def make_styles() -> dict[str, ParagraphStyle]:
    s = getSampleStyleSheet()

    def mk(name: str, parent: str, **kwargs) -> ParagraphStyle:
        st = ParagraphStyle(name, parent=s[parent], fontName=FONT_NAME, **kwargs)
        st.wordWrap = "CJK"
        return st

    return {
        "title": mk("title", "Title", fontSize=20, leading=26, alignment=TA_CENTER, textColor=colors.HexColor("#0f172a")),
        "sub": mk("sub", "BodyText", fontSize=10, leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#475569")),
        "h2": mk("h2", "Heading2", fontSize=12.5, leading=17, textColor=colors.HexColor("#0f172a")),
        "body": mk("body", "BodyText", fontSize=9.6, leading=14.2, textColor=colors.HexColor("#1f2937")),
        "small": mk("small", "BodyText", fontSize=8.5, leading=12, textColor=colors.HexColor("#475569")),
    }


def add_table(story: list, rows: list[list[Paragraph]], widths: list[float], color: str) -> None:
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(color)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 5))


def build_pdf() -> Path:
    register_font()
    data = collect_data()
    styles = make_styles()
    now = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")

    OUT_REPO.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT_REPO),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="至4.2报告（CEO拍板版）",
    )

    story: list = []
    story.append(para("至4.2报告（CEO拍板版）", styles["title"]))
    story.append(para("一页主报告 + 一页证据附录；只写可拍板动作与已核事实", styles["sub"]))
    story.append(para(f"生成时间：{now} | 读者：CEO（Kater）", styles["sub"]))
    story.append(Spacer(1, 6))

    story.append(para("1) CEO 本周必须拍板（Top 7）", styles["h2"]))
    top7 = [
        ["动作", "Owner", "截止", "验收口径"],
        ["邀请码+奖励派发合并P1", "Rsii/Ella", "T+2天", "邀请码错误率<0.1%，奖励派发P95<10min"],
        ["Token验签合入+复测", "Kevin/Scanner", "T+3天", "代码合入+复测报告"],
        ["SEO Schema上线与索引验收", "Flash/Lorena", "T+3天", "commit+线上截图+GSC数据"],
        ["6个P0需求强制排期", "Miya/Jung", "T+2天", "每个P0具备owner/ETA/上线窗"],
        ["MoonX尾项清零", "Tony/Lori/Owen/Rsii", "T+7天", "提现/UI/规范/活动四项给验收结果"],
        ["翻译协同签核放行", "Stone/Christina/法务", "次日", "签核结果+放行结果+执行回执"],
        ["日报链路恢复门禁", "数据侧负责人", "T+2天", "incremental+backfill成功且run可追溯"],
    ]
    add_table(story, [[para(c, styles["small"]) for c in r] for r in top7], [47 * mm, 33 * mm, 21 * mm, 80 * mm], "#7c2d12")

    story.append(para("2) 三条出血线（管理判断）", styles["h2"]))
    for line in [
        "代理链路：邀请码与奖励派发是跨部门断链，连续影响BD信任，需按P1并单执行。",
        "SEO链路：指标暴露充分但闭环偏慢，必须由“口头进展”切换成“commit+验收值”。",
        "安全/风控链路：方案讨论多于代码闭环，需在验签、复测、上线节点做硬门禁。",
    ]:
        story.append(para(f"• {line}", styles["body"]))
    story.append(Spacer(1, 4))

    story.append(para("3) 不可下结论项（防误判）", styles["h2"]))
    for line in [
        "当前不能宣称“全自动日报链路已恢复”，因增量与回填尚无完整run追溯证明。",
        "三部门效能优化需求群当前库内命中为0，必须挂起判定，不得强下结论。",
        "产研周报发送群、MoonX业务大群样本偏少，趋势可参考，不可直接做绩效裁决。",
    ]:
        story.append(para(f"• {line}", styles["body"]))

    story.append(PageBreak())
    story.append(para("证据附录（群覆盖与数据边界）", styles["h2"]))
    meta = data["meta"]
    story.append(para(
        f"数据规模：audit_records={meta['audit_records']}，source_documents={meta['source_documents']}，dept_meeting_history={meta['meeting_rows']}，最新时间={meta['latest_ts']}",
        styles["small"],
    ))
    story.append(Spacer(1, 4))

    g_rows = [["群/来源", "命中记录", "最新时间", "状态"]]
    for g in data["groups"]:
        g_rows.append([g["name"], str(g["count"]), g["latest"], g["status"]])
    add_table(story, [[para(c, styles["small"]) for c in r] for r in g_rows], [52 * mm, 18 * mm, 62 * mm, 36 * mm], "#334155")

    story.append(para("本报告用途：用于CEO会前拍板，不作为全自动系统恢复证明。", styles["small"]))
    story.append(para("本报告原则：可追溯事实下判断；证据缺口项只挂起，不编造。", styles["small"]))

    doc.build(story)

    shutil.copyfile(OUT_REPO, OUT_DESKTOP)
    shutil.copyfile(OUT_REPO, OUT_DOWNLOAD)

    msg = """老板，至4.2拍板版已更新：
1) 首页仅保留Top7拍板动作（owner/截止/验收口径）。
2) 明确三条出血线与不可下结论项，避免误判。
3) 附页给出群覆盖缺口表，证据透明。
文件：C:\\Users\\cyh\\Desktop\\至4.2报告.pdf"""
    OUT_MSG.write_text(msg, encoding="utf-8")
    return OUT_DESKTOP


if __name__ == "__main__":
    print(build_pdf())
