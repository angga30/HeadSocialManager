"""Media budget enforcement — max 5 images / 2 videos per asset."""

import pytest

from headofsocial.domain.enums import ContentDepth, MediaType
from headofsocial.domain.schemas import MediaSpecItem
from headofsocial.services import media_service
from headofsocial.services.media_service import BudgetExceededError


def _spec(images: int, videos: int) -> list[MediaSpecItem]:
    items = [
        MediaSpecItem(media_type=MediaType.IMAGE, creative_brief="img", position=i)
        for i in range(images)
    ]
    items += [
        MediaSpecItem(media_type=MediaType.VIDEO, creative_brief="vid", position=i)
        for i in range(videos)
    ]
    return items


@pytest.mark.parametrize(
    "images,videos,ok",
    [
        (0, 0, True),
        (1, 0, True),
        (5, 0, True),
        (6, 0, False),
        (0, 2, True),
        (0, 3, False),
        (5, 2, True),
        (6, 2, False),
        (5, 3, False),
    ],
)
def test_media_budget_caps(images, videos, ok):
    items = _spec(images, videos)
    if ok:
        media_service.check_media_budget(items)
    else:
        with pytest.raises(BudgetExceededError):
            media_service.check_media_budget(items)


def test_content_type_for_depth():
    assert media_service.content_type_for_depth(ContentDepth.TEXT).value == "text"
    assert media_service.content_type_for_depth(ContentDepth.CAROUSEL).value == "image"
    assert media_service.content_type_for_depth(ContentDepth.SERIES).value == "video"
    assert media_service.content_type_for_depth(ContentDepth.RICH).value == "mixed"