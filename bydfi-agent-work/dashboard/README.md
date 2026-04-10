# BYDFI Sentinel Dashboard

这是一个独立的 Next.js 仪表盘壳，用来展示：

- 左侧任务输入
- 中间结果流
- 右侧 Agent trace 日志

## 运行

```bash
npm install
npm run dev
```

## 环境变量

前端默认请求 `/api/chat/stream`。
如果后端不在同域，设置：

```bash
NEXT_PUBLIC_AGENT_API_BASE=http://127.0.0.1:3000
```
