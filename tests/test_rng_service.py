import pytest

from backend.core.services.rng_attunement_service import (
    NeedleState,
    ReadingQuality,
    RNGAttunementService,
)


@pytest.fixture
def rng_service():
    return RNGAttunementService()


@pytest.fixture
def rng_session(rng_service):
    session_id = rng_service.create_session(baseline_tone_arm=5.0, sensitivity=1.0)
    yield session_id
    rng_service.stop_session(session_id)


@pytest.mark.unit
class TestRNGServiceLifecycle:
    def test_create_session(self, rng_service):
        session_id = rng_service.create_session(baseline_tone_arm=5.0, sensitivity=1.0)
        assert session_id is not None
        rng_service.stop_session(session_id)

    def test_stop_session(self, rng_service):
        session_id = rng_service.create_session(baseline_tone_arm=5.0, sensitivity=1.0)
        assert rng_service.stop_session(session_id) is True
        assert rng_service.get_reading(session_id) is None


@pytest.mark.unit
class TestRNGReadings:
    def test_get_reading_returns_valid_data(self, rng_service, rng_session):
        reading = rng_service.get_reading(rng_session)
        assert reading is not None
        assert 0.0 <= reading.raw_value <= 1.0
        assert 0.0 <= reading.tone_arm <= 10.0
        assert -100 <= reading.needle_position <= 100
        assert isinstance(reading.needle_state, NeedleState)
        assert isinstance(reading.quality, ReadingQuality)
        assert 0.0 <= reading.coherence <= 1.0
        assert 0.0 <= reading.entropy <= 1.0
        assert 0.0 <= reading.floating_needle_score <= 1.0

    def test_readings_vary(self, rng_service, rng_session):
        r1 = rng_service.get_reading(rng_session)
        r2 = rng_service.get_reading(rng_session)
        assert r1.raw_value != r2.raw_value


@pytest.mark.unit
class TestRNGSessionSummary:
    def test_summary_after_readings(self, rng_service, rng_session):
        for _ in range(5):
            rng_service.get_reading(rng_session)

        summary = rng_service.get_session_summary(rng_session)
        assert summary is not None
        assert summary["total_readings"] == 5
        assert summary["is_active"] is True
        assert "avg_tone_arm" in summary
        assert "avg_coherence" in summary
