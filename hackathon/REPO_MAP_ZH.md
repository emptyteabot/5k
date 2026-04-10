# 5k 仓库地图

## 先说结论

这个仓库不是一个单独网页项目。
它是一个 **黑客松总仓**，里面同时包含：

- 当前展示网页
- 过去的网页快照
- BYDFI 实习阶段沉淀出来的脚本、报告、技能和资料
- Hermes Agent 底层引擎源码
- 黑客松原始参考材料

## 顶层目录说明

### `bydfi-agent-proxy/`

当前主展示入口。
你现在对外最该展示的网页就在这里。

关键文件：

- `index.html`：页面结构
- `styles.css`：页面样式
- `app.js`：前端逻辑和粒子背景
- `api/hermes_bridge.js`：网页到 Hermes 的桥接
- `api/_engine.js`：回答引擎封装
- `HACKATHON_WIN_PLAN_ZH.md`：黑客松赢法
- `PITCH_90S_ZH.md`：短版路演稿

### `bydfi-agent-work/`

更早一版网页/原型快照。
保留它是为了回看历史方案，不建议把它作为主展示版本。

### `bydfi-audit-bot/`

这是整个五千美元文件夹最硬的底座。

这里面有：

- `scripts/`：采集、检查、报告、调度脚本
- `mcp/`：MCP 服务相关代码
- `skills/`：本地技能
- `docs/`：交付说明、归档说明、调度说明
- `data/reports/`：结构化报告和产物
- `output/`：历史生成结果
- 顶层若干 `generate_*.py`、`run_*.py`：报告和任务流脚本

这部分说明你不是只做了一个前端壳，而是已经碰过企业级数据、报告和执行流。

### `hermes-agent/`

Hermes Agent 源码快照。

这部分的意义不是让你在路演里现场讲源码，
而是告诉别人：

- 你的网页不是凭空捏造概念
- 底层接的是成熟 Agent 框架
- 记忆、skills、消息网关、工具执行这些概念都有真实来源

### `references/`

黑客松官方 PDF 等参考资料。

## 如果你只有 5 分钟，按这个顺序看

1. `hackathon/BYDFI_5000_PLAYBOOK_ZH.md`
2. `bydfi-agent-proxy/HACKATHON_WIN_PLAN_ZH.md`
3. `bydfi-agent-proxy/PITCH_90S_ZH.md`
4. `bydfi-audit-bot/PITCH_3MIN_AND_JUDGE_QA_20260406.md`
5. `references/bydfi Reforge hackathon参赛指南.pdf`

## 如果你只有 1 分钟，记住这个

这套仓库的本质不是一个网页，也不是一个脚本。

它的本质是：

**一个已经开始成型的 BYDFI 定制版 Hermes Agent 总仓。**

网页负责展示，Hermes 负责底层能力，`bydfi-audit-bot` 负责证明你过去已经做过真正的企业材料和流程工作。
