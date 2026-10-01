"""Mention parsing mirrors the web composer's @type:id tokens."""

from headofsocial.services.mentions_service import parse_mentions


def test_parse_mentions_extracts_tokens():
    text = "lihat @brand:3 dan @channel:12 bandingkan @post:7"
    assert parse_mentions(text) == [
        {"type": "brand", "id": 3},
        {"type": "channel", "id": 12},
        {"type": "post", "id": 7},
    ]


def test_parse_mentions_empty():
    assert parse_mentions("tanpa mention") == []


def test_parse_mentions_ignores_unknown_kinds():
    assert parse_mentions("@user:5 @brand:1") == [{"type": "brand", "id": 1}]
