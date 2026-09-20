# three-kingdoms-agent

一个可以和三国人物对话的游戏化 Agent 项目。玩家在 2D 地图上走动，靠近诸葛亮、曹操、关羽等角色即可开始对话；角色的回答由 LangGraph 编排的 Agent 生成，带短期记忆、长期记忆和 RAG 检索。

架构参考 [philoagents-course](https://github.com/neural-maze/philoagents-course)，前端游戏部分沿用其 Phaser 模板，后端 Agent 逻辑为本仓库自行实现。

## 目录

```
.
├── api/                     # Python 后端（Agent 全部逻辑在这里）
│   ├── src/three_kingdoms/  # ← 主要工作区
│   ├── tools/               # 离线脚本入口（建长期记忆、评估等）
│   ├── notebooks/           # 实验用
│   └── data/                # 抓取到的原始语料、评估数据集
├── ui/                      # Phaser 游戏前端（沿用上游模板）
├── docker-compose.yml       # MongoDB Atlas local + api + ui
└── Makefile
```

## 快速开始

```bash
cp api/.env.example api/.env    # 填入 GROQ_API_KEY
cd api && uv lock && cd ..      # 生成 uv.lock（Dockerfile 需要）
make infrastructure-up
```

- 游戏：http://localhost:8080
- API 文档：http://localhost:8000/docs

## 进度

- [✓] 模块 0：脚手架搭好，环境跑通
- [✓] 模块 1：裸 LangGraph，六个三国人物能对话（无记忆）
- [✓] 模块 2：短期记忆 —— checkpointer + 对话摘要 + /reset-memory
- [✓] 模块 3：RAG 长期记忆
- [ ] 模块 4：评估 + LLMOps
- [ ] 模块 5：迁移到 Postgres + pgvector
- [ ] 模块 6：换角色美术、加自己的功能
