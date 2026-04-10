# 交易所实习作战档案

更新时间：2026-04-07

## 1. 这段实习实际做成了什么

这套仓库最后沉淀出来的，不只是“抓聊天记录写报告”，而是一条完整的管理情报生产链：

1. 把 Lark 群消息、会议纪要、云文档、周报、截图补录进本地数据库。
2. 对原始材料做去噪、去系统消息、去机器人痕迹、去后补脏数据影响。
3. 生成结构化群组摘要、人员卡片、风险统计和证据索引。
4. 把内部证据稿转换成管理层可直接阅读的 CEO 版报告。
5. 在出 PDF 前做“禁词校验 + 时效校验 + 局外人 review”，避免机器痕迹穿帮。
6. 把最终 PDF 自动落到桌面，形成稳定交付链路。

## 2. 核心资产地图

### 2.1 数据层

- `data/audit_records.sqlite3`
  主库，存抓取后的消息、审计结果、文档正文、采集批次。
- `tmp_desktop_audit_records.sqlite3`
  当前桌面工作副本，适合做快速核证和 Kater 需求回查。
- `config/lark_group_registry.json`
  正式纳管的群清单。以后凡是要宣称“收全”，都必须先对这个注册表。
- `data/reports/*.json`
  按群组沉淀的结构化摘要，带 `peopleCards / evidenceIndex / summaryText`。
- `data/reports/*.md`
  同步生成的人类可读版摘要。

### 2.2 分析与校验层

- `evidence_guard_audit.py`
  做证据守卫、识别系统噪音、提示幻觉和缺口。
- `scripts/check_group_coverage.py`
  把 discover 结果、注册表和本地库做三方对账，输出覆盖状态。
- `scripts/collect_registered_groups.py`
  对注册表中的缺失群或过期群做受控补采。
- `run_daily_ops_cycle.py`
  跑日常运营分析，生成 daily digest。
- `run_weekly_ops_cycle.py`
  跑周日周度分析，生成 weekly digest。
- `HALLUCINATION_REMEDIATION_20260402.md`
  幻觉治理经验总结。
- `STRICT_CEO_REPORT_TEMPLATE.md`
  早期管理层报告模板约束。

### 2.3 报告生产层

- `generate_management_report_pdf.py`
  内部证据型管理稿 PDF。
- `generate_ceo_brief_pdf.py`
  管理层版 CEO 简报 PDF，当前主交付脚本。
- `data/reports/management_report_20260407.md`
  内部分析型稿件。
- `data/reports/ceo_brief_20260407.md`
  当前 CEO-safe 管理层稿件源文件。

### 2.4 技能与规则层

- `C:\Users\cyh\.codex\skills\bydfi-ceo-brief`
  已沉淀好的 CEO 报告技能，专门处理管理层 PDF。
- `C:\Users\cyh\.codex\skills\bydfi-exchange-ops`
  本次新增的总控技能，负责整个实习工作流复用。

### 2.5 交付层

- `C:\Users\cyh\Desktop\高层决策报告_20260407_CEO版.pdf`
  当前给管理层发的成品。
- `data/reports/desktop_pdf_renders/`
  历次桌面交付备份。

## 3. 这段时间真正反复做的 SOP

### SOP A：从原始 Lark 到管理判断

1. 先定证据边界，只吃和业务判断直接相关的最新消息、周报、会议、云文档。
2. 把系统消息、拉群消息、撤回、机器人二次结论、回填时间日志全部降权或剔除。
3. 先做内部分析稿，不直接把原始抓取内容给 CEO。
4. 把内部稿翻译成管理语言，只保留：
   - 经营判断
   - 风险等级
   - 决策动作
   - 验收口径
5. PDF 出稿前必须做禁词和局外人 review。

### SOP B：Kater 需求判断

Kater 的要求不能只回答“内容有没有”，必须拆成三层：

1. 内容覆盖是否满足。
2. 结构闭环是否满足。
3. 自动化与时效是否真的满足。

只有三层都满足，才能说“完全满足”。

### SOP C：管理层版本写法

管理层稿只能保留会影响拍板的内容：

1. 一句话判断。
2. 今天必须拍板的三件事。
3. 会议级待办追踪页。
4. 核心问题线。
5. 必要时补 Ella 项目串联页。
6. 人效信号页。

### SOP D：人效页规则

Kater 对人效页的真实要求不是“列出所有人”，而是“降低认知负担”：

1. 不按业务线堆名字。
2. 样本不足的人不硬下判断。
3. 系统阻塞型人物不误判为低效。
4. 如果管理层明确要求收缩视角，就改成 `做得好的前五 / 做得不好的后五`。

### SOP E：新增群纳管与补采

以后只要新增研发群、任务群、项目群，必须走这套流程：

1. 先把群名写进 `config/lark_group_registry.json`。
2. 跑 `python scripts/check_group_coverage.py --run-discover --write-json output/group_coverage_latest.json`。
3. 看结果里的 `missing / stale / unverified`，不要口头说“应该都收到了”。
4. 跑 `python scripts/collect_registered_groups.py --run-discover` 做补采。
5. 再跑一次 coverage，对外只说最终状态，不说底层抓取细节。

## 4. 这段实习最重要的几条经验

1. 管理层最反感的不是坏消息，而是底层抓取残渣混进正式报告。
2. 真正的高层报告不是“汇总”，而是“降认知负担后的判断”。
3. 只看周报百分比会制造幻觉，必须把“已上线 / 已验收 / 待回执”强行区分开。
4. 不能把业务线结果差直接等同于个人低效，很多问题其实是验收口径和审批权问题。
5. 对 CEO 来说，前五和后五往往比全员平铺更有管理价值。

## 5. 以后继续复用时的最短路径

### 5.1 要继续出 CEO 报告

直接走：

1. `bydfi-ceo-brief` skill
2. 更新 `data/reports/ceo_brief_YYYYMMDD.md`
3. `python generate_ceo_brief_pdf.py`
4. `python C:\Users\cyh\.codex\skills\bydfi-ceo-brief\scripts\verify_ceo_brief.py <md-path>`

### 5.2 要继续做整套交易所实习分析

直接走：

1. `bydfi-exchange-ops` skill
2. 先查 `config/lark_group_registry.json` 和 `scripts/check_group_coverage.py`
3. 再查 `data/reports/*.json` 的结构化群组摘要
4. 查 `tmp_desktop_audit_records.sqlite3` 做原始核证
5. 必要时调用本地 MCP server

### 5.3 要走工具化调用

启动：

`python mcp/bydfi_exchange_ops_server.py`

可直接暴露：

- 归档摘要
- 群组摘要列表
- 报告搜索
- Kater 需求检索
- 群纳管注册表
- 群覆盖率对账
- 日常/周度运营分析
- CEO brief 校验
- CEO brief 渲染

## 6. 当前归档状态

这次归档后，已经形成三种可复用资产：

1. 文档化 SOP：本文件和 MCP 说明文件。
2. 技能化复用：`bydfi-ceo-brief` 和 `bydfi-exchange-ops`。
3. 工具化入口：`mcp/bydfi_exchange_ops_server.py`。
4. 群纳管机制：注册表 + 覆盖率对账 + 补采脚本。
