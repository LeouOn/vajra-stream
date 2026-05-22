import pytest


@pytest.mark.integration
class TestContainerInit:
    def test_container_imports(self):
        from container import container
        assert container is not None

    def test_scalar_waves_accessible(self, fresh_container):
        assert fresh_container.scalar_waves is not None

    def test_radionics_accessible(self, fresh_container):
        assert fresh_container.radionics is not None

    def test_blessings_accessible(self, fresh_container):
        assert fresh_container.blessings is not None


@pytest.mark.integration
class TestVisualizationModule:
    def test_loads_and_reports_status(self):
        from modules.visualization import VisualizationService
        viz = VisualizationService()
        status = viz.get_status()
        assert "rothko_available" in status
        assert "energetic_viz_available" in status


@pytest.mark.integration
class TestAnatomyModule:
    def test_loads_with_visualization_flag(self):
        from modules.anatomy import AnatomyService
        anatomy = AnatomyService()
        assert hasattr(anatomy, "has_visualization")


@pytest.mark.integration
class TestAudioModule:
    def test_loads_and_reports_status(self):
        from modules.audio import AudioService
        audio = AudioService()
        status = audio.get_status()
        assert "audio_generator" in status
        assert "tts" in status


@pytest.mark.integration
class TestAPIImport:
    def test_fastapi_app_imports(self):
        from backend.app.main import app
        assert app is not None
