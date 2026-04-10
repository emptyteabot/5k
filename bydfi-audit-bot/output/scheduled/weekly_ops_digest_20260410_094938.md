# BYDFI 周度运营分析

- 生成时间：2026-04-10T09:49:38.278762+08:00
- 一句话：本周采集链路还没闭环，先补齐必管群覆盖，再看管理判断。
- 数据库：消息 2245 条，文档 113 份，采集批次 225 次
- 采集覆盖：必管群 covered=7 / missing=0 / stale=1 / unverified=0
- 发送门槛：阻断

## 必看业务线

| 群/线 | 最新时间 | 为什么要看 | 关键数字 |
| --- | --- | --- | --- |
| 产研周报发送群 | 2026-04-08T04:47:02.759520+00:00 | 阻塞项偏多 | delivered=440 / testing=166 / developing=71 / blocked=15 |
| 产研周报发送群 | 2026-04-06T19:07:14.707198+00:00 | 阻塞项偏多 | delivered=440 / testing=166 / developing=71 / blocked=15 |
| BYDFi·MoonX业务大群 | 2026-04-08T04:42:09.454504+00:00 | 阻塞项偏多；开发/测试堆积高于已交付 | delivered=123 / testing=110 / developing=55 / blocked=22 |
| BYDFi·MoonX业务大群 | 2026-04-06T18:58:52.901615+00:00 | 阻塞项偏多；开发/测试堆积高于已交付 | delivered=113 / testing=109 / developing=52 / blocked=22 |
| 产研周报发送群 | 2026-04-09T04:32:15.296493+00:00 | 阻塞项偏多 | delivered=118 / testing=30 / developing=19 / blocked=4 |

## 延期与闭环风险预警

| 群/线 | 风险分 | 预警原因 | 近期触发项 |
| --- | --- | --- | --- |
| BYDFi·MoonX业务大群 | 244.2 | 阻塞项偏多；开发/测试堆积高于已交付 | - |
| BYDFi·MoonX业务大群 | 240.4 | 阻塞项偏多；开发/测试堆积高于已交付 | - |
| 产研周报发送群 | 228.8 | 阻塞项偏多 | - |
| 产研周报发送群 | 228.8 | 阻塞项偏多 | - |
| 血战到底 | 154.7 | 阻塞项偏多 | - |

## 输出信号靠前

| 人 | 输出分 | 依据 | 涉及群 |
| --- | --- | --- | --- |
| Kater | 225.0 | 交付回执较多；跨线串联较多；阻塞项偏多 | AI翻译交流；BYDFi & Codeforce 全面合作群；BYDFi·MoonX业务大群；三部门效能优化需求；产研周报发送群；血战到底 |
| Owen | 219.3 | 交付回执较多；跨线串联较多 | BYDFi·MoonX业务大群；web3研发任务 |
| Jenny | 167.2 | 交付回执较多；阻塞项偏多 | 血战到底 |
| Shirley | 145.5 | 交付回执较多 | 产研周报发送群 |
| Iven | 123.6 | 交付回执较多 | 产研周报发送群 |

## 风险关注候选

| 人 | 关注分 | 依据 | 涉及群 |
| --- | --- | --- | --- |
| Chuang | 139.6 | 跨线串联较多；阻塞项偏多；在研/测试堆积偏高 | 中心研发任务；产研周报发送群 |
| Teemo | 139.5 | 交付回执较多；阻塞项偏多；在研/测试堆积偏高 | BYDFi·MoonX业务大群 |
| Jenny | 115.2 | 交付回执较多；阻塞项偏多 | 血战到底 |
| Jung | 104.6 | 交付回执较多；跨线串联较多；阻塞项偏多 | 中心研发任务；产研周报发送群 |
| Miya | 63.3 | 交付回执较多；跨线串联较多；在研/测试堆积偏高 | BYDFi & Codeforce 全面合作群；中心研发任务；产研周报发送群 |

## 发送门槛

- 必管群仍存在 missing / stale / unverified，不能对外发送。

## 自动化动作回执

- coverage_audit：成功（returncode=0）
- collect_registered_groups：成功（returncode=0）
- coverage_audit_after_collect：成功（returncode=0）

## 相关产物

- 当前 CEO 源稿：`C:\Users\cyh\Desktop\交易所实习\bydfi-audit-bot\data\reports\ceo_brief_final_send.md`
- 当前 CEO PDF：`C:\Users\cyh\Desktop\交易所实习\bydfi-audit-bot\data\reports\ceo_brief_20260408.pdf`
