import unittest
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.radionics_enhancer import RadionicsEnhancer, StructuralLink

class TestRadionicsEnhancer(unittest.TestCase):
    def setUp(self):
        self.enhancer = RadionicsEnhancer()

    def test_entropy_generation(self):
        """Test that entropy values are within valid range [0.0, 1.0]."""
        entropy = self.enhancer.get_entropy_value()
        self.assertIsInstance(entropy, float)
        self.assertGreaterEqual(entropy, 0.0)
        self.assertLessEqual(entropy, 1.0)
        
        # Verify randomness (basic check)
        entropy2 = self.enhancer.get_entropy_value()
        self.assertNotEqual(entropy, entropy2)

    def test_rate_attunement(self):
        """Test that rate attunement generates consistent but entropy-influenced rates."""
        intention = "Healing for the World"
        rate = self.enhancer.attune_rate(intention)
        self.assertIsInstance(rate, float)
        self.assertGreaterEqual(rate, 0.0)
        self.assertLessEqual(rate, 100.0)

    def test_trend_padding_fibonacci(self):
        """Test Fibonacci trend padding."""
        signal = "test_signal"
        padded = self.enhancer.apply_trend_padding(signal, padding_type='fibonacci', repetitions=3)
        
        # Fibonacci sequence: 1, 1, 2, 3, 5...
        # Repetitions=3 means we iterate 3 times.
        # Iteration 1: b=1 -> adds 1 signal. a=1, b=2
        # Iteration 2: b=2 -> adds 2 signals. a=2, b=3
        # Iteration 3: b=3 -> adds 3 signals. a=3, b=5
        # Total length = 1 + 2 + 3 = 6
        self.assertEqual(len(padded), 6)
        self.assertEqual(padded[0], signal)

    def test_trend_padding_exponential(self):
        """Test Exponential trend padding."""
        signal = "test_signal"
        padded = self.enhancer.apply_trend_padding(signal, padding_type='exponential', repetitions=3)
        
        # Exponential: 2^0, 2^1, 2^2...
        # Iteration 0: 2^0 = 1
        # Iteration 1: 2^1 = 2
        # Iteration 2: 2^2 = 4
        # Total length = 1 + 2 + 4 = 7
        self.assertEqual(len(padded), 7)

    def test_structural_link_creation(self):
        """Test creation and registration of structural links."""
        link = self.enhancer.create_structural_link(
            link_type="digital",
            target="John Doe",
            metadata={"notes": "Test Subject"}
        )
        
        self.assertIsInstance(link, StructuralLink)
        self.assertEqual(link.target, "John Doe")
        self.assertEqual(link.link_type, "digital")
        self.assertIn(link.id, self.enhancer.active_links)
        self.assertEqual(self.enhancer.active_links[link.id], link)

if __name__ == '__main__':
    unittest.main()