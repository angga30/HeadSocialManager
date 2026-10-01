"""SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from headofsocial.domain.enums import (
    AssetStatus,
    AssetType,
    BrandAssetKind,
    BrandType,
    ContentDepth,
    PlanStatus,
    Platform,
    PostStatus,
)


class Base(DeclarativeBase):
    pass


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[BrandType] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(200), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="id")

    positioning_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_audience: Mapped[list | None] = mapped_column(JSON, nullable=True)
    differentiators: Mapped[list | None] = mapped_column(JSON, nullable=True)
    voice_tone: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_pillars: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Locked visual identity (palette, keywords, tone, render style) — grounding for media (M1).
    visual_style: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    channels: Mapped[list["Channel"]] = relationship(back_populates="brand", cascade="all, delete-orphan")
    plans: Mapped[list["Plan"]] = relationship(back_populates="brand", cascade="all, delete-orphan")
    assets: Mapped[list["Asset"]] = relationship(back_populates="brand", cascade="all, delete-orphan")
    posts: Mapped[list["Post"]] = relationship(back_populates="brand", cascade="all, delete-orphan")
    brand_assets: Mapped[list["BrandAsset"]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )


class BrandAsset(Base):
    """A real uploaded brand asset (face photo, logo, product photo, reference style) — M1."""

    __tablename__ = "brand_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    kind: Mapped[BrandAssetKind] = mapped_column(String(30))
    file_path: Mapped[str] = mapped_column(String(500))
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    brand: Mapped[Brand] = relationship(back_populates="brand_assets")


class ResearchNote(Base):
    """Cached web-research result so monthly planning doesn't re-query (R1)."""

    __tablename__ = "research_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    kind: Mapped[str] = mapped_column(String(30))
    query: Mapped[str] = mapped_column(Text)
    results: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    platform: Mapped[Platform] = mapped_column(String(20))
    handle: Mapped[str] = mapped_column(String(200))
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    style_overrides: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    credentials: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    brand: Mapped[Brand] = relationship(back_populates="channels")
    posts: Mapped[list["Post"]] = relationship(back_populates="channel", cascade="all, delete-orphan")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    period: Mapped[str] = mapped_column(String(7))  # "YYYY-MM"
    status: Mapped[PlanStatus] = mapped_column(String(20), default=PlanStatus.DRAFT)
    theme: Mapped[str | None] = mapped_column(Text, nullable=True)
    weekly_themes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    cadence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    content_mix: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    key_dates: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    brand: Mapped[Brand] = relationship(back_populates="plans")
    posts: Mapped[list["Post"]] = relationship(back_populates="plan")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    type: Mapped[AssetType] = mapped_column(String(20))
    status: Mapped[AssetStatus] = mapped_column(String(20), default=AssetStatus.DRAFT)
    depth: Mapped[ContentDepth | None] = mapped_column(String(20), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_spec: Mapped[list | None] = mapped_column(JSON, nullable=True)
    media_files: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    brand: Mapped[Brand] = relationship(back_populates="assets")
    posts: Mapped[list["Post"]] = relationship(back_populates="asset")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[PostStatus] = mapped_column(String(20), default=PostStatus.DRAFT)
    pillar: Mapped[str | None] = mapped_column(String(200), nullable=True)
    depth_hint: Mapped[str | None] = mapped_column(String(20), nullable=True)
    publish_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    brand: Mapped[Brand] = relationship(back_populates="posts")
    channel: Mapped[Channel] = relationship(back_populates="posts")
    asset: Mapped[Asset | None] = relationship(back_populates="posts")
    plan: Mapped[Plan | None] = relationship(back_populates="posts")
    metrics: Mapped[list["PostMetrics"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120), default="Percakapan baru")
    status: Mapped[str] = mapped_column(String(20), default="idle")  # idle|processing|error
    adk_session_id: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String(20))  # user|assistant
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class PostMetrics(Base):
    __tablename__ = "post_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"))
    platform: Mapped[str] = mapped_column(String(20))
    collected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    reach: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    follows: Mapped[int] = mapped_column(Integer, default=0)

    post: Mapped[Post] = relationship(back_populates="metrics")