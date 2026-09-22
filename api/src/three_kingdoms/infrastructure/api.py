from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

from three_kingdoms.application.conversation_service.generate_response import (
    get_response,
    get_streaming_response,
)
from three_kingdoms.application.conversation_service.reset_conversation import (
    reset_conversation_state,
)
from three_kingdoms.config import settings
from three_kingdoms.domain.character_factory import CharacterFactory
from three_kingdoms.domain.exceptions import CharacterNotFound
from three_kingdoms.infrastructure.mongo.checkpointer import (
    close_checkpointer,
    init_checkpointer,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_checkpointer()
    yield
    close_checkpointer()


app = FastAPI(lifespan=lifespan)

# 本地开发的默认放行列表。生产环境靠 ALLOWED_ORIGINS 覆盖掉它。
_DEV_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
]


def _allowed_origins() -> list[str]:
    """解析允许的前端来源。

    原来是 allow_origins=["*"] 配 allow_credentials=True。这个组合下
    Starlette 会把请求的 Origin 原样回显并带上 Allow-Credentials，
    等于**任何网站**都能带凭据调这个 API。本地无所谓，公网上不行。
    """
    configured = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    return configured or _DEV_ORIGINS


ALLOWED_ORIGINS = _allowed_origins()
logger.info(f"允许的前端来源: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Token"],
)


class ChatMessage(BaseModel):
    message: str
    character_id: str


@app.post("/chat")
async def chat(chat_message: ChatMessage):
    try:
        character_factory = CharacterFactory()
        character = character_factory.get_character(chat_message.character_id)

        response, _ = await get_response(
            messages=chat_message.message,
            character=character,
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    # **CORS 管不到 WebSocket。**这是规范层面的事，不是配置问题：上面那个
    # CORSMiddleware 对 /ws/chat 完全不生效，任何页面、任何脚本都能直接连
    # 上来跑对话——而对话正是花钱的那条路径。所以必须在这里自己查 Origin。
    #
    # 注意 Origin 是客户端可伪造的请求头，curl 随便就能带一个对的。它挡的是
    # "别人的网页偷用你的后端"，不是"有人写脚本刷你"。后者要靠反代层的限流
    # 和 OpenRouter 的消费上限，三层各管一段。
    origin = websocket.headers.get("origin")
    if origin not in ALLOWED_ORIGINS:
        logger.warning(f"拒绝来源不明的 WebSocket 连接: {origin!r}")
        await websocket.close(code=1008)  # 1008 = policy violation
        return

    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            if "message" not in data or "character_id" not in data:
                await websocket.send_json(
                    {
                        "error": (
                            "Invalid message format. "
                            "Required fields: 'message' and 'character_id'"
                        )
                    }
                )
                continue

            try:
                character_factory = CharacterFactory()
                character = character_factory.get_character(data["character_id"])

                response_stream = get_streaming_response(
                    messages=data["message"],
                    character=character,
                )

                await websocket.send_json({"streaming": True})

                full_response = ""
                async for chunk in response_stream:
                    full_response += chunk
                    await websocket.send_json({"chunk": chunk})

                await websocket.send_json(
                    {"response": full_response, "streaming": False}
                )

            except Exception as e:
                await websocket.send_json({"error": str(e)})

    except WebSocketDisconnect:
        pass


@app.post("/reset-memory")
async def reset_memory(
    character_id: str | None = None,
    x_admin_token: str | None = Header(default=None),
):
    """清空对话状态。**需要口令。**

    这个接口会清掉所有人的对话记录。公开暴露等于给全世界一个重置按钮，
    随便谁都能在别人聊到一半时把上下文抹掉。

    没配 ADMIN_TOKEN 时一律 404——不是 401、也不是 403。返回 404 是为了
    不暴露"这里存在一个管理接口"这个事实，扫描器看不出区别。
    """
    if settings.ADMIN_TOKEN is None:
        raise HTTPException(status_code=404, detail="Not Found")
    if x_admin_token != settings.ADMIN_TOKEN.get_secret_value():
        raise HTTPException(status_code=404, detail="Not Found")

    try:
        return await reset_conversation_state(character_id)
    except CharacterNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """给反代和监控用的探活。不碰数据库，不花钱。"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
