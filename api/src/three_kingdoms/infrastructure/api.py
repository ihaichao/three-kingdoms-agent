from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from three_kingdoms.application.conversation_service.generate_response import (
    get_response,
    get_streaming_response,
)
from three_kingdoms.application.conversation_service.reset_conversation import (
    reset_conversation_state,
)
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
async def reset_memory(character_id: str | None = None):
    try:
        return await reset_conversation_state(character_id)
    except CharacterNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
