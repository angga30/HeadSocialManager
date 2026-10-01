"""Conversation + chat message persistence (UI record of agent chats).

Agent memory lives in the ADK session (DatabaseSessionService); these tables are the
durable, human-readable record the web/TUI renders (title, status, ordered messages).
"""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from headofsocial.domain.models import ChatMessage, Conversation

STATUS_IDLE = "idle"
STATUS_PROCESSING = "processing"
STATUS_ERROR = "error"


def _title_from(text: str) -> str:
    clean = " ".join(text.strip().split())
    return (clean[:57] + "…") if len(clean) > 60 else (clean or "Percakapan baru")


async def create(session: AsyncSession, title: str = "Percakapan baru") -> Conversation:
    conv = Conversation(title=title[:120], status=STATUS_IDLE, adk_session_id="pending")
    session.add(conv)
    await session.flush()
    conv.adk_session_id = f"conv-{conv.id}"
    await session.commit()
    await session.refresh(conv)
    return conv


async def list_conversations(session: AsyncSession) -> list[dict]:
    counts = dict(
        (await session.execute(
            select(ChatMessage.conversation_id, func.count(ChatMessage.id)).group_by(
                ChatMessage.conversation_id
            )
        )).all()
    )
    convs = (
        await session.execute(select(Conversation).order_by(Conversation.updated_at.desc()))
    ).scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "status": c.status,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "message_count": counts.get(c.id, 0),
        }
        for c in convs
    ]


async def get(session: AsyncSession, conversation_id: int) -> Conversation | None:
    return await session.get(Conversation, conversation_id)


async def delete(session: AsyncSession, conversation_id: int) -> bool:
    conv = await session.get(Conversation, conversation_id)
    if conv is None:
        return False
    await session.delete(conv)
    await session.commit()
    return True


async def add_message(
    session: AsyncSession, conversation_id: int, role: str, text: str
) -> ChatMessage:
    msg = ChatMessage(conversation_id=conversation_id, role=role, text=text)
    session.add(msg)
    conv = await session.get(Conversation, conversation_id)
    if conv is not None:
        if role == "user" and conv.title == "Percakapan baru":
            conv.title = _title_from(text)
        conv.updated_at = func.now()
    await session.commit()
    await session.refresh(msg)
    return msg


async def list_messages(session: AsyncSession, conversation_id: int) -> list[dict]:
    rows = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.id)
        )
    ).scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "text": m.text,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]


async def last_user_message(session: AsyncSession, conversation_id: int) -> str | None:
    """Text of the most recent user message (used by retry/regenerate)."""
    row = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id, ChatMessage.role == "user")
            .order_by(ChatMessage.id.desc())
            .limit(1)
        )
    ).scalars().first()
    return row.text if row else None


async def delete_trailing_assistant(session: AsyncSession, conversation_id: int) -> bool:
    """Drop the last message if it is an assistant reply (retry re-runs it)."""
    row = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.id.desc())
            .limit(1)
        )
    ).scalars().first()
    if row is None or row.role != "assistant":
        return False
    await session.delete(row)
    await session.commit()
    return True


async def set_status(session: AsyncSession, conversation_id: int, status: str) -> None:
    await session.execute(
        update(Conversation).where(Conversation.id == conversation_id).values(status=status)
    )
    await session.commit()


async def reset_stale_processing(session: AsyncSession) -> int:
    """Any 'processing' left over from a crashed/restarted server becomes idle."""
    result = await session.execute(
        update(Conversation)
        .where(Conversation.status == STATUS_PROCESSING)
        .values(status=STATUS_IDLE)
    )
    await session.commit()
    return result.rowcount or 0