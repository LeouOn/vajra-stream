"""GET /api/v1/stories/search must return the key the UI reads.

Ticket CD-3: the route returned {"results": [...], "query": q} while
frontend/src/stores/commandStore.ts reads ``data.stories?.forEach(...)``, so
story search silently showed nothing in the Command Center. The fix is
additive: BOTH ``results`` (existing consumers) and ``stories`` (the UI) hold
the same list, plus ``query``.

Verified offline with TestClient against the app object — no server, no
lifespan (TestClient is not used as a context manager), no network.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_search_arrow_returns_stories_and_results_identical(client: TestClient) -> None:
    response = client.get("/api/v1/stories/search", params={"q": "arrow"})
    assert response.status_code == 200
    data = response.json()

    # The key the UI reads must exist and match the existing key.
    assert isinstance(data.get("stories"), list) and data["stories"], "'stories' must be a non-empty list"
    assert data["stories"] == data["results"], "'stories' and 'results' must hold the same list"
    assert data["query"] == "arrow"
    assert data["stories"][0]["id"] == "the_arrow"


def test_empty_q_returns_all_tales(client: TestClient) -> None:
    response = client.get("/api/v1/stories/search", params={"q": ""})
    assert response.status_code == 200
    data = response.json()

    assert data["query"] == ""
    assert len(data["stories"]) == len(data["results"])
    assert len(data["stories"]) >= 4, "empty q must return the full hardcoded tale list"


def test_unknown_q_returns_empty_lists(client: TestClient) -> None:
    response = client.get("/api/v1/stories/search", params={"q": "zebra-unicorn-42"})
    assert response.status_code == 200
    data = response.json()

    assert data["stories"] == []
    assert data["results"] == []
    assert data["query"] == "zebra-unicorn-42"
