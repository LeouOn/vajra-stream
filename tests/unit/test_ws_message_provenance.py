"""Guard: every WebSocket message type is classified for provenance.

The honest instrument (docs/DEVELOPMENT_ROADMAP.md, Phase 2): every displayed
value is record, computed, draw or decorative. WebSocket messages get their
labels at the connection manager's single choke point from
``backend/websocket/message_provenance.py``. This test fails when the backend
emits a type that table does not classify, so a new message cannot ship
unlabeled; and it checks that the labels really reach the wire.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.websocket.message_provenance import WS_MESSAGE_PROVENANCE, annotate
from core.provenance import PROVENANCE_KINDS, provenance_map, validate_provenance, with_provenance

REPO_ROOT = Path(__file__).resolve().parents[2]


def _emitted_ws_types() -> set[str]:
    spec = importlib.util.spec_from_file_location("audit_ws_contract", REPO_ROOT / "scripts" / "audit_ws_contract.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.extract_backend_types()


@pytest.mark.unit
def test_every_emitted_ws_type_is_classified():
    emitted = _emitted_ws_types()
    unclassified = sorted(emitted - set(WS_MESSAGE_PROVENANCE))
    assert not unclassified, (
        "WebSocket message types without a provenance entry. Add each to WS_MESSAGE_PROVENANCE in "
        f"backend/websocket/message_provenance.py (a {{field: kind}} map, or a reason string): {unclassified}"
    )


@pytest.mark.unit
def test_no_stale_ws_entries():
    stale = sorted(set(WS_MESSAGE_PROVENANCE) - _emitted_ws_types())
    assert not stale, f"Remove provenance entries for message types the backend no longer emits: {stale}"


@pytest.mark.unit
def test_every_ws_entry_is_a_valid_map_or_a_reason():
    for msg_type, entry in WS_MESSAGE_PROVENANCE.items():
        if isinstance(entry, str):
            assert len(entry) > 10, f"{msg_type}: reason must explain why no labels are attached"
        else:
            assert entry, f"{msg_type}: an empty map labels nothing; use a reason string instead"
            assert set(entry.values()) <= PROVENANCE_KINDS, msg_type


@pytest.mark.unit
def test_rng_reading_is_always_a_draw():
    entry = WS_MESSAGE_PROVENANCE["RNG_READING"]
    assert not isinstance(entry, str)
    assert set(entry.values()) == {"draw"}


@pytest.mark.unit
def test_annotate_labels_data_and_keeps_producer_labels():
    message = {"type": "RNG_READING", "data": {"coherence": 0.4, "provenance": {"extra": "draw"}}}
    out = annotate(message)
    assert out["data"]["provenance"]["coherence"] == "draw"
    assert out["data"]["provenance"]["extra"] == "draw"
    # The caller's dict is untouched.
    assert message["data"]["provenance"] == {"extra": "draw"}


@pytest.mark.unit
def test_annotate_labels_flat_messages_at_top_level():
    out = annotate({"type": "realtime_data", "audio_spectrum": [0.1], "active_sessions": {}})
    assert out["provenance"]["audio_spectrum"] == "computed"
    assert out["provenance"]["active_sessions"] == "record"


@pytest.mark.unit
def test_annotate_leaves_value_free_and_unknown_messages_alone():
    ping = {"type": "ping", "timestamp": 1.0}
    assert annotate(ping) is ping
    op = {"type": "operation_update", "data": {"id": "op_1", "provenance": {"seed": "draw"}}}
    assert annotate(op) is op
    assert annotate("not a dict") == "not a dict"


class _FakeSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, message: dict) -> None:
        self.sent.append(message)


@pytest.mark.unit
def test_broadcast_sends_labeled_messages():
    from backend.websocket.connection_manager import StableConnectionManagerV2

    manager = StableConnectionManagerV2()
    sock = _FakeSocket()
    manager.active_connections["c1"] = sock  # type: ignore[assignment]
    asyncio.run(manager.broadcast({"type": "SCALAR_WAVE_ACTIVE", "data": {"active": True, "session_count": 2}}))
    asyncio.run(manager.send_personal_message({"type": "PLANETARY_HOUR_SHIFT", "data": {"hour": "Venus"}}, "c1"))
    assert sock.sent[0]["data"]["provenance"] == {"session_count": "record"}
    assert sock.sent[1]["data"]["provenance"]["hour"] == "computed"


@pytest.mark.unit
def test_provenance_helpers_validate_kinds():
    assert provenance_map(moon="computed") == {"moon": "computed"}
    with pytest.raises(ValueError):
        validate_provenance({"gv": "measured"})
    payload = {"provenance": {"rate_values": "record"}}
    with_provenance(payload, {"rate_values": "computed", "frequencies": "computed"})
    assert payload["provenance"] == {"rate_values": "record", "frequencies": "computed"}
