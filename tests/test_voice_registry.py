import pytest

from Core.voice_registry import VoiceRegistry


def make_registry(n=2):
    voices = [("id-%d" % i, "Voice %d" % i) for i in range(1, n + 1)]
    return VoiceRegistry(enabled=voices), voices


def test_claim_assigns_first_free_voice():
    reg, voices = make_registry(2)

    result = reg.claim()

    assert result["id"] == "id-1"
    assert result["shared"] is False
    assert result["reused"] is False


def test_claim_specific_voice_by_name_or_id():
    reg, _ = make_registry(2)

    by_name = reg.claim(agent="a", voice="Voice 2")
    assert by_name["id"] == "id-2"

    reg2, _ = make_registry(2)
    by_id = reg2.claim(agent="a", voice="id-2")
    assert by_id["id"] == "id-2"


def test_claim_until_exhausted_then_requires_agent():
    reg, _ = make_registry(2)

    reg.claim(agent="alpha")
    reg.claim(agent="beta")

    # All voices taken: an anonymous claim must fail with guidance.
    with pytest.raises(ValueError) as exc:
        reg.claim()
    assert "agent" in str(exc.value).lower()


def test_reuse_with_agent_succeeds_and_is_shared():
    reg, _ = make_registry(2)
    reg.claim(agent="alpha")
    reg.claim(agent="beta")

    result = reg.claim(agent="gamma")

    assert result["reused"] is True
    assert result["shared"] is True
    assert result["id"] in ("id-1", "id-2")


def test_claim_is_idempotent_for_same_agent():
    reg, _ = make_registry(2)

    first = reg.claim(agent="alpha")
    again = reg.claim(agent="alpha")

    assert first["id"] == again["id"]
    # Only one voice consumed, so a second distinct agent still gets a free one.
    other = reg.claim(agent="beta")
    assert other["id"] != first["id"]


def test_requesting_a_taken_voice_while_others_free_raises():
    reg, _ = make_registry(2)
    reg.claim(agent="alpha", voice="id-1")

    with pytest.raises(ValueError):
        reg.claim(agent="beta", voice="id-1")


def test_unknown_voice_raises():
    reg, _ = make_registry(2)

    with pytest.raises(ValueError):
        reg.claim(voice="nope")


def test_no_enabled_voices_raises():
    reg = VoiceRegistry(enabled=[])

    with pytest.raises(ValueError):
        reg.claim()


def test_set_enabled_drops_claims_for_disabled_voices():
    reg, _ = make_registry(2)
    reg.claim(agent="alpha", voice="id-1")

    reg.set_enabled([("id-2", "Voice 2")])

    assert reg.voice_for("alpha") is None
    status = reg.status()
    assert [s["id"] for s in status] == ["id-2"]


def test_voice_for_and_release():
    reg, _ = make_registry(2)
    claimed = reg.claim(agent="alpha")

    assert reg.voice_for("alpha") == claimed["id"]

    released = reg.release("alpha")
    assert released == claimed["id"]
    assert reg.voice_for("alpha") is None


def test_status_reports_claimers():
    reg, _ = make_registry(1)
    reg.claim(agent="alpha")
    reg.claim(agent="beta")  # shares the only voice

    status = reg.status()
    assert status[0]["claimed_by"] == ["alpha", "beta"]


def test_agents_avoid_the_users_reserved_voice():
    reg, _ = make_registry(2)
    reg.set_user_voice("id-1")  # user reserves the first voice

    result = reg.claim(agent="agent-one")

    assert result["id"] == "id-2"  # agent takes the non-user voice


def test_reuse_avoids_user_voice_and_shares_agent_voice():
    reg, _ = make_registry(2)
    reg.set_user_voice("id-1")
    reg.claim(agent="agent-one")  # takes id-2 (only free non-user voice)

    result = reg.claim(agent="agent-two")  # exhausted -> reuse

    assert result["id"] == "id-2"  # never the user's id-1
    assert result["reused"] is True
    assert result["shared"] is True


def test_single_total_voice_is_shared_with_user():
    reg, _ = make_registry(1)
    reg.set_user_voice("id-1")  # the only voice is the user's

    first = reg.claim(agent="agent-one")
    second = reg.claim(agent="agent-two")

    # Only one voice total, so agents do use the user's voice (and share it).
    assert first["id"] == "id-1"
    assert second["id"] == "id-1"
    assert second["shared"] is True


def test_requesting_the_user_voice_is_rejected_when_others_free():
    reg, _ = make_registry(2)
    reg.set_user_voice("id-1")

    with pytest.raises(ValueError):
        reg.claim(agent="agent-one", voice="id-1")


def test_status_shows_user_reservation():
    reg, _ = make_registry(2)
    reg.set_user_voice("id-1")

    status = {s["id"]: s["claimed_by"] for s in reg.status()}
    assert status["id-1"] == ["user"]
    assert status["id-2"] == []


def test_set_enabled_clears_disabled_user_voice():
    reg, _ = make_registry(2)
    reg.set_user_voice("id-1")

    reg.set_enabled([("id-2", "Voice 2")])

    # id-1 no longer enabled, so it is no longer reserved; agent gets id-2 shared.
    status = {s["id"]: s["claimed_by"] for s in reg.status()}
    assert "id-1" not in status


def test_resolve_for_speak_requires_reservation_with_multiple_voices():
    reg, _ = make_registry(2)

    with pytest.raises(ValueError) as exc:
        reg.resolve_for_speak()
    assert "claim_voice" in str(exc.value)


def test_resolve_for_speak_requires_claim_for_unknown_agent():
    reg, _ = make_registry(2)

    with pytest.raises(ValueError) as exc:
        reg.resolve_for_speak(agent="agent-one")
    assert "claim_voice" in str(exc.value)


def test_resolve_for_speak_returns_claimed_voice():
    reg, _ = make_registry(2)
    claimed = reg.claim(agent="agent-one")

    assert reg.resolve_for_speak(agent="agent-one") == claimed["id"]


def test_resolve_for_speak_honors_explicit_voice():
    reg, _ = make_registry(2)

    assert reg.resolve_for_speak(voice="Voice 2") == "id-2"


def test_resolve_for_speak_rejects_unknown_explicit_voice():
    reg, _ = make_registry(2)

    with pytest.raises(ValueError):
        reg.resolve_for_speak(voice="nope")


def test_resolve_for_speak_uses_sole_voice_without_reservation():
    reg, _ = make_registry(1)

    assert reg.resolve_for_speak() == "id-1"
    assert reg.resolve_for_speak(agent="agent-one") == "id-1"


def test_resolve_for_speak_returns_none_when_no_voices_enabled():
    reg = VoiceRegistry(enabled=[])

    assert reg.resolve_for_speak() is None
