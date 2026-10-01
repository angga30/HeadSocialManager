"""LinkedIn publisher (STUB). Requires LinkedIn API OAuth 2.0 + a verified app."""

from headofsocial.domain.models import Asset, Post
from headofsocial.publishing.base import Publisher


class LinkedInPublisher(Publisher):
    async def publish(self, post: Post, asset: Asset | None) -> None:
        raise NotImplementedError(
            "LinkedIn publishing is not wired yet (Phase 4). "
            "Needs LinkedIn API: a developer app with r_liteprofile, r_emailaddress, "
            "w_member_social scopes, OAuth 2.0 flow, and the Share API (ugcPosts)."
        )