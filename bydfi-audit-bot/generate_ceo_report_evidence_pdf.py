from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(r"C:\repo")
REPORTS = ROOT / "data" / "reports"
DB = ROOT / "data" / "audit_records.sqlite3"
OUT = REPORTS / "至4.2报告.pdf"
OUT_DESKTOP = Path(r"C:\Users\cyh\Desktop\至4.2报告.pdf")
OUT_DESKTOP_ARCHIVE = Path(r"C:\Users\cyh\Desktop\final_report_20260402_evidence_based.pdf")
OUT_DOWNLOADS = Path(r"C:\Users\cyh\Documents\Downloads\final_report.pdf")
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_NAME = "MicrosoftYaHei"


@dataclass(frozen=True)
class SourceRef:
    code: str
    kind: str
    title: str
    when: str
    locator: str
    note: str


def register_font() -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH), subfontIndex=0))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def latest_evidence_guard() -> dict:
    files = sorted(REPORTS.glob("evidence_guard_*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError("No evidence_guard JSON found.")
    return load_json(files[-1])


def query_one(conn: sqlite3.Connection, sql: str, params: Iterable[object] = ()) -> object:
    cur = conn.cursor()
    row = cur.execute(sql, tuple(params)).fetchone()
    return row[0] if row else None


def db_snapshot() -> dict:
    conn = sqlite3.connect(DB)
    try:
        return {
            "audit_records": int(query_one(conn, "SELECT COUNT(*) FROM audit_records") or 0),
            "source_documents": int(query_one(conn, "SELECT COUNT(*) FROM source_documents") or 0),
            "dept_meeting_history": int(query_one(conn, "SELECT COUNT(*) FROM dept_meeting_history") or 0),
            "inbound_messages": int(query_one(conn, "SELECT COUNT(*) FROM inbound_messages") or 0),
            "audit_runs": int(query_one(conn, "SELECT COUNT(*) FROM audit_runs") or 0),
            "latest_timestamp": query_one(conn, "SELECT MAX(message_timestamp) FROM audit_records") or "unknown",
            "today_records": int(
                query_one(
                    conn,
                    "SELECT COUNT(*) FROM audit_records WHERE substr(message_timestamp,1,10)='2026-04-02'",
                )
                or 0
            ),
        }
    finally:
        conn.close()


def sources() -> list[SourceRef]:
    return [
        SourceRef(
            "S01",
            "audit_records",
            "CEO 新要求截图入库",
            "2026-04-02",
            "audit_records#7932-7935",
            "四条手工入库记录，覆盖会议分析、周报系统、日报时效、反幻觉核对。",
        ),
        SourceRef(
            "S02",
            "file",
            "证据守卫审计结果",
            "2026-04-02 16:55 +08:00",
            str(REPORTS / "evidence_guard_2026-04-02T165537_0800.json"),
            "确认 autopilot fail、audit_runs 为空、噪音和 AI 二次分析混入。",
        ),
        SourceRef(
            "S03",
            "source_documents",
            "3.26 会议总结",
            "最近修改: 2026-03-26 / 抓取于 2026-03-31",
            "source_documents#259",
            "含 3.26 SEO 项目组周会、客服单周会、社媒周会、SEO+增长会议。",
        ),
        SourceRef(
            "S04",
            "source_documents",
            "3.27 会议总结",
            "最近修改: 2026-03-28 / 抓取于 2026-03-31",
            "source_documents#2366",
            "含 3.27 中心会议、单周组长汇报、风控审核双周会、产品部门周会。",
        ),
        SourceRef(
            "S05",
            "source_documents",
            "3.25 会议总结",
            "最近修改: 2026-03-25 / 抓取于 2026-03-31",
            "source_documents#2365",
            "含韩国招商周会、现货+用户会议、前端日会。",
        ),
        SourceRef(
            "S06",
            "source_documents",
            "3.17 SEO 项目周会",
            "2026-03-17",
            "source_documents#55",
            "用于补 SEO 历史基线，验证 3.26 之前就存在目标缺口。",
        ),
        SourceRef(
            "S07",
            "audit_records",
            "永续优化 V1.1 / 版本计划",
            "2026-03-25 / 2026-03-31",
            "audit_records#255,#459,#460",
            "确认 3.8.9 版本项顺延到 3.20 / 4.20，且 3.9.4 仍待开发。",
        ),
        SourceRef(
            "S08",
            "audit_records",
            "USDC 合约调整需求",
            "2026-03-25",
            "audit_records#801",
            "提供 CEX 需求 owner 分工与需求边界。",
        ),
        SourceRef(
            "S09",
            "audit_records",
            "体验金 V3.0",
            "2026-03-25",
            "audit_records#803",
            "提供 CEX 迭代 owner 分工与功能范围。",
        ),
        SourceRef(
            "S10",
            "audit_records",
            "WEB 合约网格",
            "2026-03-25",
            "audit_records#816",
            "提供 CEX 需求 owner 分工与功能范围。",
        ),
        SourceRef(
            "S11",
            "audit_records",
            "Tony 周报",
            "2026-03-27",
            "audit_records#3287",
            "CEX / MoonX App / 预测市场个人交付信号。",
        ),
        SourceRef(
            "S12",
            "audit_records",
            "Owen 周报",
            "2026-03-30",
            "audit_records#3290",
            "MoonX 预测市场后端推进和剩余项。",
        ),
        SourceRef(
            "S13",
            "audit_records",
            "Lori 周报",
            "2026-03-28",
            "audit_records#3289",
            "MoonX UI 设计与验收进度。",
        ),
        SourceRef(
            "S14",
            "audit_records",
            "Liam 周报",
            "2026-03-27",
            "audit_records#3288",
            "MoonX 后端稳定币兑换推进情况。",
        ),
        SourceRef(
            "S15",
            "audit_records",
            "Rsii 周报",
            "2026-03-31",
            "audit_records#3294",
            "MoonX 社媒与活动数据。",
        ),
        SourceRef(
            "S16",
            "audit_records",
            "Crads 周报",
            "2026-03-27",
            "audit_records#3360",
            "基础设施、安全、监控和 relay 相关推进。",
        ),
        SourceRef(
            "S17",
            "file",
            "翻译工作上下文简报",
            "2026-04-02",
            r"C:\Users\cyh\Desktop\BYDFi_translation_context_brief.md",
            "证明翻译链路是多文档工作流；当前缺少完整群聊历史，不能写成翻译绩效结论。",
        ),
    ]


def req_rows() -> list[list[str]]:
    return [
        [
            "会议级分析",
            "满足方式：本报告对本周关键会议材料逐部门拆解，不再做无边界总览。",
            "S01",
            "仍受历史短记录污染影响，历史趋势只给中等置信度。",
        ],
        [
            "日报时效",
            "已识别为系统职责，而非本 PDF 本身的交付频率。",
            "S01",
            "当前 PDF 只汇总截至 2026-04-02 已入库材料，不能冒充每日自动稳定推送。",
        ],
        [
            "周报+版本计划+话题群交叉",
            "用版本计划、需求 owner、个人周报交叉核对 CEX / MoonX。",
            "S07-S16",
            "研发话题群在当前本地快照中不完整，未对每条需求做到话题级逐项回链。",
        ],
        [
            "部门+个人双维分析",
            "部门分析和个人执行信号单列，且区分事实与建议。",
            "S03-S16",
            "部门历史表存在 23 条极短记录，趋势结论强度受限。",
        ],
        [
            "明确归因 / 零幻觉",
            "所有判断都挂来源码；缺 owner / ETA / 验收的地方直接标注证据不足。",
            "S02",
            "当前自动链路失败，因此不得宣称“全自动已恢复”。",
        ],
        [
            "翻译专项",
            "只写流程约束，不写虚构翻译产出。",
            "S01,S17",
            "当前缺少完整翻译任务明细和群聊历史，不做绩效判断。",
        ],
    ]


def executive_findings() -> list[tuple[str, str, str, str]]:
    return [
        (
            "结论 1：自动化链路仍是 fail-closed，今天新增的是 CEO 要求，不是全量业务事实刷新。",
            "证据守卫状态为 fail，autopilot 最近一次增量/回填都在 2026-03-31 失败；最新 2026-04-02 记录主要是截图入库的要求项。",
            "如果不把这一点写在最前面，后面的“最新报告”就是在冒充系统健康。",
            "S01,S02",
        ),
        (
            "结论 2：SEO 线问题识别清楚，但目标差距仍大，交付更多停留在方案与局部优化。",
            "3.26 周会显示整站索引率 38.5% 对目标 55%，PSEO 索引率 29%，72 小时新内容索引率完成度 5%；同周动作主要是 LCP 二期、schema、sitemap、本周 4 个 PSEO 模块人工优化。",
            "这不是“没做事”，但也远没到可以向 CEO 报喜的程度。问题在于目标差距仍大，且大量动作还在本周落地或待观察阶段。",
            "S03,S06",
        ),
        (
            "结论 3：中心/CEX 线有明确推进，但性能压测、版本顺延和 owner 闭环仍是主要风险。",
            "3.27 中心会议显示 28 个版本需求完成 15 个，10 个业务监控优化上线；同时 8 倍流量冲击仍有积压，永续下单 4K 验收未通过，Open API 3K 未验收。版本计划文档还显示合约跟单/网格从 3.20 顺延，安全中心顺延到 2026-04-20。",
            "能看到推进，但不能把“有进展”说成“无延期风险”。基线都在文件里，你要是视而不见，就是自欺。",
            "S04,S07",
        ),
        (
            "结论 4：韩国招商/活动线存在真实信任损耗，问题不只在风控，还在规则变更与系统稳定性。",
            "3.25 韩国招商周会记录显示注册、充值、交易量提升，但套利用户大幅增加；活动方案改动后，部分代理认为平台失信。此前 PNL 不更新问题影响韩国、越南、俄罗斯并引发投诉。",
            "这条线已经不是抽象的“活动效果波动”，而是代理信任和平台稳定性被一起打穿。",
            "S05",
        ),
        (
            "结论 5：MoonX 个人执行层面的推进比很多部门纪要更清晰，但仍停留在多角色并行推进、局部未完工的阶段。",
            "Owen、Lori、Liam、Tony、Rsii 的周报都给出了明确完成项与剩余项；例如预测市场提现 80%、Web 链上预测 UI 验收 50%、稳定币兑换剩余接口待完成。",
            "MoonX 线不能被写成“整体大好”或“整体卡死”。更准确的说法是：关键子模块有人推进，但仍缺统一闭环口径。",
            "S11-S15",
        ),
    ]


def department_blocks() -> list[dict]:
    return [
        {
            "name": "SEO / 增长",
            "good": [
                "3.26 周会给出明确指标和问题拆解：整站索引率 38.5%，questions 模块高无效曝光已做 No index；Cointalk 索引率 81%，表现最佳。",
                "本周动作清晰：LCP 二期、schema 字段、sitemap 优化落地；4 个 PSEO 模块人工优化本周上线；六周年预热文章要求 3 月 31 日前发布。",
            ],
            "bad": [
                "目标缺口仍大：目标 55%，当前 38.5%；PSEO 页面体量大但索引率 29%，点击极低。",
                "大量动作还停留在“本周落地/观察后复用”的阶段，缺最终验收结果和影响回收。",
            ],
            "action": "停止泛化汇报，只保留指标差距、当周已上线动作、未验收动作三层；优先放大 Cointalk、日语区和媒体类词，继续削减低效 questions 与低价值 PSEO 页面。",
            "confidence": "中",
            "sources": "S03,S06",
        },
        {
            "name": "客服",
            "good": [
                "3.26 客服单周会确认 PNL 字段缺失问题已由 Miya 上线修复，客服可正常导出。",
                "会议议程已经覆盖报表导出、培训账号、VIP 识别、AI 模型测试、客服话术优化，说明问题清单相对成型。",
            ],
            "bad": [
                "当前可验证事实主要停留在单点修复，缺少客服效率、用户满意度和 AI 测试效果的量化结果。",
                "历史周报中客服/KYC/风控多项事项长期处于待上线、待评审、转测试，闭环结果不足。",
            ],
            "action": "客服线所有“已修复”事项必须补上用户影响范围和补偿/补发动作；AI 模型测试若无准确率、覆盖率、人工复核结果，不准上升到管理成效。",
            "confidence": "中",
            "sources": "S03,S16",
        },
        {
            "name": "中心 / 技术 / 性能",
            "good": [
                "3.27 中心会议显示 28 个版本需求完成 15 个，10 个业务监控优化上线，平均耗时降低 50%。",
                "现货业务 P0/P1 需求各 4 个按期上线，无线上问题；品牌隔离策略已发测试环境，现货引擎改造待合入测试。",
            ],
            "bad": [
                "生产问题仍重：1 个严重事故、共 5 个问题，含 2 个 P1、1 个 P0；8 倍流量冲击仍有积压。",
                "压测验收未过：永续下单 4K 未通过，Open API 3K 未验收，现货止盈止损未实际压测。",
            ],
            "action": "把“性能保障”和“版本完成数”拆开汇报。没有压测验收通过，不准用完成数粉饰风险；4K / 3K / 止盈止损要有单独 owner、时间点和回归结果。",
            "confidence": "中高",
            "sources": "S04",
        },
        {
            "name": "韩国招商 / 运营",
            "good": [
                "本周新增 2 家大型新代理，尚在洽谈合作细节；交易量、注册、充值环比提升。",
                "已批量处理对敲行为用户，代理配合扣除异常佣金，当前舆情可控。",
            ],
            "bad": [
                "活动方案中途改动后，部分代理认为平台失信；用户出现充值后立即转出、注册量下滑的市场反应。",
                "此前 PNL 不更新问题跨韩国、越南、俄罗斯，引发用户投诉并伤害稳定性认知。",
            ],
            "action": "活动线必须建立实时监控和止损线，规则变更前先做影响评估；涉及稳定性的 bug 不修完就别再谈扩大代理信任。",
            "confidence": "中",
            "sources": "S05",
        },
        {
            "name": "CEX 产品 / 版本计划",
            "good": [
                "版本计划和需求 owner 记录相对完整，能看到 USDC 合约、体验金 V3.0、Web 合约网格、智能比例跟单等明确分工。",
                "报表重构按 3 月 31 日发版流程推进，交易量数据问题已修复，准备开放 KOL 体验。",
            ],
            "bad": [
                "版本计划文档直接写明合约跟单/网格顺延到 3.20，安全中心顺延到 4.20，说明延期信号客观存在。",
                "大量需求虽然有 owner，但缺最新验收口径和上线结果；部分功能仍待开发、待测试或拟延后上线。",
            ],
            "action": "CEX 报告必须从“是否有需求文档”切到“是否有上线/验收”。带顺延日期的项单独列红，不准混在普通进度里。",
            "confidence": "中高",
            "sources": "S04,S07,S08,S09,S10",
        },
        {
            "name": "MoonX / 社媒",
            "good": [
                "个人周报能看到明确推进：预测市场后端功能、UI 设计、社媒投放和活动数据都有进展。",
                "Rsii 周报给出 29 条推文、KOL 招募浏览量 1.6W、Jasper 联合活动有效增粉 2945 等量化结果。",
            ],
            "bad": [
                "多条子项仍未闭环：预测市场提现 80%，Web 链上预测 UI 验收 50%，App 链上预测设计 90%，稳定币兑换剩余接口待完成。",
                "会议级的 MoonX 总结在当前本地材料里不如个人周报完整，说明部门汇总口径弱于执行侧。",
            ],
            "action": "MoonX 单独报告应该直接围绕预测市场、稳定币兑换、社媒增长三条线写，不要再被大盘总览稀释。",
            "confidence": "中",
            "sources": "S11,S12,S13,S14,S15",
        },
    ]


def personal_rows() -> list[list[str]]:
    return [
        [
            "Tony",
            "Bot 标签展示、资产页 UI + 接口接入、充值流程已完成；提现流程 80%。",
            "预测市场提现、持仓/挂单/历史交易接口联调、盈利领取流程仍在后续。",
            "交付项清晰，但提现未闭环，不能写成全模块完成。",
            "S11",
        ],
        [
            "Owen",
            "地址标签上线、预测市场固定分区/标签树、授权接口、赎回流程优化、列表序列化问题修复已完成。",
            "编码规范优化 50%；下周继续处理预测市场问题和 K 线修复。",
            "后端推进强，但仍有工程治理与后续修复尾项。",
            "S12",
        ],
        [
            "Lori",
            "多项 Web 预测 UI 已完成；App 链上预测设计 90%。",
            "Web 链上预测 UI 验收 50%；仍有 APP 细节和规范对齐待补。",
            "设计产出多，但验收闭环不足。",
            "S13",
        ],
        [
            "Liam",
            "稳定币兑换数据库、后台管理接口、Redis 缓存、市价/限价交易均 100%。",
            "剩余接口下周继续完成。",
            "后端推进稳定，适合作为 MoonX 线的确定性交付样本。",
            "S14",
        ],
        [
            "Rsii",
            "29 条推文、奖励派发、KOL 招募浏览量 1.6W、Jasper 联合活动有效增粉 2945。",
            "预测市场上线预告/竞猜活动、渠道拓展、视频素材需求继续推进。",
            "运营数据可见，但与产品闭环仍需绑定，不然容易只剩声量。",
            "S15",
        ],
        [
            "Crads",
            "VPN 打通 Kibana/Grafana 生产环境、xxljob 升级、后台域名多层安全验证、独立 Grafana 监控等已上线或已完成。",
            "Claude relay 缺账号，渗透提需求调整待安排，ES/Kibana 升级研究待做。",
            "基础设施推进真实，但还有账号与安全项尾部风险。",
            "S16",
        ],
    ]


def cex_rows() -> list[list[str]]:
    return [
        [
            "版本基线",
            "3.8.9 文档写明合约跟单/网格顺延到 3.20，安全中心顺延到 4.20；3.9.4 当前仍待开发。",
            "说明延期信号客观存在，不能说“未见延期风险”。",
            "S07",
        ],
        [
            "USDC 合约",
            "前端 Steve，后台 Bobby，后端 Ken，测试 Zohar。",
            "有 owner，但当前本地材料未给出最新上线验收结果。",
            "S08",
        ],
        [
            "体验金 V3.0",
            "前端 Steve，后端 Travel/Ken/Raymy，后台 Bobby，测试 Abel。",
            "需求复杂且规则多，若无验收结果，最容易在活动/代理线复发争议。",
            "S09",
        ],
        [
            "Web 合约网格",
            "后端 Jimmy，前端 Chad，测试 Kimi。",
            "需求范围清晰，但当前看到的是需求文档，不是上线回执。",
            "S10",
        ],
        [
            "中心会议口径",
            "28 个版本需求完成 15 个；现货 P0/P1 各 4 个按期上线；报表重构按 3 月 31 日发版流程推进。",
            "性能压测和部分后端优化仍未闭环，版本数字不能覆盖质量风险。",
            "S04",
        ],
    ]


def moonx_rows() -> list[list[str]]:
    return [
        [
            "预测市场后端",
            "Owen 已完成固定分区、标签树、授权接口、赎回流程优化等多项后端工作。",
            "编码规范优化 50%，后续继续处理问题和 K 线修复。",
            "S12",
        ],
        [
            "预测市场设计",
            "Lori 完成多项 Web 设计，App 链上预测设计 90%。",
            "Web UI 验收仅 50%，说明设计到验收仍有断层。",
            "S13",
        ],
        [
            "稳定币兑换",
            "Liam 已完成数据库、后台接口、缓存、市价/限价交易。",
            "剩余接口待下周完成，属于接近闭环但未收口。",
            "S14",
        ],
        [
            "社媒增长",
            "Rsii 已完成 29 条推文、活动奖励派发、KOL 招募、增粉渠道拓展。",
            "仍需把社媒数据和产品上线节奏绑定，否则会形成运营热闹、产品未闭环。",
            "S15",
        ],
        [
            "前后端联动",
            "Tony 已完成 MoonX App 持仓标签 Bot 标识展示，并参与预测市场资产页/充值流程。",
            "提现流程仍 80%，是直接可见的未完成项。",
            "S11",
        ],
    ]


def blocked_conclusions() -> list[str]:
    return [
        "不能宣称“自动化日报/周报链路已恢复健康”，因为 evidence guard 仍为 fail，audit_runs 仍为空。 [S02]",
        "不能对全公司做最终绩效结论，部门历史表有 23 条极短记录，且自动链路从 2026-03-31 起未成功刷新。 [S02]",
        "不能把带顺延日期的 CEX 事项说成“无延期风险”，因为版本计划文件已经给出顺延。 [S07]",
        "不能把翻译专项写成已完成分析，因为当前只有流程 brief，没有完整任务明细与群聊历史。 [S17]",
        "不能把 AI 二次总结当成一手证据；Claude 分析机器人和群汇总分析只能做旁证，不能独立支撑 CEO 结论。 [S02]",
    ]


def next_actions() -> list[str]:
    return [
        "P0：恢复增量/回填执行并补 run lineage。没有 run_id、source_ids、prompt_hash，就别再谈“最新报告”自动化。 [S02]",
        "P0：把 CEO 报告拆成固定四层字段：事实、问题、建议、证据码。没有证据码的句子一律不上屏。 [S01,S02]",
        "P1：CEX 所有带顺延日期的项单独列红，并补 owner、ETA、验收口径；没有 ETA 就写“缺 ETA”，不要装作一切正常。 [S07-S10]",
        "P1：MoonX 按预测市场、稳定币兑换、社媒增长三条线单独出报告，不再混在综合总览里。 [S11-S15]",
        "P1：SEO 只报目标差距、当周已上线动作、未验收动作，不再用过程性汇报冒充结果。 [S03,S06]",
    ]


def title_page_rows(snapshot: dict, guard: dict) -> list[list[str]]:
    return [
        ["生成时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["报告边界", r"C:\Users\cyh\Desktop\交易所实习\bydfi-audit-bot"],
        ["本地记录总量", f"audit_records={snapshot['audit_records']} / source_documents={snapshot['source_documents']} / dept_meeting_history={snapshot['dept_meeting_history']}"],
        ["最新记录时间", str(snapshot["latest_timestamp"])],
        ["今日新增记录", str(snapshot["today_records"])],
        ["证据守卫状态", str(guard.get("overall_status", "unknown"))],
        ["关键现实", "今天新增已入库的是 CEO 要求；自动链路未恢复健康。"],
    ]


def on_page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(doc.leftMargin, 10 * mm, "至4.2报告")
    canvas.drawRightString(A4[0] - doc.rightMargin, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def add_heading(story: list, text: str, style: ParagraphStyle, spacer: float = 4) -> None:
    story.append(Paragraph(text, style))
    story.append(Spacer(1, spacer))


def add_bullets(story: list, items: list[str], style: ParagraphStyle) -> None:
    for item in items:
        story.append(Paragraph(f"• {item}", style))
        story.append(Spacer(1, 1.2))


def add_table(story: list, rows: list[list[str]], widths: list[float], font_name: str) -> None:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8.3),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 5))


def add_source_index(story: list, refs: list[SourceRef], body: ParagraphStyle, note: ParagraphStyle) -> None:
    for idx, ref in enumerate(refs, 1):
        story.append(Paragraph(f"<b>{ref.code}</b> | {ref.title}", body))
        story.append(Paragraph(f"类型：{ref.kind} | 时间：{ref.when}", note))
        story.append(Paragraph(f"定位：{ref.locator}", note))
        story.append(Paragraph(f"说明：{ref.note}", note))
        story.append(Spacer(1, 4))
        if idx in {8, 14}:
            story.append(PageBreak())


def build() -> Path:
    register_font()
    guard = latest_evidence_guard()
    snapshot = db_snapshot()
    refs = sources()

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "title",
        parent=styles["Title"],
        fontName=FONT_NAME,
        fontSize=20,
        leading=26,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle = ParagraphStyle(
        "subtitle",
        parent=styles["BodyText"],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
    )
    h1 = ParagraphStyle(
        "h1",
        parent=styles["Heading1"],
        fontName=FONT_NAME,
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=2,
    )
    h2 = ParagraphStyle(
        "h2",
        parent=styles["Heading2"],
        fontName=FONT_NAME,
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#1d4ed8"),
    )
    body = ParagraphStyle(
        "body",
        parent=styles["BodyText"],
        fontName=FONT_NAME,
        fontSize=9.4,
        leading=14,
        textColor=colors.HexColor("#111827"),
    )
    note = ParagraphStyle(
        "note",
        parent=body,
        fontSize=8.6,
        leading=12,
        textColor=colors.HexColor("#475569"),
    )

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    story: list = []

    story.append(Paragraph("至4.2报告", title))
    story.append(
        Paragraph(
            "截至 2026-04-02 的 CEO 事实定稿版 | 目标：只保留本地材料能证明的事实，不再复写旧稿幻觉。",
            subtitle,
        )
    )
    story.append(Spacer(1, 8))
    add_table(
        story,
        [["字段", "内容"], *title_page_rows(snapshot, guard)],
        [33 * mm, 138 * mm],
        FONT_NAME,
    )
    story.append(
        Paragraph(
            "先把丑话说在前面：这份报告可以用于 CEO 今日决策，不可以被包装成“自动化链路已恢复、系统已完全可信”。你如果忽略这个边界，后面所有判断都会被污染。 [S01,S02]",
            body,
        )
    )
    story.append(Spacer(1, 8))

    add_heading(story, "1. 逆向结论：旧版 PDF 是什么，为什么垃圾", h1)
    add_bullets(
        story,
        [
            "旧版 `C:\\Users\\cyh\\Documents\\Downloads\\final_report.pdf` 首页显示它是 2026-03-30 的浏览器导出版，底部暴露了 `file:///C:/Users/cyh/Desktop/rpt.html`，说明它来自桌面 HTML 打印，而不是严格证据链生成。",
            "项目目录里还能找到旧链路的源头痕迹：`source_documents#2256` 存着 `CEO_现场抓取全量报告_20260330`；`generate_ceo_report_v2_pdf.py` 和 `generate_ceo_report_pdf.py` 则是后续修补尝试。",
            "v2 脚本的问题不在样式，在方法：它拿统计量和模板拼 CEO 口吻报告，还伴随大量乱码中文，根本达不到“每个字都正确”的要求。",
        ],
        body,
    )
    story.append(
        Paragraph(
            "所以本次方案直接放弃沿用旧报告内容，只保留可回溯结构与少量可验证事实。无法回证的旧结论，一律删。 [S02,S03]",
            body,
        )
    )
    story.append(Spacer(1, 6))

    add_heading(story, "2. CEO 最新要求覆盖表", h1)
    add_table(
        story,
        [["要求", "本次处理", "证据", "剩余缺口"], *req_rows()],
        [28 * mm, 66 * mm, 18 * mm, 59 * mm],
        FONT_NAME,
    )

    add_heading(story, "3. 管理层先看这 5 条结论", h1)
    for issue, evidence, why, src in executive_findings():
        story.append(Paragraph(f"<b>{issue}</b>", body))
        story.append(Paragraph(f"证据：{evidence} [{src}]", body))
        story.append(Paragraph(f"判断：{why}", body))
        story.append(Spacer(1, 4))

    add_heading(story, "4. 部门穿透分析", h1)
    for block in department_blocks():
        add_heading(story, block["name"], h2, spacer=2)
        story.append(Paragraph(f"<b>做得好的：</b> {block['good'][0]}", body))
        story.append(Paragraph(f"{block['good'][1]}", body))
        story.append(Paragraph(f"<b>做得不好的：</b> {block['bad'][0]}", body))
        story.append(Paragraph(f"{block['bad'][1]}", body))
        story.append(Paragraph(f"<b>建议动作：</b> {block['action']}", body))
        story.append(Paragraph(f"<b>置信度：</b> {block['confidence']} | <b>来源：</b> {block['sources']}", note))
        story.append(Spacer(1, 5))

    add_heading(story, "5. 个人执行信号", h1)
    add_table(
        story,
        [["人员", "已验证交付", "在途事项", "风险判断", "证据"], *personal_rows()],
        [17 * mm, 52 * mm, 48 * mm, 46 * mm, 15 * mm],
        FONT_NAME,
    )
    story.append(
        Paragraph(
            "这里故意不写人格评价。CEO 要的是执行信号，不是主观印象。用消息量、出勤感、口气好坏去替代交付，就是低水平偷懒。 [S01]",
            body,
        )
    )
    story.append(Spacer(1, 6))

    add_heading(story, "6. CEX 版本计划交叉核对", h1)
    add_table(
        story,
        [["事项", "当前能确认的事实", "管理含义", "证据"], *cex_rows()],
        [28 * mm, 63 * mm, 62 * mm, 15 * mm],
        FONT_NAME,
    )
    story.append(
        Paragraph(
            "结论很直接：CEX 线不是没有 owner，而是有 owner 但缺最新验收闭环。你要继续拿“文档齐、分工齐”当进展，就是在拿过程替代结果。 [S07-S10]",
            body,
        )
    )
    story.append(Spacer(1, 6))

    add_heading(story, "7. MoonX 单独观察", h1)
    add_table(
        story,
        [["子线", "已验证事实", "当前缺口", "证据"], *moonx_rows()],
        [26 * mm, 70 * mm, 57 * mm, 15 * mm],
        FONT_NAME,
    )
    story.append(
        Paragraph(
            "MoonX 是当前最适合被拆成独立报告的线，因为个人周报信息密度明显高于综合会议纪要。继续把它埋在总报告里，只会稀释有效信息。 [S11-S15]",
            body,
        )
    )
    story.append(Spacer(1, 6))

    add_heading(story, "8. 翻译专项现状", h1)
    add_bullets(
        story,
        [
            "当前能确认的是流程，不是产出绩效：翻译执行表、notice 规则页、glossary、VPN/tooling 文档共同组成分布式工作流。 [S17]",
            "截图要求明确写了“先抽功能词形成行业关键词，再做文章翻译，并参考关键词”。这属于流程约束，不是当前 repo 已完成的翻译事实。 [S01]",
            "本地材料缺完整翻译群聊和逐任务明细，所以本报告只保留流程判断和风险，不写人效结论。",
        ],
        body,
    )
    story.append(Spacer(1, 6))

    add_heading(story, "9. 当前不能下的结论", h1)
    add_bullets(story, blocked_conclusions(), body)
    story.append(Spacer(1, 6))

    add_heading(story, "10. CEO 今日可直接下发的动作", h1)
    add_bullets(story, next_actions(), body)

    story.append(PageBreak())
    add_heading(story, "附录 A. 关键来源索引", h1)
    story.append(
        Paragraph(
            "附录不再塞成一页密表。这里改成逐条索引，目的不是好看，而是确保 CEO 真能看清每条结论回到哪里。",
            body,
        )
    )
    story.append(Spacer(1, 4))
    add_source_index(story, refs, body, note)
    story.append(
        Paragraph(
            "生成原则：一切管理判断都必须能回到本地源文件、SQLite 记录或审计报告。没有证据码的结论，不应出现在 CEO 定稿里。",
            note,
        )
    )

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    OUT_DESKTOP_ARCHIVE.write_bytes(OUT.read_bytes())
    OUT_DESKTOP.write_bytes(OUT.read_bytes())
    OUT_DOWNLOADS.write_bytes(OUT.read_bytes())
    return OUT_DESKTOP


if __name__ == "__main__":
    path = build()
    print(str(path))
