import pytest

from modules.radionics_enhancer import RadionicsEnhancer, StructuralLink


@pytest.fixture
def enhancer():
    return RadionicsEnhancer()


@pytest.mark.unit
class TestEntropy:
    def test_entropy_in_range(self, enhancer):
        entropy = enhancer.get_entropy_value()
        assert isinstance(entropy, float)
        assert 0.0 <= entropy <= 1.0

    def test_entropy_varies(self, enhancer):
        e1 = enhancer.get_entropy_value()
        e2 = enhancer.get_entropy_value()
        assert e1 != e2


@pytest.mark.unit
class TestRateAttunement:
    def test_attune_rate_in_range(self, enhancer):
        rate = enhancer.attune_rate("Healing for the World")
        assert isinstance(rate, float)
        assert 0.0 <= rate <= 100.0


@pytest.mark.unit
class TestTrendPadding:
    def test_fibonacci_padding(self, enhancer):
        padded = enhancer.apply_trend_padding("test_signal", padding_type="fibonacci", repetitions=3)
        assert len(padded) == 6
        assert padded[0] == "test_signal"

    def test_exponential_padding(self, enhancer):
        padded = enhancer.apply_trend_padding("test_signal", padding_type="exponential", repetitions=3)
        assert len(padded) == 7


@pytest.mark.unit
class TestStructuralLink:
    def test_create_link(self, enhancer):
        link = enhancer.create_structural_link(
            link_type="digital",
            target="John Doe",
            metadata={"notes": "Test Subject"},
        )
        assert isinstance(link, StructuralLink)
        assert link.target == "John Doe"
        assert link.link_type == "digital"
        assert link.id in enhancer.active_links
