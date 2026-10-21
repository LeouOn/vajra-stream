"""CD-6: a frontend-to-backend contract test.

Nothing in the suite compared what the frontend SENDS and READS with what the
backend SERVES. The W0 frontend/backend contract audit
(``docs/notes/audit-frontend-backend-contract-2026-10-08.md``) found a dozen
drifts by hand across 349 backend routes and 191 frontend calls, and three of
them shipped as user-visible breakage: the Dharma story search always returned
nothing, the practice counter reset to zero every two seconds, and the
"Interpret" button failed with a 500.

This test is the systematic guard against that class. It is DATA-DRIVEN: the
calls the frontend makes are listed in ``frontend_calls.json``, and each one is
checked against

  * the live OpenAPI schema, loaded from the FastAPI app OBJECT
    (``app.openapi()``) -- no server is started and the lifespan never runs;
  * the frontend source, parsed as TEXT -- the frontend is never built;
  * and, for the three contracts that were BROKEN and are now fixed, the
    actual response of the endpoint.

A KNOWN-UNFIXED drift is recorded in the table with its ticket id and runs as
a STRICT xfail naming that ticket. When the fix lands the test XPASSes, and
because the xfail is strict that becomes a FAILURE, which is the signal to
delete the ticket marker. So the suite goes green one fix at a time, and a
regression that re-breaks a fixed contract fails immediately.

THE TABLE IS DATA A PERSON EXTENDS. See the ``_how_to_extend`` key in
``frontend_calls.json`` for the fields and their meaning, and the module
docstring of that file for the reasoning behind them.

Offline, deterministic and fast: no network, no LLM (the one chat route is
called with a fake), no audio, no server, and the live database is never
opened -- ``test_the_live_database_is_never_opened`` asserts it.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TABLE_PATH = PROJECT_ROOT / "tests" / "contract" / "frontend_calls.json"
FRONTEND_ROOT = PROJECT_ROOT / "frontend" / "src"
LIVE_DB_PATH = PROJECT_ROOT / "vajra_stream.db"
API_PREFIX = "/api/v1"


def _load_table() -> dict[str, Any]:
    data = json.loads(TABLE_PATH.read_text(encoding="utf-8"))
    calls = data.get("calls")
    if not isinstance(calls, list) or not calls:
        pytest.fail(f"{TABLE_PATH} has no 'calls' list")
    return data


_TABLE = _load_table()
_CALLS: list[dict[str, Any]] = _TABLE["calls"]


def _case_params() -> list[Any]:
    """One param per table entry; unfixed drift carries a strict xfail."""
    params = []
    for call in _CALLS:
        marks = []
        ticket = call.get("ticket")
        if ticket:
            marks.append(
                pytest.mark.xfail(
                    strict=True,
                    reason=(
                        f"known frontend/backend drift, {ticket}. The contract for "
                        f"{call['name']} does not hold yet. When the fix lands this test "
                        f"XPASSes, and a strict xfail turns that into a failure asking for "
                        f"the ticket marker to be deleted from frontend_calls.json."
                    ),
                )
            )
        params.append(pytest.param(call, id=call["name"], marks=marks))
    return params


@pytest.fixture(scope="session")
def openapi_schema() -> dict[str, Any]:
    """The live OpenAPI schema, from the app object. No server, no lifespan."""
    from backend.app.main import app

    return app.openapi()


@pytest.fixture(scope="session")
def client() -> Any:
    """A TestClient that never runs the lifespan.

    Entering ``TestClient(app)`` as a context manager runs the application's
    startup and shutdown, which starts background services. Used directly,
    the lifespan does not run, so no service is started and no startup side
    effect can fire.
    """
    from fastapi.testclient import TestClient

    from backend.app.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _declared_properties(schema: dict[str, Any], ref: str | None) -> list[str] | None:
    """The property names of a ``$ref``'d component schema, or None."""
    if not ref:
        return None
    components = schema.get("components", {}).get("schemas", {})
    resolved = components.get(ref.split("/")[-1])
    if not isinstance(resolved, dict):
        return None
    properties = resolved.get("properties")
    return sorted(properties) if isinstance(properties, dict) else None


def _request_body_properties(schema: dict[str, Any], operation: dict[str, Any]) -> list[str] | None:
    """The declared top-level body keys of an operation, or None if it declares none."""
    body = operation.get("requestBody")
    if not body:
        return None
    json_schema = body.get("content", {}).get("application/json", {}).get("schema", {})
    if "$ref" in json_schema:
        return _declared_properties(schema, json_schema["$ref"])
    properties = json_schema.get("properties")
    return sorted(properties) if isinstance(properties, dict) else None


def _response_properties(schema: dict[str, Any], operation: dict[str, Any]) -> list[str] | None:
    """The declared response keys of an operation, or None if it declares none.

    A route that returns a plain dict declares no response model, which is the
    common case in this project; the table's ``known_response_keys`` covers
    those, and the fixed contracts are additionally checked against the real
    response by the tests further down.
    """
    responses = operation.get("responses", {})
    for status in sorted(responses):
        if not status.startswith("2"):
            continue
        json_schema = responses[status].get("content", {}).get("application/json", {}).get("schema", {})
        if "$ref" in json_schema:
            return _declared_properties(schema, json_schema["$ref"])
        properties = json_schema.get("properties")
        if isinstance(properties, dict):
            return sorted(properties)
    return None


def _normalise_path(path: str) -> str:
    """Replace path parameters with a placeholder.

    The frontend writes template literals (``/practices/${id}/status``) while
    the OpenAPI schema spells the parameter out (``/practices/{practice_id}/status``).
    The NAMES differ but the route is the same, so both sides are normalised
    before they are compared. The template form is substituted FIRST: a plain
    ``\\{[^}]+\\}`` would match the braces of ``${id}`` and leave the dollar
    sign behind.
    """
    return re.sub(r"\{[^}]+\}", "{}", re.sub(r"\$\{[^}]+\}", "{}", path))


def _frontend_source(call: dict[str, Any]) -> str:
    """The frontend file for an entry, as TEXT. The frontend is never built."""
    source = PROJECT_ROOT / call["frontend_source"]
    if not source.exists():
        pytest.skip(f"frontend source not present: {call['frontend_source']}")
    return source.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# the contract itself
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("call", _case_params())
def test_frontend_contract_holds(call: dict[str, Any], openapi_schema: dict[str, Any]) -> None:
    """Every audited frontend call must match what the backend actually serves.

    Checks, in order:
      1. the frontend still contains the call (the marker must still be there);
      2. the backend serves that method and path;
      3. the frontend reaches it through ``apiUrl()`` -- a raw fetch bypasses
         the dev proxy and the ``/api/v1`` prefix -- and the path it resolves
         to is the path the backend serves;
      4. every response key the frontend reads is present, in the declared
         response model where there is one, else in the table's known-good list;
      5. every body key the frontend sends is DECLARED by the request model --
         a key the model does not declare is silently dropped, which is exactly
         the "silent drop" class of drift.
    """
    problems: list[str] = []
    method = call["method"].lower()
    api_path = call["api_path"]
    frontend_path = call["frontend_path"]

    # 1. the frontend still makes this call
    text = _frontend_source(call)
    marker = call["frontend_marker"]
    if marker not in text:
        problems.append(
            f"the frontend no longer contains {marker!r} in {call['frontend_source']} -- "
            f"the call was renamed or moved, so this table entry is stale"
        )

    # 2. the backend serves it
    operations = openapi_schema["paths"].get(api_path)
    if operations is None:
        problems.append(f"the backend does not serve {api_path} at all")
    elif method not in operations:
        problems.append(
            f"the backend serves {api_path} but not with method {call['method'].upper()} "
            f"(it has {sorted(operations)})"
        )

    # 3. the frontend reaches it the way the backend expects
    if not call.get("uses_api_url", True):
        problems.append(
            f"the frontend fetches {frontend_path!r} directly instead of through apiUrl(), so it "
            f"bypasses the /api dev proxy and never gets the /api/v1 prefix"
        )
    resolved = frontend_path if frontend_path.startswith(API_PREFIX) else API_PREFIX + frontend_path
    if _normalise_path(resolved) != _normalise_path(api_path):
        problems.append(
            f"the frontend path {frontend_path!r} resolves to {resolved!r}, but the backend route "
            f"is {api_path!r} -- the request would be redirected or 404"
        )

    # 4. the response keys the frontend reads
    if operations is not None and method in operations:
        operation = operations[method]
        declared = _response_properties(openapi_schema, operation)
        if declared is not None:
            for key in call.get("response_keys", []):
                if key not in declared:
                    problems.append(
                        f"the frontend reads {key!r} from {api_path} but the declared response "
                        f"model has no such key (it has {declared})"
                    )
        else:
            known = call.get("known_response_keys", [])
            for key in call.get("response_keys", []):
                if key not in known:
                    problems.append(
                        f"the frontend reads {key!r} from {api_path}, which returns a plain dict, "
                        f"and the known-good key list does not have it (it has {known})"
                    )

        # 5. the body keys the frontend sends
        body_properties = _request_body_properties(openapi_schema, operation)
        if body_properties is not None:
            for key in call.get("payload_keys", []):
                if key not in body_properties:
                    problems.append(
                        f"the frontend sends {key!r} to {api_path} but the request model does not "
                        f"declare it, so the value is silently dropped (the model has "
                        f"{body_properties})"
                    )

    assert not problems, (
        f"frontend/backend contract drift for {call['name']} "
        f"({call['method'].upper()} {api_path}):\n" + "\n".join(f"  - {p}" for p in problems)
    )


# ---------------------------------------------------------------------------
# the three contracts that were BROKEN and are now fixed
# ---------------------------------------------------------------------------
#
# The checks above are against the SCHEMA, which cannot express "the backend
# returns a key" for a route that returns a plain dict, nor "the backend
# accepts a nested key" for a free-form object. So the three corrected
# contracts are checked against the real response.


@pytest.mark.unit
def test_story_search_returns_the_key_the_frontend_reads(client: Any) -> None:
    """CD-3: the Command Center reads ``data.stories`` (commandStore.ts).

    The backend used to return the list under ``results`` only, so the search
    silently returned nothing.
    """
    response = client.get("/api/v1/stories/search", params={"q": "arrow"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert "stories" in body, f"the frontend reads data.stories; the body has {sorted(body)}"
    assert isinstance(body["stories"], list)


@pytest.mark.unit
def test_practice_status_returns_the_count_key_the_frontend_reads(client: Any) -> None:
    """CD-4: ``PracticeDetail.tsx`` reads ``data.count`` every two seconds.

    The engine reports recitations as ``total_recited``, so the counter used to
    reset to zero on every poll.
    """
    response = client.get("/api/v1/practices/zhunti/status")

    assert response.status_code == 200, response.text
    body = response.json()
    assert "count" in body, f"the frontend reads data.count; the body has {sorted(body)}"
    assert isinstance(body["count"], int)
    # The fix is ADDITIVE: when the engine has a status, its own key must
    # still be there alongside "count". A practice that has never run takes the
    # not_started branch, which has no engine status to pass through.
    if body.get("status") == "not_started":
        assert body["count"] == 0
    else:
        assert "total_recited" in body, f"the engine key must be preserved alongside count; the body has {sorted(body)}"


@pytest.mark.unit
def test_interpret_accepts_the_iching_details_key(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """CD-1: the frontend posts the cast as ``details.iching``.

    The backend used to look only at ``details["cast"]`` / ``details["primary"]``,
    so the rich I Ching branch never ran, and the chat call raised a TypeError
    that surfaced as an HTTP 500 on every interpretation.
    """
    from backend.app.api.v1.endpoints import llm as llm_module
    from core import knowledge_index

    captured: dict[str, Any] = {}

    async def fake_chat_interaction(chat_request: Any, http_request: Any = None) -> Any:
        captured["prompt"] = chat_request.messages[0].content
        return SimpleNamespace(response="stub interpretation", tool_calls=[])

    monkeypatch.setattr(llm_module, "chat_interaction", fake_chat_interaction)
    # The RAG lookup is optional and would otherwise read the knowledge index.
    monkeypatch.setattr(knowledge_index, "get_knowledge_index", lambda: SimpleNamespace(search=lambda *a, **k: []))

    response = client.post(
        "/api/v1/divination/interpret",
        json={
            "system": "I Ching",
            "question": "What does this hexagram say?",
            "details": {
                "iching": {
                    "cast_lines": [7, 7, 7, 7, 7, 7],
                    "primary": {
                        "name": "Qian / The Creative",
                        "name_english": "The Creative",
                        "judgment": "The Creative speaks of the strength of the creative force.",
                    },
                    "relating": {
                        "name": "Kun / The Receptive",
                        "name_english": "The Receptive",
                    },
                }
            },
        },
    )

    assert response.status_code == 200, f"the interpret route failed: {response.text}"
    assert "prompt" in captured, "the chat function was never called"
    assert (
        "The Creative" in captured["prompt"]
    ), "the rich I Ching branch did not activate: the hexagram name is not in the prompt"


# ---------------------------------------------------------------------------
# the guard rails
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_the_live_database_is_never_opened() -> None:
    """This suite must never touch the repo's vajra_stream.db.

    The repository conftest points DATABASE_URL at a temporary directory, and
    this asserts it actually took effect rather than trusting it.
    """
    from core.schema import get_db_path

    db_path = Path(get_db_path()).resolve()
    assert db_path != LIVE_DB_PATH.resolve(), f"the live database would be opened: {db_path}"
    assert str(db_path).startswith(
        tempfile.gettempdir()
    ), f"the test database must live under the system temp dir, not at {db_path}"


@pytest.mark.unit
def test_the_table_only_contains_audited_calls() -> None:
    """The table must be a subset of the calls the frontend really makes.

    A table entry whose marker is nowhere in the frontend is a phantom row, and
    it would make the contract test assert things nobody calls.
    """
    for call in _CALLS:
        text = _frontend_source(call)
        assert (
            call["frontend_marker"] in text
        ), f"{call['name']}: {call['frontend_marker']!r} is not in {call['frontend_source']}"
        assert call["name"] not in [
            c["name"] for c in _CALLS if c is not call
        ], f"duplicate table entry named {call['name']}"


@pytest.mark.unit
def test_every_known_unfixed_drift_names_a_ticket() -> None:
    """A strict xfail must say WHICH ticket will fix it.

    A drift with no ticket cannot be handed to an owner, so the table may not
    carry one.
    """
    for call in _CALLS:
        ticket = call.get("ticket")
        if ticket is None:
            continue
        assert (
            isinstance(ticket, str) and ticket.strip()
        ), f"{call['name']} is marked as unfixed drift but names no ticket"
