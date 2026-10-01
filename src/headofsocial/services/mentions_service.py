"""Mention support: search brands/channels/posts and resolve them into agent context."""

import re

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from headofsocial.domain.models import Brand, Channel, Post

_MENTION_RE = re.compile(r"@(brand|channel|post):(\d+)")


def parse_mentions(text: str) -> list[dict]:
    """Extract [{type,id}] mentions from raw composer text (mirrors the web parser)."""
    return [{"type": t, "id": int(i)} for t, i in _MENTION_RE.findall(text)]


async def search(session: AsyncSession, q: str = "", limit: int = 8) -> dict:
    """Return mention candidates (brands/channels/posts) matching a query string."""
    like = f"%{q.strip()}%"

    brand_stmt = select(Brand).order_by(Brand.name).limit(limit)
    channel_stmt = select(Channel).order_by(Channel.platform).limit(limit)
    post_stmt = select(Post).order_by(Post.id.desc()).limit(limit)
    if q.strip():
        brand_stmt = brand_stmt.where(Brand.name.ilike(like))
        channel_stmt = channel_stmt.where(
            or_(Channel.handle.ilike(like), Channel.platform.ilike(like))
        )
        post_stmt = post_stmt.where(or_(Post.pillar.ilike(like), Post.status.ilike(like)))

    brands = (await session.execute(brand_stmt)).scalars().all()
    channels = (await session.execute(channel_stmt)).scalars().all()
    posts = (await session.execute(post_stmt)).scalars().all()

    return {
        "brands": [{"id": b.id, "label": b.name, "type": str(b.type)} for b in brands],
        "channels": [
            {"id": c.id, "label": f"{c.platform} @{c.handle}", "platform": str(c.platform)}
            for c in channels
        ],
        "posts": [
            {"id": p.id, "label": f"#{p.id} {p.pillar or 'post'} ({p.status})", "status": str(p.status)}
            for p in posts
        ],
    }


async def build_context(session: AsyncSession, mentions: list[dict]) -> str:
    """Turn [{type,id}] mentions into a grounding text block for the agent."""
    if not mentions:
        return ""
    lines: list[str] = []
    for m in mentions:
        mtype, mid = str(m.get("type", "")).lower(), m.get("id")
        if mid is None:
            continue
        if mtype == "brand":
            b = await session.get(Brand, int(mid))
            if b:
                pillars = ", ".join(
                    (p.get("name") if isinstance(p, dict) else str(p))
                    for p in (b.content_pillars or [])
                )
                lines.append(
                    f'- Brand #{b.id} "{b.name}" ({b.type}, lang {b.language})'
                    + (f'; pillars: {pillars}' if pillars else "")
                    + (f'; positioning: {b.positioning_statement}' if b.positioning_statement else "")
                )
        elif mtype == "channel":
            c = await session.get(Channel, int(mid))
            if c:
                lines.append(f"- Channel #{c.id} {c.platform} @{c.handle} (brand {c.brand_id})")
        elif mtype == "post":
            p = await session.get(Post, int(mid))
            if p:
                lines.append(
                    f"- Post #{p.id} (brand {p.brand_id}, pillar {p.pillar or '-'}, "
                    f"status {p.status}, asset {p.asset_id or 'none'}, "
                    f"scheduled {p.scheduled_at.isoformat() if p.scheduled_at else '-'})"
                )
    if not lines:
        return ""
    return "Referensi yang disebut user (gunakan ini sebagai konteks):\n" + "\n".join(lines)