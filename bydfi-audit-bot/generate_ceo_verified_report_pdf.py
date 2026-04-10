from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "audit_records.sqlite3"
REPORT_DIR = ROOT / "data" / "reports"
ARCHIVE_PDF = REPORT_DIR / "final_report_verified_20260402.pdf"
OUTPUT_PDF = Path(r"C:\Users\cyh\Documents\Downloads\final_report.pdf")
OUTPUT_PDF_DESKTOP = Path(r"C:\Users\cyh\Desktop\final_report_verified_20260402.pdf")
OUTPUT_MD = REPORT_DIR / "final_report_verified_20260402.md"
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_NAME = "MicrosoftYaHei"


@dataclass(frozen=True)
class Evidence:
    ref: str
    title: str
    date: str
    note: str


EVIDENCE_INDEX = [
    Evidence("SD-2256", "CEO_现场抓取全量报告_20260330", "2026-03-30", "旧版 CEO 全量报告 markdown 源"),
    Evidence("SD-2365", "3.25 会议总结", "2026-03-25", "韩国招商周会、现货+用户会议、前端日会"),
    Evidence("SD-259", "3.26 会议总结", "2026-03-26", "SEO 项目周会、客服单周会、社媒周会、SEO+增长会议"),
    Evidence("SD-2366", "3.27 会议总结", "2026-03-27", "中心会议、单周组长汇报、风控审核双周会、设计周会、产品部门周会"),
    Evidence("AR-255", "3.8.9版本--1.30", "2026-03-31", "CEX 版本计划文档，含顺延节点与上线状态"),
    Evidence("AR-735", "【迭代】永续优化V1.1", "2026-03-25", "永续优化版本文档，含 3.20 / 4.20 顺延信息"),
    Evidence("AR-755", "【需求】跟单包赔券", "2026-03-25", "CEX 需求文档，含 owner 分配"),
    Evidence("AR-786", "【需求】智能比例跟单", "2026-03-25", "CEX 需求文档，含 owner 分配"),
    Evidence("AR-801", "【需求】支持USDC合约", "2026-03-25", "CEX 需求文档，含 owner 分配"),
    Evidence("AR-803", "【迭代】体验金V3.0", "2026-03-25", "CEX 迭代文档，含 owner 分配"),
    Evidence("AR-816", "【需求】web合约网格", "2026-03-25", "CEX 需求文档，含 owner 分配"),
    Evidence("AR-233", "Night 周报", "2026-03-22", "MoonX / Polymarket 后端周报"),
    Evidence("AR-3287", "Tony 周报", "2026-03-27", "CEX / MoonX App / 预测市场周报"),
    Evidence("AR-3288", "Liam 周报", "2026-03-27", "MoonX 后端周报"),
    Evidence("AR-3289", "Lori 周报", "2026-03-28", "MoonX UI 周报"),
    Evidence("AR-3290", "Owen 周报", "2026-03-30", "MoonX / 预测市场周报"),
    Evidence("AR-3294", "Rsii 周报", "2026-03-31", "MoonX 社媒周报"),
    Evidence("AR-3360", "Crads 周报", "2026-03-27", "技术支撑周报"),
    Evidence("AR-7932", "今日要求：每个会议记录都要形成结论并指出部门问题与建议", "2026-04-02", "CEO 最新硬要求"),
    Evidence("AR-7933", "组织建议：先搜集分类存储，再统一分析，形成技能化流程", "2026-04-02", "文件 -> 数据库 -> MCP -> Skill 方向"),
    Evidence("AR-7934", "时效要求：日报需在开会前同步，保证每天自动更新", "2026-04-02", "日报时效要求"),
    Evidence("AR-7935", "质量要求：减少幻觉，重点信息需人工核对后同步", "2026-04-02", "反幻觉与翻译流程要求"),
]


REQUIREMENT_ROWS = [
    (
        "每个会议记录形成结论",
        "本版只分析已核到原始材料的 3.25 / 3.26 / 3.27 会议总结，并逐部门写结论、问题、建议。",
        "已覆盖",
        "AR-7932, SD-2365, SD-259, SD-2366",
    ),
    (
        "周报要看部门和个人",
        "本版加入 6 份原始个人周报，单列个人执行信号，不使用机器人二次评价。",
        "已覆盖",
        "AR-7932, AR-3287, AR-3288, AR-3289, AR-3290, AR-3294, AR-3360",
    ),
    (
        "CEX 进度要结合版本计划",
        "本版将 CEX 原始版本文档与本周个人周报对表，只对文档中明确顺延或待开发项作延期判断。",
        "已覆盖",
        "AR-255, AR-735, AR-755, AR-786, AR-801, AR-803, AR-816",
    ),
    (
        "MoonX 可单独分析",
        "本版单列 MoonX / 预测市场专题，覆盖前端、后端、UI、社媒四类原始周报。",
        "已覆盖",
        "AR-7932, AR-233, AR-3287, AR-3288, AR-3289, AR-3290, AR-3294",
    ),
    (
        "日报要在开会前给到",
        "已识别为系统要求，但当前库内仅有 4 月 2 日指令，不足以证明日报自动链路已经恢复。",
        "部分覆盖",
        "AR-7934, data/reports/autopilot_state.json",
    ),
    (
        "减少幻觉、重点信息人工核对",
        "本版显式排除 Claude / 审计机器人二次分析记录，不写无来源 owner / ETA / 绩效判断。",
        "已覆盖",
        "AR-7935, HALLUCINATION_REMEDIATION_20260402.md",
    ),
    (
        "翻译任务先抽功能词再做文章翻译",
        "当前文件夹中未找到足够翻译原文样本，因此只保留流程要求，不输出翻译质量结论。",
        "部分覆盖",
        "AR-7935",
    ),
]


EXEC_SUMMARY = [
    "本版报告不是旧稿的润色版，而是一次有边界的重建。旧版 `final_report.pdf` 可追溯到 2026-03-30 的现场抓取全量报告与本地 HTML 导出，但其中大量管理判断在当前库内缺少逐条可回溯的一手证据。本版只保留当前仍能在本地文件和数据库里核到的事实。[SD-2256]",
    "当前最强的已验证执行线来自 MoonX / 预测市场周报，而不是大而全的公司总览。Tony、Owen、Liam、Lori、Rsii 在 2026-03-27 到 2026-03-31 之间提供了连续、可核验的产出记录，但仍有提现流程、UI 验收、编码规范、活动上线节奏等未闭环项。[AR-3287, AR-3288, AR-3289, AR-3290, AR-3294]",
    "SEO、韩区运营、中心技术三条线都存在明确事实支撑的风险点：SEO 指标距离目标仍大，韩区活动规则变更已引发信任损耗，中心技术侧仍有 P0 / P1 问题与压测验收未通过项。问题不是看不见，而是跨部门闭环速度仍然慢于问题暴露速度。[SD-2365, SD-259, SD-2366]",
]


DATA_BOUNDARY = [
    "本报告生成时间为本地当前时间，基于 `C:\\repo\\data\\audit_records.sqlite3` 直接读取并人工筛选一手材料。",
    "纳入范围：2026-03-22 到 2026-03-31 的原始个人周报 / 群消息；2026-03-25、2026-03-26、2026-03-27 的原始会议总结；2026-04-02 补入库的 CEO 最新要求；CEX 版本 / 需求文档原文。",
    "排除范围：Claude 分析机器人、审计机器人、群汇总分析等二次 AI 叙述；任何当前无法对应到原始文档的 owner、ETA、绩效结论。",
    "新鲜度边界：最新的 CEO 指令已经到 2026-04-02，但当前库内可直接引用的业务事实主要集中在 2026-03-22 到 2026-03-31；因此本版能回答“老板现在要什么”，但不能伪装成“自动日报链路已恢复”。",
]


DEPARTMENT_SECTIONS = [
    {
        "title": "SEO 与增长",
        "progress": "已验证进展：3.26 会议确认，主站索引率与帮助中心索引率已纳入监控，3.9.3 版本技术问题已解决且源数据调整本周完成 40%，LCP 二期、schema 字段、sitemap 优化列为本周落地项；内容工厂按 MVP 与模块覆盖两阶段推进，4 个 PSEO 模块人工优化计划本周上线。[SD-259]",
        "issues": "问题与风险：整站索引率仅 38.5%，目标 55%；PSEO 页面约 13 万，但索引率仅 29%、点击极低；新内容 72 小时索引率完成度仅 5%；questions 模块无效曝光偏高，说明现阶段仍是“指标暴露得很清楚，但工程闭环和内容价值提升不够快”。[SD-259]",
        "actions": "管理动作：只盯两条硬链路。第一，索引链路必须拆成负责人、截止时间、验收口径；第二，页面生产链路必须把“本周上线”转换成可验收页面清单。任何只写方向不写上线动作的汇报，都应降级处理。[SD-259]",
    },
    {
        "title": "韩区招商与运营",
        "progress": "已验证进展：3.25 韩国招商周会显示，本周新增 2 家大型代理进入洽谈；异常对敲用户已批量处理，代理侧配合扣除异常佣金后暂无负面舆情；新代理在接入 Coinone 后对 BYDFi 有兴趣。[SD-2365]",
        "issues": "问题与风险：活动方案临时改动后，部分代理认为平台失信，出现用户充值后立即转出、注册量下滑；前期标记价格异常与持仓收益率 PNL 不更新引发韩国、越南、俄罗斯地区投诉，平台稳定性被质疑。活动监控当前仍缺实时播报与止损指标，这不是执行瑕疵，是信任损耗风险。[SD-2365]",
        "actions": "管理动作：后续活动必须先有日级实时监控、止损线和变更沟通预案，再上线。韩区活动类需求如果继续允许中途改规则，市场口碑会继续吃损，增长数据再漂亮也不稳。[SD-2365]",
    },
    {
        "title": "中心技术与现货支撑",
        "progress": "已验证进展：3.27 中心会议确认，中心业务 28 个版本需求已完成 15 个（均属于 3.9.3 版本），10 个业务监控优化已上线并使平均耗时下降 50%；现货业务 P0 / P1 各 4 个需求按期上线且无线上问题；AI 发布处于测试阶段，PR 自动评审与定期报告已完成部分开发。[SD-2366]",
        "issues": "问题与风险：同一场会议也记录了 1 个严重事故、共 5 个问题，其中含 2 个 P1 和 1 个 P0；永续下单 4K 压测验收未通过，Open API 下单 3K 未验收，8 倍流量冲击下仍有积压；部分线如活动派奖和风控提币仍无数据反馈。当前中心技术的问题不是“没做事”，而是验收门槛和反馈闭环没有跟上推进速度。[SD-2366]",
        "actions": "管理动作：把压测验收、问题反馈、数据回传列成单独门禁。没有验收结果的优化不算闭环，没有反馈数据的功能不算上线价值成立。[SD-2366]",
    },
    {
        "title": "客服",
        "progress": "已验证进展：3.26 客服单周会明确，原报税报表缺少 PNL 盈亏字段的问题已由 Miya 上线修复，客服端已可正常导出；同时会议明确要统计反馈不满的用户，重发含 PNL 字段的资料。[SD-259]",
        "issues": "问题与风险：当前结构化层对 3.26 客服会议的后续段落保留不完整，因此本版只能确认“报表字段问题已修复”这一点，不能继续脑补 VIP 分流、AI 话术或培训质量结论。这本身说明客服线的数据抽取质量仍不足以支撑激进判断。[SD-259]",
        "actions": "管理动作：客服线短期内先别追大而全评分，先把本周已修事项、待补发对象、下周要验收的字段类问题列清。数据不完整时硬下判断，只会继续制造垃圾报告。[SD-259]",
    },
    {
        "title": "MoonX 与社媒",
        "progress": "已验证进展：原始周报显示，MoonX 线在 3.23 到 3.31 之间有连续交付。后端侧，Owen 完成地址标签、预测市场固定分区、买卖授权、赎回接口流程优化、ES 查询优化等多项任务，Liam 完成稳定币兑换数据库、后台接口、redis 缓存、市价与限价交易 5 项后端工作；前端 / UI 侧，Tony 完成资产页 UI 与数据接口接入、充值流程、MoonX Bot 标签展示，Lori 完成多项 web 预测市场交互设计；社媒侧，Rsii 本周发 29 条推文，KOL 招募浏览量 1.6W，联合活动有效增粉 2945。[AR-3287, AR-3288, AR-3289, AR-3290, AR-3294]",
        "issues": "问题与风险：本线的风险集中在未完成尾项而非整体失速。Tony 的提现流程仍为 80%，Lori 的 web 链上预测 UI 验收为 50%、App 设计为 90%，Owen 的编码规范优化仍在 50%；Rsii 的预测市场上线活动仍处于方案调整、排期和 KOL 梳理阶段，说明上线前的内容、设计、联调、活动节奏还未完全合拍。[AR-3287, AR-3289, AR-3290, AR-3294]",
        "actions": "管理动作：MoonX 线不需要再被空泛地评价“状态不错”，而是应该把提现、UI 验收、接口联调、活动上线拆成 1 周内必须清零的最后一公里清单。这条线最接近真实交付，也最容易因为收尾不紧而拖慢上线节奏。[AR-3287, AR-3289, AR-3290, AR-3294]",
    },
]


PERSONAL_SIGNALS = [
    {
        "name": "Tony",
        "body": "已验证交付：CEX K 线委托点击异常优化 100%，MoonX App 持仓标签支持 Bot 标识 100%，预测市场资产页 UI 与数据接口接入 100%，充值流程 100%。在途事项：提现流程 80%。风险信号：本周最明确的剩余项就是提现链路，适合继续追联调与验收结果，而不是重复问总体进度。[AR-3287]",
    },
    {
        "name": "Owen",
        "body": "已验证交付：地址标签功能、预测市场固定分区和标签树、买卖授权接口、赎回接口流程优化、个人中心持仓金额与待领取金额、ES 查询优化、JSON 序列化问题修复均已完成。在途事项：预测市场编码规范优化 50%。风险信号：功能密度高，但后续仍要观察规范化和持续修 bug 是否拖累后续迭代效率。[AR-3290]",
    },
    {
        "name": "Liam",
        "body": "已验证交付：稳定币兑换数据库、后台管理接口、redis 缓存、市价交易、限价交易均为 100%。在途事项：下周继续完成其余接口。风险信号：当前看到的是后端骨架与核心交易能力推进，尚未看到完整联调或上线验收结果，不能提前把稳定币兑换当作已闭环能力。[AR-3288]",
    },
    {
        "name": "Lori",
        "body": "已验证交付：web 预测市场交易提示通知、历史成交调整、结算进度交互、循环时间优化、资产与用户详情布局、web 盈利地址展示、流动性池变化设计均为 100%。在途事项：web 链上预测 UI 验收 50%，App 链上预测设计 90%。风险信号：设计侧出图速度不慢，但交付真正上线前仍卡在验收与 App 尾项。[AR-3289]",
    },
    {
        "name": "Rsii",
        "body": "已验证交付：MoonX 社媒运营 29 条推文，特斯拉交易 S4 奖励派奖，KOL 招募 1.6W 浏览，Jasper 联合活动有效增粉 2945。在途事项：预测市场上线活动预告、竞猜活动、视频和新功能素材。风险信号：增长数据能看，但预测市场宣发仍在排期与素材准备阶段，说明市场侧节奏还没完全接上产品上线节奏。[AR-3294]",
    },
    {
        "name": "Crads",
        "body": "已验证交付：新 VPN 打通 Kibana 与 Grafana 生产环境、xxljob 新版本上生产、后台域名增加多层安全验证、web3 前端多项路径调整上线、独立 Grafana 监控上线、行情域名限速频率控制已切换拦截。在途事项：ES / Kibana 版本研究、新 VPN 文档映射、渗透需求调整。风险信号：基础设施推进密度高，但仍有“已完成观察中”“缺账号”“待安排”类尾项，说明支撑线可用但不够干净。[AR-3360]",
    },
    {
        "name": "Night",
        "body": "已验证交付：Polymarket 订单模块本地落库与发送、仓位业务模块、授权接口、赎回接口、认证缓存优化、可售出 token 数量接口均已完成。在途事项：二期接口对接、订单交易 WS 模块、订单与仓位状态实时更新。风险信号：当前证据止于 3.22，说明 Night 的周报样本偏旧，本版只能作为 MoonX 早期推进参照，不适合用来评价本周最终状态。[AR-233]",
    },
]


CEX_CROSS_CHECK = [
    "原始版本文档显示，`永续优化V1.1` 中合约跟单与合约网格顺延至 2026-03-20，安全中心顺延到 2026-04-20 / 3.9.4；同一份文档中 2026-04-20 的条目状态仍为“待开发”。这类延期不是推断，而是文档原文写明的顺延与状态。[AR-255, AR-735]",
    "CEX 大版本 / 需求文档本身已经具备较完整的 owner 分配。例如：USDC 合约、体验金 V3.0、web 合约网格、智能比例跟单、跟单包赔券都写明了前端 / 后端 / 后台 / 测试责任人。[AR-755, AR-786, AR-801, AR-803, AR-816]",
    "但当前周的原始周报样本里，能够直接确认的闭环更多集中在 MoonX / 预测市场和局部 CEX 界面项，例如 Tony 的 K 线委托点击优化。对大型 CEX 版本项，本版没有看到足够多的“已上线验收结果”样本，因此不会把所有文档项都强行判成延期或已完成。[AR-3287]",
]


UNKNOWNS = [
    "自动增量与回填链路仍是 fail-closed 状态，`autopilot_state.json` 记录 2026-03-31 的 incremental / backfill 失败，`audit_runs` 表为空，因此当前报告不具备完整 run lineage。",
    "客服、社媒等会议原文已入库，但结构化抽取并不完整；因此本版只能对已完整提取出的事实下判断。",
    "日报“开会前送达”已被明确要求，但当前本地证据不足以证明日报自动发送已经恢复。",
    "翻译流程要求已识别，但当前 `交易所实习` 文件夹里没有足够的翻译原文与术语核对样本，因此本版不输出翻译质量结论。",
]


def register_font() -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH), subfontIndex=0))


def escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def current_meta() -> dict[str, str]:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    counts = {
        "audit_records": cur.execute("SELECT COUNT(*) FROM audit_records").fetchone()[0],
        "source_documents": cur.execute("SELECT COUNT(*) FROM source_documents").fetchone()[0],
        "dept_meeting_history": cur.execute("SELECT COUNT(*) FROM dept_meeting_history").fetchone()[0],
        "audit_runs": cur.execute("SELECT COUNT(*) FROM audit_runs").fetchone()[0],
        "latest_ts": cur.execute("SELECT MAX(message_timestamp) FROM audit_records").fetchone()[0] or "",
    }
    conn.close()
    return counts


def build_markdown(meta: dict[str, str], now_text: str) -> str:
    lines: list[str] = []
    lines.append("# BYDFi CEO 核验版报告")
    lines.append("")
    lines.append(f"- 生成时间：{now_text}")
    lines.append("- 输出定位：给 CEO 的人工核验版 PDF，不宣称自动日报链路已恢复")
    lines.append(
        f"- 当前本地库规模：audit_records={meta['audit_records']} | source_documents={meta['source_documents']} | "
        f"dept_meeting_history={meta['dept_meeting_history']} | audit_runs={meta['audit_runs']}"
    )
    lines.append("")
    lines.append("## 1. 数据边界")
    lines.append("")
    for item in DATA_BOUNDARY:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 2. 管理层摘要")
    lines.append("")
    for item in EXEC_SUMMARY:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 3. CEO 最新要求覆盖")
    lines.append("")
    lines.append("| 要求 | 本版响应 | 覆盖情况 | 证据 |")
    lines.append("|---|---|---|---|")
    for row in REQUIREMENT_ROWS:
        lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |")
    lines.append("")
    lines.append("## 4. 部门穿透分析")
    lines.append("")
    for sec in DEPARTMENT_SECTIONS:
        lines.append(f"### {sec['title']}")
        lines.append("")
        lines.append(f"- {sec['progress']}")
        lines.append(f"- {sec['issues']}")
        lines.append(f"- {sec['actions']}")
        lines.append("")
    lines.append("## 5. 个人执行信号")
    lines.append("")
    for signal in PERSONAL_SIGNALS:
        lines.append(f"### {signal['name']}")
        lines.append("")
        lines.append(f"- {signal['body']}")
        lines.append("")
    lines.append("## 6. CEX / 版本计划交叉核验")
    lines.append("")
    for item in CEX_CROSS_CHECK:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 7. 未知项与阻塞")
    lines.append("")
    for item in UNKNOWNS:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 8. 证据索引")
    lines.append("")
    for item in EVIDENCE_INDEX:
        lines.append(f"- {item.ref} | {item.date} | {item.title} | {item.note}")
    lines.append("")
    return "\n".join(lines)


def make_styles():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleCN",
        parent=styles["Title"],
        fontName=FONT_NAME,
        fontSize=21,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )
    subtitle = ParagraphStyle(
        "SubtitleCN",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=10.5,
        leading=15,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10,
    )
    section = ParagraphStyle(
        "SectionCN",
        parent=styles["Heading2"],
        fontName=FONT_NAME,
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=8,
    )
    subhead = ParagraphStyle(
        "SubheadCN",
        parent=styles["Heading3"],
        fontName=FONT_NAME,
        fontSize=11.5,
        leading=16,
        textColor=colors.HexColor("#0f766e"),
        spaceBefore=8,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "BodyCN",
        parent=styles["BodyText"],
        fontName=FONT_NAME,
        fontSize=9.5,
        leading=15.2,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=5,
    )
    note = ParagraphStyle(
        "NoteCN",
        parent=styles["BodyText"],
        fontName=FONT_NAME,
        fontSize=8.8,
        leading=13.5,
        textColor=colors.HexColor("#475569"),
        spaceAfter=4,
    )
    return {
        "title": title,
        "subtitle": subtitle,
        "section": section,
        "subhead": subhead,
        "body": body,
        "note": note,
    }


def bullet(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(f"&bull; {escape(text)}", style)


def req_table(styles) -> Table:
    rows = [
        [Paragraph("<b>要求</b>", styles["body"]), Paragraph("<b>本版响应</b>", styles["body"]), Paragraph("<b>覆盖</b>", styles["body"]), Paragraph("<b>证据</b>", styles["body"])]
    ]
    for item in REQUIREMENT_ROWS:
        rows.append([Paragraph(escape(item[0]), styles["body"]), Paragraph(escape(item[1]), styles["body"]), Paragraph(escape(item[2]), styles["body"]), Paragraph(escape(item[3]), styles["note"])])
    table = Table(rows, colWidths=[34 * mm, 74 * mm, 20 * mm, 52 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ]
        )
    )
    return table


def evidence_table(styles) -> Table:
    rows = [
        [
            Paragraph("<b>证据 ID</b>", styles["body"]),
            Paragraph("<b>日期</b>", styles["body"]),
            Paragraph("<b>标题</b>", styles["body"]),
            Paragraph("<b>说明</b>", styles["body"]),
        ]
    ]
    for item in EVIDENCE_INDEX:
        rows.append(
            [
                Paragraph(escape(item.ref), styles["note"]),
                Paragraph(escape(item.date), styles["note"]),
                Paragraph(escape(item.title), styles["note"]),
                Paragraph(escape(item.note), styles["note"]),
            ]
        )
    table = Table(rows, colWidths=[22 * mm, 23 * mm, 54 * mm, 82 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ]
        )
    )
    return table


def add_page_number(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawRightString(195 * mm, 8 * mm, f"第 {canvas.getPageNumber()} 页")
    canvas.restoreState()


def build_story(meta: dict[str, str], now_text: str):
    styles = make_styles()
    story = []

    story.append(Paragraph("BYDFi CEO 核验版报告", styles["title"]))
    story.append(Paragraph("只保留可回溯的一手证据，不再复用旧版的无来源判断", styles["subtitle"]))
    story.append(
        Paragraph(
            f"生成时间：{escape(now_text)} | 数据库规模：audit_records={meta['audit_records']} / source_documents={meta['source_documents']} / "
            f"dept_meeting_history={meta['dept_meeting_history']} | audit_runs={meta['audit_runs']}",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 3))
    story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cbd5e1")))
    story.append(Spacer(1, 6))

    story.append(Paragraph("版本说明", styles["section"]))
    story.append(
        bullet(
            "旧版 `final_report.pdf` 可追溯到 2026-03-30 的现场抓取全量报告与本地 HTML 导出。它的结构可以参考，但其中很多管理结论在当前本地库中没有逐条一手证据映射，因此本版不照搬。",
            styles["body"],
        )
    )
    story.append(
        bullet(
            "本版的原则只有一个：能核到原始会议、原始周报、原始需求文档的才写；核不到的，一律写成未知项或管理建议，而不是装懂。",
            styles["body"],
        )
    )

    story.append(Paragraph("数据边界", styles["section"]))
    for item in DATA_BOUNDARY:
        story.append(bullet(item, styles["body"]))

    story.append(Paragraph("管理层摘要", styles["section"]))
    for item in EXEC_SUMMARY:
        story.append(bullet(item, styles["body"]))

    story.append(Paragraph("CEO 最新要求覆盖", styles["section"]))
    story.append(req_table(styles))

    story.append(Paragraph("部门穿透分析", styles["section"]))
    for sec in DEPARTMENT_SECTIONS:
        block = [
            Paragraph(escape(sec["title"]), styles["subhead"]),
            bullet(sec["progress"], styles["body"]),
            bullet(sec["issues"], styles["body"]),
            bullet(sec["actions"], styles["body"]),
            Spacer(1, 3),
        ]
        story.append(KeepTogether(block))

    story.append(Paragraph("个人执行信号", styles["section"]))
    for item in PERSONAL_SIGNALS:
        story.append(Paragraph(escape(item["name"]), styles["subhead"]))
        story.append(bullet(item["body"], styles["body"]))

    story.append(Paragraph("CEX / 版本计划交叉核验", styles["section"]))
    for item in CEX_CROSS_CHECK:
        story.append(bullet(item, styles["body"]))

    story.append(Paragraph("未知项与阻塞", styles["section"]))
    for item in UNKNOWNS:
        story.append(bullet(item, styles["body"]))

    story.append(PageBreak())
    story.append(Paragraph("证据索引", styles["section"]))
    story.append(
        Paragraph(
            "以下索引只列本报告实际使用的关键材料。任何没进这个索引却出现在结论里的判断，都不应该被信任。",
            styles["note"],
        )
    )
    story.append(evidence_table(styles))
    return story


def build_pdf() -> None:
    register_font()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    meta = current_meta()
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    OUTPUT_MD.write_text(build_markdown(meta, now_text), encoding="utf-8")

    doc = SimpleDocTemplate(
        str(ARCHIVE_PDF),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="BYDFi CEO 核验版报告",
        author="OpenAI Codex",
    )
    story = build_story(meta, now_text)
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)

    shutil.copyfile(ARCHIVE_PDF, OUTPUT_PDF)
    shutil.copyfile(ARCHIVE_PDF, OUTPUT_PDF_DESKTOP)


if __name__ == "__main__":
    build_pdf()
    print(str(OUTPUT_PDF))
