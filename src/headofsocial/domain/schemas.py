"""Pydantic schemas for agent tool I/O, structured output, and future API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from headofsocial.domain.enums import ContentDepth, MediaType, Platform


# --- Positioning ---
class PositioningRecommendation(BaseModel):
    positioning_statement: str = Field(description="One crisp sentence: who you help and why you differ.")
    target_audience: list[str] = Field(description="Audience segments with pain points and goals.")
    differentiators: list[str] = Field(description="Why people pick you over alternatives.")
    voice_tone: str = Field(description="How the brand sounds: adjectives and do/don't rules.")
    content_pillars: list[dict] = Field(
        description="3-5 pillars, each {name: str, angle: str, example_angles: list[str]}."
    )


# --- Media spec / depth ---
class MediaSpecItem(BaseModel):
    media_type: MediaType
    prompt: str = Field(description="Detailed image/video generation prompt.")
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