"""Chat API: conversations, message history, mention search, and SSE streaming."""

import json
import logging
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from headofsocial.services import conversation_service, mentions_service
from headofsocial.services.chat_service import ChatService
from headofsocial.storage.db import SessionFactory
from headofsocial.tools._deps import ensure_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@lru_cache(maxsize=1)
def get_chat_service() -> ChatService:
    """One shared ChatService (runner + DB session service); sessions are per-conversation."""
    return ChatService()


class ChatRequest(BaseModel):
    message: str
    mentions: list[dict] = Field(default_factory=list)


def _sse(event: dict) -> str:
    """Serialise a service event dict onto an SSE frame (its `type` becomes the event name)."""
    payload = {k: v for k, v in event.items() if k != "type"}
    return f"event: {event['type']}\ndata: {json.dumps(payload)}\n\n"


async def _require_conversation(conversation_id: int) -> None:
    async with SessionFactory() as session:
        if await conversation_service.get(session, conversation_id) is None:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")


@router.get("/conversations")
async def list_conversations():
    await ensure_db()
    async with SessionFactory() as session:
        return await conversation_service.list_conversations(session)


@router.post("/conversations")
async def create_conversation():
    await ensure_db()
    async with SessionFactory() as session:
        conv = await conversation_service.create(session)
        return {"id": conv.id, "title": conv.title, "status": conv.status}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int):
    await ensure_db()
    async with SessionFactory() as session:
        if not await conversation_service.delete(session, conversation_id):
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        return {"ok": True}


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: int):
    await ensure_db()
    async with SessionFactory() as session:
        if await conversation_service.get(session, conversation_id) is None:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        return await conversation_service.list_messages(session, conversation_id)


@router.get("/mentions")
async def search_mentions(q: str = Query("", description="Query untuk brand/channel/post")):
    await ensure_db()
    async with SessionFactory() as session:
        return await mentions_service.search(session, q)


@router.post("/conversations/{conversation_id}/stream")
async def chat_stream(
    conversation_id: int,
    body: ChatRequest,
    request: Request,
) -> StreamingResponse:
    """Stream the agent's reply for a conversation as SSE (POST so the body can carry mentions)."""
    await ensure_db()
    await _require_conversation(conversation_id)
    chat = get_chat_service()

    async def event_source():
        try:
            async for event in chat.stream(conversation_id, body.message, body.mentions):
                yield _sse(event)
        finally:
            # Client went away mid-run → stop the server-side task too (no-op if finished).
            chat.stop(conversation_id)

    return StreamingResponse(event_source(), media_type="text/event-stream")


@router.post("/conversations/{conversation_id}/stop")
async def stop_conversation(conversation_id: int):
    """Cancel the running agent task; the partial reply is kept with a (dihentikan) marker."""
    await ensure_db()
    await _require_conversation(conversation_id)
    stopped = get_chat_service().stop(conversation_id)
    if not stopped:
        async with SessionFactory() as session:
            await conversation_service.set_status(
                session, conversation_id, conversation_service.STATUS_IDLE
            )
    return {"ok": True, "stopped": stopped}


@router.post("/conversations/{conversation_id}/retry")
async def retry_stream(conversation_id: int, request: Request) -> StreamingResponse:
    """Re-run the last user message (dropping the last assistant reply) as an SSE stream."""
    await ensure_db()
    async with SessionFactory() as session:
        if await conversation_service.get(session, conversation_id) is None:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        text = await conversation_service.last_user_message(session, conversation_id)
        if text is None:
            raise HTTPException(status_code=400, detail="Tidak ada pesan untuk diulang")
        await conversation_service.delete_trailing_assistant(session, conversation_id)

    mentions = mentions_service.parse_mentions(text)
    chat = get_chat_service()

    async def event_source():
        try:
            async for event in chat.stream(conversation_id, text, mentions, retry=True):
                yield _sse(event)
        finally:
            chat.stop(conversation_id)

    return StreamingResponse(event_source(), media_type="text/event-stream")
