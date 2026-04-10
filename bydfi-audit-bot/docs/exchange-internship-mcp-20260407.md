# 交易所实习 MCP 复用说明

更新时间：2026-04-07

## 1. 目标

把这段实习期间最常调用的动作，从“人手点脚本”升级成可被客户端直接调用的本地 MCP 工具。

当前落地的是一个本地 stdio server：

- 路径：`mcp/bydfi_exchange_ops_server.py`
- 启动命令：`python mcp/bydfi_exchange_ops_server.py`

## 2. 当前暴露的工具

### `archive.summary`

返回：

- 归档文档位置
- 关键 skill 位置
- MCP server 路径
- 最新 CEO brief 源文件与 PDF

### `sources.list`

返回当前 `data/reports/*.json` 中可直接复用的群组摘要列表，包括：

- 文件名
- 标题
- peopleCount
- reportCount
- documentCount

### `report.search`

按关键词搜索 `data/reports/` 下的 md/json 文本，适合快速回找：

- 人名
- 项目名
- 问题线
- 会议标题

### `requirements.search`

查询 `tmp_desktop_audit_records.sqlite3` 或主库里的 Kater 需求、截图补录要求、历史核证内容。

### `group.registry`

返回当前已经正式纳管的 Lark 群清单，包括：

- 群名
- 分类
- 是否强制纳管
- 优先级

### `group.coverage`

读取 `config/lark_group_registry.json`，对账：

- 注册表里的群
- 最新 discover 发现到的群
- 本地 SQLite 已采集到的群
- 最后一次采集状态

这一步是以后回答“有没有收全”时的标准入口，不能再只靠记忆或口头判断。

### `ops.daily_run`

跑一轮日常运营分析：

- 群覆盖对账
- 必要时补采
- 生成 daily digest

### `ops.weekly_run`

跑一轮周度运营分析：

- 群覆盖对账
- 必要时补采
- 生成 weekly digest

### `ops.digest_latest`

读取最新生成的 daily / weekly digest，方便客户端直接消费。

### `ceo_brief.validate`

调用 `bydfi-ceo-brief` 的校验脚本，对管理层稿做禁词和结构校验。

### `ceo_brief.render`

运行 `generate_ceo_brief_pdf.py`，并返回 repo 内 PDF 与桌面 PDF 的路径和时间戳。

## 3. 设计原则

1. 只暴露高频动作，不把整个 repo 生硬塞成工具。
2. 优先暴露“取信息”和“做校验”类动作，避免高风险写操作。
3. 直接复用现有脚本，不重复发明另一套逻辑。
4. 所有输出默认转成文本，方便被大模型直接消费。

## 4. 客户端接入示例

本地 stdio 配置思路：

```json
{
  "mcpServers": {
    "bydfi-exchange-ops": {
      "command": "python",
      "args": [
        "C:/Users/cyh/Desktop/交易所实习/bydfi-audit-bot/mcp/bydfi_exchange_ops_server.py"
      ]
    }
  }
}
```

## 5. 下一步可以继续加的工具

如果后面继续做自动化，可以继续往这个 server 上加：

1. `people.rank`
   直接从群组摘要里生成前五 / 后五候选名单。
2. `meeting.followups`
   从会议记录里抽出待办、缺口、今日新增待办。
3. `ella.progress`
   从产品 / 前端 / 后端 / 测试口径里自动拼 Ella 串联表。
4. `evidence.guard`
   直接触发 `evidence_guard_audit.py` 输出风险报告。
5. `group.collect`
   对缺失或过期群做受控补采。
6. `ops.daily_run / ops.weekly_run`
   直接从 MCP 触发日常或周日分析。

## 6. 当前边界

当前 server 是本地复用入口，不是公网服务，也不负责：

1. 自动调度 Lark 长期抓取。
2. 定时任务调度。
3. 权限系统。
4. 多用户并发。

它的作用是把这次实习期间已经稳定的分析与交付动作，抽成一个可被客户端复用的本地工具层。
