"""Instagram publisher (STUB). Requires Meta Graph API app review + access tokens."""

from headofsocial.domain.models import Asset, Post
from headofsocial.publishing.base import Publisher


class InstagramPublisher(Publisher):
    async def publish(self, post: Post, asset: Asset | None) -> None:
        raise NotImplementedError(
            "Instagram publishing is not wired yet (Phase 4). "
            "Needs Meta Graph API: a Facebook App, instagram_basic + instagram_content_publish "
            "permissions, a long-lived page access token, and an Instagram Business account linked."
        )