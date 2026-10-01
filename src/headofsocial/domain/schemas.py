"""Pydantic schemas for agent tool I/O, structured output, and future API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from headofsocial.domain.enums import ContentDepth, MediaType, Platform

# --- Visual identity (M1) ---
_HEX_RE = r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$"


class LogoOverlay(BaseModel):
    """Deterministic logo compositing config (M5)."""

    position: Literal["top-left", "top-right", "bottom-left", "bottom-right"] = "bottom-right"
    opacity: float = Field(default=0.85, ge=0.0, le=1.0)
    margin: int = Field(default=24, ge=0, description="Pixel margin from the chosen corner.")


class VisualStyle(BaseModel):
    """Locked, structured visual identity. Rendered verbatim into every media prompt (M1/M2)."""

    palette: list[str] = Field(default_factory=list, description="2-4 brand hex colors.")
    style_keywords: list[str] = Field(default_factory=list)
    image_tone: str = Field(default="", description="bright | dark | muted | vibrant.")
    typography_hint: str = Field(default="")
    avoid: list[str] = Field(default_factory=list)
    render_style: str = Field(default="", description="photography | flat-illustration | 3d | mixed.")
    logo_overlay: LogoOverlay | None = None

    @field_validator("palette")
    @classmethod
    def _palette_is_hex(cls, values: list[str]) -> list[str]:
        import re

        for value in values:
            if not re.match(_HEX_RE, value):
                raise ValueError(f"palette color must be hex like #1A1A2E (got {value!r})")
        return values


# --- Positioning ---
class PositioningRecommendation(BaseModel):
    positioning_statement: str = Field(description="One crisp sentence: who you help and why you differ.")
    target_audience: list[str] = Field(description="Audience segments with pain points and goals.")
    differentiators: list[str] = Field(description="Why people pick you over alternatives.")
    voice_tone: str = Field(description="How the brand sounds: adjectives and do/don't rules.")
    content_pillars: list[dict] = Field(
        description="3-5 pillars, each {name: str, angle: str, example_angles: list[str]}."
    )
    visual_style: VisualStyle | None = Field(
        default=None, description="Locked visual identity (palette, keywords, tone, render style)."
    )


# --- Media spec / depth ---
class MediaSpecItem(BaseModel):
    media_type: MediaType
    creative_brief: str = Field(
        description="Creative-only brief (subject/scene/mood). Visual style lives in the brand."
    )
    position: int = Field(default=0, description="Order within the asset (0-based).")


class MediaSpec(BaseModel):
    items: list[MediaSpecItem] = Field(default_factory=list, description="Planned media items.")


class ContentDraft(BaseModel):
    depth: ContentDepth = Field(description="How much media this content carries.")
    body: str = Field(description="Channel-native copy text.")
    headline: str = Field(default="", description="Short headline/hook, used for history summaries.")
    media_spec: list[MediaSpecItem] = Field(
        default_factory=list, description="Image/video items to generate."
    )


# --- Monthly plan ---
class WeeklyTheme(BaseModel):
    week: int
    focus: str
    goal: str = ""


class MonthlyPlan(BaseModel):
    period: str = Field(description="YYYY-MM")
    theme: str = Field(description="One north-star narrative for the month.")
    weekly_themes: list[WeeklyTheme] = Field(default_factory=list)
    cadence: dict[str, int] = Field(default_factory=dict, description="posts/week per channel.")
    content_mix: dict = Field(
        default_factory=dict,
        description="pillar % and format % (text/image/video/carousel/series).",
    )
    key_dates: list[dict] = Field(
        default_factory=list, description="Campaigns/holidays/launches to anchor around."
    )


# --- Insights ---
class PostInsight(BaseModel):
    post_id: int
    channel: str
    depth: str = ""
    pillar: str = ""
    headline: str = ""
    engagement_rate: float = 0.0


class EngagementInsights(BaseModel):
    top_posts: list[PostInsight] = Field(default_factory=list)
    bottom_posts: list[PostInsight] = Field(default_factory=list)
    best_times: list[dict] = Field(default_factory=list, description="Best day/hour slots.")
    pillar_performance: list[dict] = Field(default_factory=list)
    format_performance: list[dict] = Field(default_factory=list)
    channel_notes: list[dict] = Field(default_factory=list)


# --- Tool I/O helpers ---
class ChannelInput(BaseModel):
    platform: Platform
    handle: str
    language: str | None = None
    style_overrides: dict | None = None


class PostSlot(BaseModel):
    post_id: int
    channel: str
    pillar: str = ""
    scheduled_at: datetime | None = None
    depth_hint: Literal["text", "visual", "carousel", "motion", "series", "rich"] | None = None