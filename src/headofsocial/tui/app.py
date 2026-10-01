"""Head of Social Media Agent TUI entry point.

Usage: uv run python -m headofsocial.tui.app
"""

import contextlib

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import TabbedContent, TabPane

from headofsocial.logging_config import configure_logging
from headofsocial.services.chat_service import ChatService
from headofsocial.services.scheduler import PublishingScheduler
from headofsocial.tools._deps import ensure_db
from headofsocial.tui.screens.brands import BrandsScreen
from headofsocial.tui.screens.calendar import CalendarScreen
from headofsocial.tui.screens.composer import ComposerScreen

CSS = """
#brands-layout { height: 1fr; padding: 1; }
.screen-title { margin-bottom: 1; }
.conversation { height: 1fr; border: round $accent; padding: 1; }
.conversation Markdown { margin-bottom: 1; }
.agent-status { height: auto; }
.agent-status .tiny-loader { height: 1; width: 3; }
.agent-status .status-text { height: 1; color: $text-muted; }
"""


class HeadOfSocialApp(App):
    TITLE = "Head of Social Media Agent"
    CSS = CSS
    BINDINGS = [Binding("q", "quit", "Quit", priority=True)]

    def __init__(self) -> None:
        super().__init__()
        self._scheduler = PublishingScheduler()
        self._chat = ChatService()

    def compose(self) -> ComposeResult:
        with TabbedContent(initial="composer"):
            with TabPane("💬 Composer", id="composer"):
                yield ComposerScreen(self._chat)
            with TabPane("👤 Brands", id="brands"):
                yield BrandsScreen()
            with TabPane("📅 Calendar", id="calendar"):
                yield CalendarScreen()

    async def on_mount(self) -> None:
        await ensure_db()  # guarded & idempotent; also called by tools/screens
        self._scheduler.start()

    async def on_unmount(self) -> None:
        self._scheduler.stop()


def main() -> None:
    # TUI owns the terminal: log to file only, so scheduler/framework chatter doesn't
    # flash over the Textual alternate screen. See: tail -f data/logs/app.log
    configure_logging(console=False)
    app = HeadOfSocialApp()
    with contextlib.suppress(KeyboardInterrupt):
        app.run()


if __name__ == "__main__":
    main()