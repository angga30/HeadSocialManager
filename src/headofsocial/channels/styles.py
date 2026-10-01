"""Per-platform style profiles used by the Content Agent to write channel-native copy."""

from dataclasses import dataclass, replace

from headofsocial.domain.enums import ContentDepth, Platform


@dataclass(frozen=True)
class ChannelStyle:
    platform: Platform
    label: str
    tone: str
    caption_limit_chars: int
    hashtag_range: tuple[int, int]
    emoji_level: str  # "none" | "light" | "moderate" | "heavy"
    suggested_depths: list[ContentDepth]
    guidance: str
    image_aspect: str = "1:1"
    image_size: str = "1080x1080"
    image_composition: str = "single clear subject, centered."

    def with_overrides(self, overrides: dict | None) -> "ChannelStyle":
        """Merge DB-style overrides onto this profile without mutating it."""
        if not overrides:
            return self
        return replace(
            self,
            tone=overrides.get("tone", self.tone),
            emoji_level=overrides.get("emoji_level", self.emoji_level),
        )


STYLES: dict[Platform, ChannelStyle] = {
    Platform.INSTAGRAM: ChannelStyle(
        platform=Platform.INSTAGRAM,
        label="Instagram",
        tone=(
            "visual-first and energizing; speak to how the audience feels. "
            "Lead with a strong visual anchor, keep the hook in the first line, "
            "and close with a clear call-to-action to the profile/bio."
        ),
        caption_limit_chars=2200,
        hashtag_range=(1, 5),
        emoji_level="moderate",
        suggested_depths=[ContentDepth.VISUAL, ContentDepth.CAROUSEL, ContentDepth.MOTION, ContentDepth.RICH],
        guidance=(
            "IG captions are shown under a photo/reel. Use 1-5 relevant hashtags, "
            "short punchy paragraphs, emojis in moderation, and end with a CTA "
            "(follow, save, see bio). Do not repeat the visual with words."
        ),
        image_aspect="4:5",
        image_size="1080x1350",
        image_composition="vertical portrait, single hero subject, generous headroom for the caption.",
    ),
    Platform.THREADS: ChannelStyle(
        platform=Platform.THREADS,
        label="Threads",
        tone=(
            "conversational, candid, and community-driven. Sound like a real person "
            "starting a discussion, not broadcasting."
        ),
        caption_limit_chars=500,
        hashtag_range=(0, 2),
        emoji_level="light",
        suggested_depths=[ContentDepth.TEXT, ContentDepth.VISUAL],
        guidance=(
            "Threads rewards authentic, short-form takes. Open with a hook, share a "
            "point of view, and invite replies. Minimal or no hashtags. Avoid "
            "polished marketing language."
        ),
        image_aspect="1:1",
        image_size="1080x1080",
        image_composition="square, casual and immediate, subject slightly off-center.",
    ),
    Platform.LINKEDIN: ChannelStyle(
        platform=Platform.LINKEDIN,
        label="LinkedIn",
        tone=(
            "professional but human; thought-leadership perspective. Share insight "
            "and practical takeaway so readers get value and want to connect."
        ),
        caption_limit_chars=3000,
        hashtag_range=(0, 3),
        emoji_level="light",
        suggested_depths=[ContentDepth.TEXT, ContentDepth.VISUAL, ContentDepth.MOTION],
        guidance=(
            "LinkedIn favors longer-form with line breaks for scannability. Open with "
            "the key idea in the first 2 lines (most read before 'see more'). Use 0-3 "
            "hashtags, minimal or no emoji, and end with a question or stance."
        ),
        image_aspect="1.91:1",
        image_size="1200x627",
        image_composition="landscape, subject offset to one side, clean negative space for a headline.",
    ),
}


def get_style(platform: Platform, overrides: dict | None = None) -> ChannelStyle:
    style = STYLES.get(platform, STYLES[Platform.INSTAGRAM])
    return style.with_overrides(overrides)


def style_instruction_block(style: ChannelStyle, language: str) -> str:
    """Render a style profile as an instruction block the Content Agent can inject."""
    lo, hi = style.hashtag_range
    return (
        f"CHANNEL: {style.label} (language: {language})\n"
        f"TONE: {style.tone}\n"
        f"CAPTION LIMIT: {style.caption_limit_chars} characters\n"
        f"HASHTAGS: {lo}-{hi} relevant\n"
        f"EMOJI LEVEL: {style.emoji_level}\n"
        f"IMAGE FORMAT: {style.image_aspect} ({style.image_size})\n"
        f"PREFERRED DEPTH: {', '.join(d.value for d in style.suggested_depths)}\n"
        f"GUIDANCE: {style.guidance}"
    )