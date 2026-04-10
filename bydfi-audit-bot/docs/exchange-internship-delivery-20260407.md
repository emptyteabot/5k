# 交易所实习自动交付说明

更新时间：2026-04-07

## 现在这套东西能自动做到什么

1. 本地定时任务每天跑一次群覆盖审计、缺口补采、结构化摘要。
2. 每次跑完会自动生成一份 `日常/周度管理分析 PDF`。
3. PDF 会自动上传到腾讯云服务器现有 Web 目录。
4. 上传完成后，会自动把下载链接发到你给的 Lark webhook。
5. 同时会打一个 zip 包，里面带：
   - 最新 digest PDF
   - 最新 digest JSON
   - 最新 digest Markdown
   - 如果当前目录里有 CEO 版 PDF，也会一起打进去

## 现在还不能硬吹的地方

1. 服务器“独立自己抓 Lark”这件事，取决于服务器上的飞书登录态是否长期有效。
2. 当前这次落地，先闭环的是：
   `本地采集分析 -> 腾讯云云床 -> webhook 通知`
3. 如果以后要完全改成服务器独立跑，需要把服务器上的：
   - `external_group_collector.py`
   - `lark_storage_state.json`
   - 定时任务
   一起稳定化。

## 当前实际交付链路

说人话就是：

`本机定时跑分析 -> 生成管理 PDF -> 上传到 43.135.51.214 -> 发 Lark webhook 链接`

腾讯云上的公开目录现在走的是：

- 远端目录：`/opt/bydfi-agent-web/public/reports`
- 公开前缀：`http://43.135.51.214/reports/`

这条链路已经验证过，上传到这个目录的文件可以直接通过公网 URL 访问。

## 密钥和密码怎么放

不要把密码写进仓库文件。

当前代码读取这些环境变量：

- `BYDFI_TENCENT_HOST`
- `BYDFI_TENCENT_USER`
- `BYDFI_TENCENT_PASSWORD`
- `BYDFI_REPORT_REMOTE_DIR`
- `BYDFI_REPORT_BASE_URL`
- `BYDFI_LARK_WEBHOOK_URL`
- `BYDFI_EXTERNAL_COLLECTOR_PATH`
- `BYDFI_LARK_STORAGE_STATE_PATH`

前 6 个用于上传和 webhook。

后 2 个用于把采集器从“写死本机路径”改成“本机/服务器都能切换”。

## 每天怎么跑

现在 Windows 定时任务还是走这两个入口：

- `BYDFI-Daily-Ops-Cycle`
- `BYDFI-Weekly-Ops-Cycle`

它们调用的是：

- `scripts/start_ops_cycle.ps1`

这个脚本现在默认会：

1. 生成 digest PDF
2. 自动上传
3. 自动发 webhook

当前默认时间：

1. 每天 `08:00`
2. 周日 `09:00`

当前运行策略：

1. `daily` 默认走快路径：跳过全量 discover，只做覆盖审计、必要补采、分析、上传和 webhook 推送。
2. `weekly` 保留全量 discover，用来发现新群、做更重的覆盖检查。

手动跑法：

```powershell
python run_daily_ops_cycle.py --render-digest-pdf --deliver
python run_weekly_ops_cycle.py --render-digest-pdf --deliver
```

## 这份自动 PDF 的定位

这份自动 PDF 是“管理分析层”，不是最终 CEO 正文层。

它适合做：

1. 每天快速看重点业务线、延期风险、人效信号。
2. 先把管理注意力收缩到该盯的人和该盯的线。
3. 给你做二次判断和转发。

它不该直接替代：

1. 你手工压缩过的 CEO 终稿
2. 需要高度语义提纯的高层正文

## 如果以后升级成服务器独立全自动

下一步该做的是：

1. 把服务器上的 `storage_state` 刷成长期有效。
2. 把当前本地新版 repo 同步到服务器。
3. 在服务器上单独注册 cron/systemd 定时跑。
4. 再把“个人真实效能量化”和“延期风险红黄灯”继续加严。

到那一步，才叫：

`腾讯云独立采集 -> 独立分析 -> 独立上传 -> 独立推送`
