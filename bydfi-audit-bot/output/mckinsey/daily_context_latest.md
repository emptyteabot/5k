# BYDFI 麦肯锡级日报入口

- 生成时间：2026-04-09T20:21:03.456781+08:00
- 周期：daily
- 一句话判断：今日采集链路还没闭环，先补齐必管群覆盖，再看管理判断。
- 覆盖状态：{"covered": 7, "missing": 0, "stale": 1, "unverified": 0}
- 发布门禁：blocked

## 固定入口

- 技能名：`bydfi-mckinsey-report`
- 日报命令：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_mckinsey_ceo_cycle.ps1 -Period daily`
- 周报命令：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_mckinsey_ceo_cycle.ps1 -Period weekly`

## 一句话触发

- 跑今天增量 CEO 报告
- 跑今天麦肯锡版管理报告
- 先补抓再重写终版 PDF
- 跑本周周日报告

## 本次产物

- 日/周 digest md：`C:\Users\cyh\Desktop\交易所实习\bydfi-audit-bot\output\scheduled\daily_ops_digest_latest.md`
- 日/周 digest json：`C:\Users\cyh\Desktop\交易所实习\bydfi-audit-bot\output\scheduled\daily_ops_digest_latest.json`
- 自动 CEO 草稿 pdf：`C:\Users\cyh\Desktop\交易所实习\bydfi-audit-bot\output\scheduled\daily_ceo_brief_latest.pdf`
- 最终管理层源稿：`C:\Users\cyh\Desktop\交易所实习\bydfi-audit-bot\data\reports\ceo_brief_final_send.md`
- 最终桌面 PDF：`C:\Users\cyh\Desktop\高层决策报告_终版.pdf`

## 使用规则

- 先跑增量补抓和自动草稿，再改 `ceo_brief_final_send.md`。
- 只有源稿改完并复核后，才渲染 `高层决策报告_终版.pdf`。
- 管理层版本禁止出现工具残留、需求口吻、数据库字段、写稿人内心旁白。

## 当前门禁提示

- 必管群仍存在 missing / stale / unverified，不能对外发送。
- 本次日常运行沿用了最近一次 discover 结果，适合先发给你审阅，不建议直接当作最终对外版。
- 不存在同日人工校准 CEO 源稿，本次自动发送仅供你审阅，不建议直接转发 CEO。

## 最终 PDF 状态

- 最终渲染成功：`True`
- 校验通过：`True`
