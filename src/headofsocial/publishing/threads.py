"""Threads publisher (STUB). Requires Meta Graph API for Threads (threads_basic, threads_content_publish)."""

from headofsocial.domain.models import Asset, Post
from headofsocial.publishing.base import Publisher


class ThreadsPublisher(Publisher):
    async def publish(self, post: Post, asset: Asset | None) -> None:
        raise NotImplementedError(
            "Threads publishing is not wired yet (Phase 4). "
            "Needs Meta Graph API: a Threads account linked to a Facebook App with "
            "threads_basic and threads_content_publish permissions."
        )