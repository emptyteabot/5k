# 交易所实习定时分析说明

更新时间：2026-04-07

## 这套定时分析是干嘛的

说人话：

1. 每天跑一轮，先检查必管群有没有漏采、有没有过期。
2. 如果有漏采或过期，就触发受控补采。
3. 然后把结构化摘要重新压成一份内部运营 digest。
4. 周日再额外跑一轮周度 digest，用于周视角看人效和延期风险。

这层产物不是直接发 CEO 的 PDF，而是给你做二次调整和决策压缩的中间分析层。

## 新增入口

- 日常 runner：`run_daily_ops_cycle.py`
- 周度 runner：`run_weekly_ops_cycle.py`
- 启动脚本：`scripts/start_ops_cycle.ps1`
- 注册计划任务：`scripts/register_ops_tasks.ps1`

## 产物位置

- `output/scheduled/daily_ops_digest_latest.json`
- `output/scheduled/daily_ops_digest_latest.md`
- `output/scheduled/weekly_ops_digest_latest.json`
- `output/scheduled/weekly_ops_digest_latest.md`

## 默认时间

- 每天：`18:30`
- 周日：`09:00`

## 注册计划任务

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register_ops_tasks.ps1
```

## 当前边界

已经能做：

1. 群覆盖审计
2. 缺失群补采
3. 日/周 digest 生成
4. 产物落盘

还没完全自动做：

1. 自动改写 CEO 正文
2. 自动判断最终版人效结论
3. 自动发送飞书/邮件
