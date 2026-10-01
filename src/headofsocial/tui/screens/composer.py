"""Composer screen — chat with the root agent, streaming responses + live status."""

from time import monotonic

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, LoadingIndicator, Markdown, Static

from headofsocial.services import conversation_service
from headofsocial.services.chat_service import ChatService
from headofsocial.storage.db import SessionFactory
from headofsocial.tools._deps import ensure_db

INTRO = (
    "Halo! Saya Head of Social Media. Saya bisa: rekomendasi positioning, menyusun rencana "
    "bulanan, membuat konten per-channel, dan menjadwalkan publish. Mulai dengan membuat brand dulu."
)


class ComposerScreen(Screen):
    BINDINGS = [Binding("ctrl+l", "clear", "Clear")]

    def __init__(self, chat: ChatService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._chat = chat
        self._conversation_id: int | None = None
        self._buffer = ""
        self._last_paint = 0.0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield VerticalScroll(id="conversation", classes="conversation")
        yield Input(placeholder="Arahkan agent… contoh: 'buat rencana konten untuk brand saya'")
        yield Footer()

    async def on_mount(self) -> None:
        await ensure_db()
        convo = self.query_one("#conversation", VerticalScroll)

        # Resume the most recent conversation (with history) or start a fresh one.
        async with SessionFactory() as session:
            existing = await conversation_service.list_conversations(session)
            if existing:
                self._conversation_id = existing[0]["id"]
                history = await conversation_service.list_messages(session, self._conversation_id)
            else:
                self._conversation_id = (await conversation_service.create(session)).id
                history = []

        if history:
            for message in history:
                await convo.mount(self._bubble(message["role"], message["text"]))
        else:
            await convo.mount(self._bubble("assistant", INTRO))
        convo.scroll_end(animate=False)
        self.query_one(Input).focus()

    @work(exclusive=True)
    async def send_message(self, text: str) -> None:
        input_widget = self.query_one(Input)
        input_widget.disabled = True
        convo = self.query_one("#conversation", VerticalScroll)
        await convo.mount(self._bubble("user", text))
        convo.scroll_end(animate=False)

        status = Vertical(
            LoadingIndicator(classes="tiny-loader"),
            Static("berpikir…", classes="status-text"),
            classes="agent-status",
        )
        await convo.mount(status)
        status_text = status.query_one(Static)

        reply = Markdown("")
        await convo.mount(reply)
        convo.scroll_end(animate=False)

        self._buffer = ""
        self._last_paint = 0.0
        writing = False
        try:
            async for event in self._chat.stream(self._conversation_id, text):
                etype = event["type"]
                if etype == "status":
                    status_text.update("⏳ berpikir…")
                elif etype == "agent":
                    status_text.update(f"🤖 {event['name']}…")
                elif etype == "tool":
                    verb = "menjalankan" if event["status"] == "start" else "selesai"
                    status_text.update(f"🔧 {verb} {event['name']}…")
                elif etype == "token":
                    if not writing:
                        writing = True
                        status_text.update("✍️ menulis…")
                    self._buffer += event["text"]
                    now = monotonic()
                    if now - self._last_paint > 0.1:
                        self._last_paint = now
                        await reply.update(self._buffer)
                        convo.scroll_end(animate=False)
                elif etype == "error":
                    self._buffer = event["message"]
                elif etype == "done":
                    break
        finally:
            await reply.update(self._buffer or "_Agent tidak menghasilkan respons._")
            await status.remove()
            convo.scroll_end(animate=False)
            input_widget.disabled = False
            input_widget.focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        event.input.value = ""
        if event.value.strip():
            self.send_message(event.value.strip())

    def action_clear(self) -> None:
        self.query_one("#conversation", VerticalScroll).remove_children()

    @staticmethod
    def _bubble(role: str, text: str) -> Markdown:
        who = "🧑 kamu" if role == "user" else "🤖 agent"
        return Markdown(f"**{who}**\n\n{text}")
