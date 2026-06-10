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
            )


def test_loop_start_parameters(client):
    with patch("container.container.outlook.start_broadcast_loop") as mock_start_loop:
        mock_start_loop.return_value = True

        response = client.post(
            "/api/v1/outlook/loop/start",
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
                "randomize_realm": True,
                "randomize_characters": True,
            },
        )

        assert response.status_code == 200
        mock_start_loop.assert_called_once_with(
            interval_minutes=10,
            lat=34.0522,
            lon=-118.2437,
            languages=["Tibetan"],
            genre="dharani",
            custom_context=None,
            realm_id=None,
            population_ids=None,
            character_ids=None,
            excluded_forces=None,
            include_dialogue=False,
            loop_mode="sequential_delay",
            model="loop-model-xyz",
            include_astrology=False,
            include_tarot=False,
            include_iching=False,
            include_geomancy=True,
            cycle_genres=False,
            randomize_realm=True,
            randomize_characters=True,
        )


def test_randomization_logic_in_generator(fresh_outlook_service):
    # Mock managers to return active items
    mock_realm = MagicMock()
    mock_realm.id = "mock_realm_id"
    mock_realm.is_metaphysical = True

    mock_char = MagicMock()
    mock_char.id = "mock_char_id"

    with (
        patch("core.outlook_generator.get_location_manager") as mock_lm,
        patch("core.outlook_generator.get_character_manager") as mock_cm,
        patch("core.outlook_generator.random.choice") as mock_choice,
        patch("core.outlook_generator.random.sample") as mock_sample,
    ):
        mock_lm.return_value.get_active_locations.return_value = [mock_realm]
        mock_cm.return_value.get_active_characters.return_value = [mock_char]
        mock_choice.return_value = mock_realm
        mock_sample.return_value = [mock_char]

        # Use mock LLM to avoid real generation calls
        fresh_outlook_service.generator.llm = MagicMock()
        fresh_outlook_service.generator.llm.generate.return_value = "Randomized blessing content."

        result = fresh_outlook_service.generate_single(
            lat=34.0522, lon=-118.2437, languages=["English"], randomize_realm=True, randomize_characters=True
        )

        assert result["status"] == "success"
        mock_lm.return_value.get_active_locations.assert_called_once()
        mock_cm.return_value.get_active_characters.assert_called_once()
        assert mock_choice.call_count == 3
        mock_sample.assert_called_once()
