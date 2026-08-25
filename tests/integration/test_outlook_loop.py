from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.app.main import app

    return TestClient(app)


@pytest.fixture
def fresh_outlook_service():
    from container import container

    return container.outlook


def test_outlook_request_parameters(client):
    # Mock generation on the service layer to avoid actual LLM calls
    with patch("container.container.outlook.generate_single") as mock_gen:
        mock_gen.return_value = {
            "status": "success",
            "type": "single",
            "genre": "healing",
            "languages": ["English"],
            "astrology_used": "Astrology alignment",
            "divination_used": "Divination alignment",
            "divination_raw": {},
            "entities_used": "Buddha",
            "narrative": "A peaceful test blessing.",
        }

        # Mock get_db_connection to avoid writing to database in test
        with patch("backend.app.api.v1.endpoints.outlook.get_db_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor

            response = client.post(
                "/api/v1/outlook/generate_single",
                json={
                    "lat": 34.0522,
                    "lon": -118.2437,
                    "languages": ["English", "Sanskrit"],
                    "genre": "healing",
                    "model": "test-model-123",
                    "randomize_realm": True,
                    "randomize_characters": True,
                },
            )

            assert response.status_code == 200
            mock_gen.assert_called_once_with(
                lat=34.0522,
                lon=-118.2437,
                languages=["English", "Sanskrit"],
                genre="healing",
                date=None,
                custom_context=None,
                realm_id=None,
                population_ids=None,
                character_ids=None,
                excluded_forces=None,
                include_dialogue=False,
                model="test-model-123",
                include_geomancy=True,
                randomize_realm=True,
                randomize_characters=True,
                natal_dt=None,
                natal_location=None,
            )


def test_loop_start_parameters(client):
    """POST /background/start stores the config the loop will use.

    The endpoint function is registered directly as the route handler, so
    patching the module attribute is useless here — assert on the stored
    ``_bg_config`` global instead, then stop the loop it started.
    """
    from backend.app.api.v1.endpoints import outlook as outlook_endpoint

    try:
        response = client.post(
            "/api/v1/outlook/background/start",
            json={
                "interval_minutes": 10,
                "lat": 34.0522,
                "lon": -118.2437,
                "languages": ["Tibetan"],
                "genre": "dharani",
                "model": "loop-model-xyz",
                "include_astrology": False,
                "include_tarot": False,
                "include_iching": False,
            },
        )

        assert response.status_code == 200
        cfg = outlook_endpoint._bg_config
        assert cfg.interval_minutes == 10
        assert cfg.lat == 34.0522
        assert cfg.lon == -118.2437
        assert cfg.languages == ["Tibetan"]
        assert cfg.genre == "dharani"
        assert cfg.model == "loop-model-xyz"
        assert cfg.include_astrology is False
        assert cfg.include_tarot is False
        assert cfg.include_iching is False
        assert cfg.include_geomancy is True
    finally:
        client.post("/api/v1/outlook/background/stop")


def test_randomization_logic_in_generator(fresh_outlook_service):
    # Mock managers to return active items
    mock_realm = MagicMock()
    mock_realm.id = "mock_realm_id"
    mock_realm.is_metaphysical = True
    mock_realm.priority = 7

    mock_char = MagicMock()
    mock_char.id = "mock_char_id"
    mock_char.priority = 5

    with (
        patch("core.outlook_generator.get_location_manager") as mock_lm,
        patch("core.outlook_generator.get_character_manager") as mock_cm,
        # Updated: randomization now uses random.choices (weighted) instead
        # of random.choice / random.sample.
        patch("core.outlook_generator.random.choices") as mock_choices,
        patch("core.outlook_generator.random.randint") as mock_randint,
    ):
        mock_lm.return_value.get_active_locations.return_value = [mock_realm]
        mock_cm.return_value.get_active_characters.return_value = [mock_char]
        # random.choices returns a list, so mock the realm/char selections
        mock_choices.side_effect = [[mock_realm], [mock_char, mock_char]]
        mock_randint.return_value = 2  # min(randint(2,3), len(active_chars))

        # Use mock LLM to avoid real generation calls
        fresh_outlook_service.generator.llm = MagicMock()
        fresh_outlook_service.generator.llm.generate.return_value = "Randomized blessing content."

        result = fresh_outlook_service.generate_single(
            lat=34.0522, lon=-118.2437, languages=["English"], randomize_realm=True, randomize_characters=True
        )

        assert result["status"] == "success"
        mock_lm.return_value.get_active_locations.assert_called_once()
        mock_cm.return_value.get_active_characters.assert_called_once()
        # random.choices is called for realm selection AND character selection
        assert mock_choices.call_count >= 2


def test_outlook_default_coordinates(client):
    from backend.app.api.v1.endpoints.outlook import BackgroundGenerationConfig, OutlookRequest
    from config.settings import DEFAULT_LATITUDE, DEFAULT_LONGITUDE

    req = OutlookRequest()
    assert req.lat == DEFAULT_LATITUDE
    assert req.lon == DEFAULT_LONGITUDE

    bg_cfg = BackgroundGenerationConfig()
    assert bg_cfg.lat == DEFAULT_LATITUDE
    assert bg_cfg.lon == DEFAULT_LONGITUDE


@pytest.mark.asyncio
async def test_background_loop_warmup_beats_full_interval():
    """First sequential_delay sleep is the 120s warmup, not interval_minutes*60.

    Regression lock: the loop used to sleep the full interval before its
    first generation, so any server session shorter than interval_minutes
    produced nothing (History stayed empty despite the loop "running").
    """
    import asyncio

    from backend.app.api.v1.endpoints import outlook as outlook_endpoint

    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        raise asyncio.CancelledError()

    with patch.object(outlook_endpoint.asyncio, "sleep", fake_sleep):
        # The loop's CancelledError handler breaks the while-loop, so this
        # returns normally after the first (warmup) sleep.
        await outlook_endpoint._background_generation_loop(
            outlook_endpoint.BackgroundGenerationConfig(interval_minutes=60)
        )

    assert sleeps[0] == 120.0
