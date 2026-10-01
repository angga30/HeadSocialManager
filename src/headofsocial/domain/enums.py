"""Enums shared across the domain."""

from enum import StrEnum


class BrandType(StrEnum):
    PERSONAL = "personal"
    BUSINESS = "business"
    PRODUCT = "product"


class Platform(StrEnum):
    INSTAGRAM = "instagram"
    THREADS = "threads"
    LINKEDIN = "linkedin"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    ARCHIVED = "archived"


class AssetType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    MIXED = "mixed"


class AssetStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"


class ContentDepth(StrEnum):
    """How much media a content asset carries."""

    TEXT = "text"  # 0 images, 0 videos
    VISUAL = "visual"  # 1 image
    CAROUSEL = "carousel"  # 2-5 images
    MOTION = "motion"  # 1 video
    SERIES = "series"  # 2 videos
    RICH = "rich"  # up to MAX images AND up to MAX videos


class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"


class PostStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class MediaProviderKind(StrEnum):
    MOCK = "mock"
    LITELLM = "litellm"


class BrandAssetKind(StrEnum):
    """Kinds of real brand assets a user can upload (M1)."""

    FACE_PHOTO = "face_photo"
    LOGO = "logo"
    LOGO_DARK = "logo_dark"
    PRODUCT_PHOTO = "product_photo"
    REFERENCE_STYLE = "reference_style"


class ResearchKind(StrEnum):
    """Categories of cached research notes (R1)."""

    TRENDS = "trends"
    COMPETITORS = "competitors"
    WEB = "web"