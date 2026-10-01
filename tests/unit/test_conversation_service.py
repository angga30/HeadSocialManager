"""Conversation persistence: create/list/messages/title/status/delete."""

from headofsocial.services import conversation_service as cs


async def test_create_sets_adk_session_and_default_title(session):
    conv = await cs.create(session)
    assert conv.id is not None
    assert conv.adk_session_id == f"conv-{conv.id}"
    assert conv.title == "Percakapan baru"
    assert conv.status == cs.STATUS_IDLE


async def test_title_auto_set_from_first_user_message(session):
    conv = await cs.create(session)
    await cs.add_message(session, conv.id, "user", "Buat rencana konten bulan ini untuk Kopi")
    listing = await cs.list_conversations(session)
    assert listing[0]["title"].startswith("Buat rencana konten")
    assert listing[0]["message_count"] == 1


async def test_messages_ordered_and_roles(session):
    conv = await cs.create(session)
    await cs.add_message(session, conv.id, "user", "halo")
    await cs.add_message(session, conv.id, "assistant", "hai")
    msgs = await cs.list_messages(session, conv.id)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert [m["text"] for m in msgs] == ["halo", "hai"]


async def test_status_and_stale_reset(session):
    conv = await cs.create(session)
    await cs.set_status(session, conv.id, cs.STATUS_PROCESSING)
    assert (await cs.list_conversations(session))[0]["status"] == cs.STATUS_PROCESSING
    reset = await cs.reset_stale_processing(session)
    assert reset == 1
    assert (await cs.list_conversations(session))[0]["status"] == cs.STATUS_IDLE


async def test_delete(session):
    conv = await cs.create(session)
    assert await cs.delete(session, conv.id) is True
    assert (await cs.list_conversations(session)) == []
    assert await cs.delete(session, conv.id) is False


async def test_last_user_message_and_retry_delete(session):
    conv = await cs.create(session)
    await cs.add_message(session, conv.id, "user", "pesan satu")
    await cs.add_message(session, conv.id, "assistant", "balasan")
    assert await cs.last_user_message(session, conv.id) == "pesan satu"

    # Retry drops the trailing assistant reply so it can be regenerated.
    assert await cs.delete_trailing_assistant(session, conv.id) is True
    assert [m["role"] for m in await cs.list_messages(session, conv.id)] == ["user"]
    # Nothing assistant trailing now → no-op.
    assert await cs.delete_trailing_assistant(session, conv.id) is False


async def test_last_user_message_empty(session):
    conv = await cs.create(session)
    assert await cs.last_user_message(session, conv.id) is None