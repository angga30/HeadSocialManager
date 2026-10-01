"""Brands screen — create brands, list them, and inspect positioning."""

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, Input, Label, Select, Static

from headofsocial.services import brand_service
from headofsocial.storage.db import SessionFactory

_TYPES = [("Personal", "personal"), ("Business", "business"), ("Product", "product")]


class BrandsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(
            Vertical(
                Label("👤 Buat brand baru", classes="screen-title"),
                Input(placeholder="Nama brand", id="brand-name"),
                Input(placeholder="Deskripsi singkat", id="brand-desc"),
                Select(_TYPES, value="business", id="brand-type"),
                Input(placeholder="Bahasa konten (id/en)", value="id", id="brand-lang"),
                Button("Simpan brand", id="brand-save", variant="primary"),
                Static(id="brand-msg"),
            ),
            Vertical(
                Label("📇 Brand terdaftar", classes="screen-title"),
                DataTable(id="brand-table", cursor_type="row"),
            ),
            id="brands-layout",
        )

    def on_mount(self) -> None:
        table = self.query_one("#brand-table", DataTable)
        table.add_columns("ID", "Nama", "Tipe", "Lang", "Positioning")
        self.refresh_brands()

    @work
    async def refresh_brands(self) -> None:
        from headofsocial.tools._deps import ensure_db

        await ensure_db()
        async with SessionFactory() as session:
            brands = await brand_service.list_brands(session)
        table = self.query_one("#brand-table", DataTable)
        table.clear()
        for b in brands:
            table.add_row(
                str(b.id), b.name, str(b.type), b.language,
                "✓" if b.positioning_statement else "—",
            )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "brand-save":
            return
        name = self.query_one("#brand-name", Input).value.strip()
        desc = self.query_one("#brand-desc", Input).value.strip()
        type_ = self.query_one("#brand-type", Select).value
        lang = self.query_one("#brand-lang", Input).value.strip() or "id"
        msg = self.query_one("#brand-msg", Static)
        if not name:
            msg.update("⚠️ Nama brand wajib diisi.")
            return
        async with SessionFactory() as session:
            await brand_service.create_brand(session, name, type_, desc or None, language=lang)
        msg.update(f"✅ Brand '{name}' dibuat.")
        self.query_one("#brand-name", Input).value = ""
        self.refresh_brands()