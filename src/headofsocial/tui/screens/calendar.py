"""Calendar screen — list post slots across channels with status."""

from textual import work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Header, Label, Static

from headofsocial.services import brand_service
from headofsocial.storage import repos
from headofsocial.storage.db import SessionFactory


class CalendarScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label("📅 Jadwal posting", classes="screen-title")
        yield Static(id="cal-summary")
        yield DataTable(id="cal-table", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one("#cal-table", DataTable)
        table.add_columns("ID", "Channel", "Pillar", "Depth", "Scheduled", "Status")
        self.refresh_calendar()

    @work
    async def refresh_calendar(self) -> None:
        from headofsocial.tools._deps import ensure_db

        await ensure_db()
        async with SessionFactory() as session:
            brands = await brand_service.list_brands(session)
            posts, plans = [], []
            for b in brands:
                posts += await repos.list_posts(session, b.id)
                plans += await repos.list_plans(session, b.id)
            by_status: dict[str, int] = {}
            for p in posts:
                by_status[p.status] = by_status.get(p.status, 0) + 1
        summary = ", ".join(f"{k}: {v}" for k, v in sorted(by_status.items())) or "belum ada post"
        per_plan = "; ".join(f"{pl.period} ({pl.theme or '-'})" for pl in plans[:3]) or "-"
        self.query_one("#cal-summary", Static).update(
            f"[b]Status:[/b] {summary}   [b]Rencana bulan aktif:[/b] {per_plan}"
        )
        table = self.query_one("#cal-table", DataTable)
        table.clear()
        for p in sorted(posts, key=lambda x: (x.scheduled_at or x.created_at), reverse=True):
            table.add_row(
                str(p.id),
                p.channel.platform if p.channel else "?",
                p.pillar or "—",
                p.depth_hint or "—",
                p.scheduled_at.strftime("%Y-%m-%d %H:%M") if p.scheduled_at else "—",
                str(p.status),
            )