# three-kingdoms api

后端 Agent 服务。FastAPI + LangGraph + MongoDB。

## 本地开发（不走 Docker）

```bash
uv sync
uv run fastapi dev src/three_kingdoms/infrastructure/api.py
```

## 分层约定

- `domain/`：纯数据和提示词，不依赖任何外部服务
- `application/`：业务流程（LangGraph 图、RAG、记忆）
- `infrastructure/`：跟外部世界打交道（HTTP 接口、MongoDB 客户端）

依赖方向只能从外往内：infrastructure → application → domain。
