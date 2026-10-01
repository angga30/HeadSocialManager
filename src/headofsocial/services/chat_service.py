"""Agent chat service — one shared ADK runner, sessions persisted in the DB.

Used by both the TUI and the web (SSE). Agent memory lives in ADK's
DatabaseSessionService (survives restart); the human-readable transcript lives in our
conversation tables. No per-request global mutable state — concurrent conversations are
isolated by session id.

The stream is **event-based** (not plain text) so the UI can show the agent "working":
`status`, `agent`, `tool`, `token`, `error`, `done`. The ADK runner already emits all of
this when `streaming_mode=SSE` — this service just forwards it instead of collapsing it
to a single final chunk.

Cancellation: each run runs in its own asyncio task registered per conversation, so a
`stop` (or a client disconnect) can cancel it mid-flight; the partial reply is persisted
with a `(dihentikan)` marker.
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.agents import RunConfig
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.apps.app import App
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from headofsocial.agents.root_agent import create_root_agent
from headofsocial.agents.trace_plugin import AgentTracePlugin, _compact_args, _result_summary
from headofsocial.config import settings
from headofsocial.services import conversation_service, mentions_service
from headofsocial.storage.db import SessionFactory

logger = logging.getLogger(__name__)

APP_NAME = "chat"
USER_ID = "web-user"
STOP_MARKER = "\n\n_(dihentikan)_"
NO_REPLY = "_Agent tidak menghasilkan respons._"

_DB_MARKERS = ("readonly", "read-only", "database is locked", "unable to open database")

# One SSE event as a dict; the route serialises {"type", ...} onto `event:`/`data:` lines.
ChatEvent = dict[str, Any]


def _error_message(exc: Exception) -> str:
    """Turn an exception into an actionable message (DB vs API key vs generic)."""
    text = str(exc)
    low = text.lower()
    if any(m in low for m in _DB_MARKERS):
        return (
            "⚠️ Database tidak bisa ditulis (SQLite readonly/locked).\n"
            "Kemungkinan: file DB dihapus/dipindah saat server berjalan, atau folder `data/` "
            "tidak writable.\n"
            "Perbaikan: hentikan server, pastikan folder `data/` bisa ditulis (atau hapus lalu "
            "buat ulang), lalu jalankan ulang.\n"
            f"Detail: {text[:200]}"
        )
    if "api key" in low or "authentication" in low or "401" in low or "credentials" in low:
        return f"⚠️ Error autentikasi provider: {text[:200]}\n(Cek API key di .env)"
    return f"⚠️ Error: {text[:300]}"


class ChatService:
    def __init__(self, user_id: str = USER_ID) -> None:
        self._user_id = user_id
        self._session_service = DatabaseSessionService(db_url=settings.resolved_db_url)
        self._adk_app = App(
            name=APP_NAME,
            root_agent=create_root_agent(),
            context_cache_config=ContextCacheConfig(cache_intervals=10, ttl_seconds=1800),
            plugins=[AgentTracePlugin()],
        )
        self._runner = Runner(app=self._adk_app, session_service=self._session_service)
        # conversation_id -> running agent task (for server-side stop).
        self._tasks: dict[int, asyncio.Task] = {}

    async def _ensure_adk_session(self, adk_session_id: str) -> None:
        existing = await self._session_service.get_session(
            app_name=APP_NAME, user_id=self._user_id, session_id=adk_session_id
        )
        if existing is None:
            await self._session_service.create_session(
                app_name=APP_NAME, user_id=self._user_id, session_id=adk_session_id
            )

    async def _agent_events(self, adk_session_id: str, text: str) -> AsyncGenerator[ChatEvent, None]:
        """Run the agent and yield UI events (status/agent/tool/token) from ADK's stream.

        ADK in SSE mode emits partial text chunks *and* a final aggregated text event for
        each model turn; we dedupe so the text is never shown twice.
        """
        new_message = types.Content(role="user", parts=[types.Part.from_text(text=text)])
        config = RunConfig(streaming_mode=StreamingMode.SSE)
        current_agent = ""
        displayed = ""  # text already streamed for the current model turn

        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=adk_session_id, new_message=new_message, run_config=config
        ):
            author = event.author or ""
            if author and author != "user" and author != current_agent:
                current_agent = author
                displayed = ""
                yield {"type": "agent", "name": author}

            if event.get_function_calls():
                if event.partial:
                    continue
                displayed = ""
                for call in event.get_function_calls():
                    if call.name == "transfer_to_agent":
                        target = (call.args or {}).get("agent_name")
                        if target and target != current_agent:
                            current_agent = str(target)
                            yield {"type": "agent", "name": str(target)}
                        continue
                    yield {
                        "type": "tool",
                        "status": "start",
                        "name": call.name,
                        "summary": _compact_args(call.args),
                    }
                continue

            if event.get_function_responses():
                if event.partial:
                    continue
                displayed = ""
                for response in event.get_function_responses():
                    yield {
                        "type": "tool",
                        "status": "done",
                        "name": response.name,
                        "summary": _result_summary(response.response),
                    }
                continue

            if not (event.content and event.content.parts):
                continue
            chunk = "".join(part.text for part in event.content.parts if part.text)
            if not chunk:
                continue
            if event.partial:
                displayed += chunk
                yield {"type": "token", "text": chunk}
            elif chunk != displayed:
                # Final aggregated text: emit only the part not already streamed.
                extra = chunk[len(displayed):] if chunk.startswith(displayed) else chunk
                displayed = chunk
                if extra:
                    yield {"type": "token", "text": extra}

    async def _run_agent(
        self,
        conversation_id: int,
        adk_session_id: str,
        prompt: str,
        queue: "asyncio.Queue[ChatEvent | None]",
    ) -> None:
        """Consume the agent stream, push UI events to the queue, persist the final reply."""
        collected: list[str] = []
        error: str | None = None
        stopped = False

        def text_so_far() -> str:
            return "".join(collected)

        try:
            await queue.put({"type": "status", "state": "thinking"})
            async for event in self._agent_events(adk_session_id, prompt):
                if event["type"] == "token":
                    collected.append(event["text"])
                elif event["type"] == "agent" and collected and not text_so_far().endswith("\n"):
                    # Separate consecutive agents' answers in the transcript.
                    collected.append("\n\n")
                    await queue.put({"type": "token", "text": "\n\n"})
                await queue.put(event)
        except asyncio.CancelledError:
            stopped = True
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI + DB
            logger.exception("Agent stream failed (conv %s)", conversation_id)
            error = _error_message(exc)
        finally:
            self._tasks.pop(conversation_id, None)

            reply = text_so_far()
            if stopped:
                reply = f"{reply}{STOP_MARKER}" if reply else STOP_MARKER.strip()
            if error:
                reply = error
            elif not reply:
                reply = NO_REPLY

            message_id: int | None = None
            try:
                async with SessionFactory() as session:
                    msg = await conversation_service.add_message(
                        session, conversation_id, "assistant", reply
                    )
                    message_id = msg.id
                    await conversation_service.set_status(
                        session,
                        conversation_id,
                        conversation_service.STATUS_ERROR if error else conversation_service.STATUS_IDLE,
                    )
            except Exception:
                logger.exception("Gagal menyimpan balasan (conv %s)", conversation_id)

            if error:
                await queue.put({"type": "error", "message": error, "retryable": True})
            await queue.put(
                {"type": "done", "message_id": message_id, "stopped": stopped, "has_error": bool(error)}
            )
            await queue.put(None)
            logger.info("Agent reply (%d chars) for conv %s", len(reply), conversation_id)

    async def stream(
        self,
        conversation_id: int,
        text: str,
        mentions: list[dict] | None = None,
        *,
        retry: bool = False,
    ) -> AsyncGenerator[ChatEvent, None]:
        """Run the agent for a conversation, yielding UI events; persist messages/status.

        `retry=True` re-runs the last user message without recording a new user turn.
        """
        logger.info("Agent request (conv %s, retry=%s): %s", conversation_id, retry, text)

        # Persist the incoming turn. If the DB is unwritable, say so once and stop —
        # otherwise every later write cascades into a confusing nested error.
        try:
            async with SessionFactory() as session:
                conv = await conversation_service.get(session, conversation_id)
                if conv is None:
                    yield {
                        "type": "error",
                        "message": f"Conversation {conversation_id} tidak ditemukan.",
                        "retryable": False,
                    }
                    return
                adk_session_id = conv.adk_session_id
                mention_block = await mentions_service.build_context(session, mentions or [])
                if not retry:
                    await conversation_service.add_message(session, conversation_id, "user", text)
                await conversation_service.set_status(
                    session, conversation_id, conversation_service.STATUS_PROCESSING
                )
        except Exception as exc:
            logger.exception("Gagal menyimpan pesan (conv %s)", conversation_id)
            yield {"type": "error", "message": _error_message(exc), "retryable": True}
            return

        await self._ensure_adk_session(adk_session_id)
        prompt = f"{mention_block}\n\n{text}" if mention_block else text

        queue: asyncio.Queue[ChatEvent | None] = asyncio.Queue()
        task = asyncio.create_task(
            self._run_agent(conversation_id, adk_session_id, prompt, queue),
            name=f"chat-run-{conversation_id}",
        )
        self._tasks[conversation_id] = task
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            self._tasks.pop(conversation_id, None)
            if not task.done():
                task.cancel()
                with contextlib.suppress(BaseException):
                    await task

    def stop(self, conversation_id: int) -> bool:
        """Cancel the running agent task for a conversation (server-side stop)."""
        task = self._tasks.get(conversation_id)
        if task is not None and not task.done():
            logger.info("Stop requested for conv %s", conversation_id)
            task.cancel()
            return True
        return False

    async def ask(self, text: str, conversation_id: int | None = None) -> str:
        """Run the agent and return the full reply (used by the TUI; auto-creates a conversation)."""
        async with SessionFactory() as session:
            if conversation_id is None:
                existing = await conversation_service.list_conversations(session)
                conv = existing[0] if existing else None
                conversation_id = conv["id"] if conv else (await conversation_service.create(session)).id
        collected: list[str] = []
        async for event in self.stream(conversation_id, text):
            if event["type"] == "token":
                collected.append(event["text"])
            elif event["type"] == "error":
                collected.append(event["message"])
        return "".join(collected) or NO_REPLY
