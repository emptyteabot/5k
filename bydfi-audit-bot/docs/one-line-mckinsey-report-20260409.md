# 一句话入口

更新时间：2026-04-09

## 这东西现在是什么

这不是再靠聊天临时拼上下文了，而是固定成了一条入口：

1. 增量查覆盖
2. 受控补抓
3. 生成日 / 周 digest
4. 生成自动 CEO 草稿
5. 改最终管理层源稿
6. 校验并导出固定终版 PDF

## 以后你只要说的话

- 跑今天增量 CEO 报告
- 跑今天麦肯锡版管理报告
- 先补抓再重写终版 PDF
- 跑本周周日报告

如果你想显式点名 skill，可以说：

- `$bydfi-mckinsey-report 跑今天增量 CEO 报告`

## 本地一键命令

日报：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_mckinsey_ceo_cycle.ps1 -Period daily
```

周报：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_mckinsey_ceo_cycle.ps1 -Period weekly
```

如果最终 CEO 源稿已经改好，要直接重渲染终版 PDF：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_mckinsey_ceo_cycle.ps1 -Period daily -RenderFinalPdf
```

## 固定产物位置

- 一句话上下文包：`output\mckinsey\daily_context_latest.md`
- 自动 digest：`output\scheduled\daily_ops_digest_latest.md`
- 自动 CEO 草稿：`output\scheduled\daily_ceo_brief_latest.md`
- 最终管理层源稿：`data\reports\ceo_brief_final_send.md`
- 最终桌面 PDF：`C:\Users\cyh\Desktop\高层决策报告_终版.pdf`

## 你以后不用重复交代的东西

- 要先查必需群覆盖再说“收全了”
- 要把最新群消息按时效加权
- 要压掉系统噪音、工具残留、需求口吻
- 要把最终版本写成 CEO 能直接看的管理报告
- 要自检、validator、PDF 抽检三层复核
