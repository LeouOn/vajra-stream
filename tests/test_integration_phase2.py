"""
Integration Tests for Phase 2: Integration Layer
Verifies Unified Orchestrator, Blessing Router, and Crystal Service integration.
"""

import unittest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.unified_orchestrator import UnifiedOrchestrator
from modules.blessing_router import BlessingRouted, TargetType
from modules.crystal import CrystalBroadcastStarted

class TestIntegrationPhase2(unittest.TestCase):
    
    def setUp(self):
        # Mock hardware to prevent actual audio output during tests
        self.mock_sd_patcher = patch('sounddevice.play')
        self.mock_sd = self.mock_sd_patcher.start()
        
        self.orchestrator = UnifiedOrchestrator()
        
        # Capture events
        self.events = []
        self.orchestrator.event_bus.subscribe(BlessingRouted, self._on_blessing_routed)
        self.orchestrator.event_bus.subscribe(CrystalBroadcastStarted, self._on_crystal_started)
        
    def tearDown(self):
        self.mock_sd_patcher.stop()
        
    def _on_blessing_routed(self, event):
        self.events.append(event)
        
    def _on_crystal_started(self, event):
        self.events.append(event)
        
    def test_full_workflow(self):
        """
        Test a full workflow:
        1. Start Orchestrator
        2. Send a "Blessing Request"
        3. Verify Router routes it
        4. Verify Crystal module receives command
        """
        
        print("\nStarting Phase 2 Integration Test...")
        
        intention = "Healing for John"
        targets = [
            {
                'type': 'individual',
                'identifier': 'to John in NY',
                'metadata': {'tradition': 'buddhist'}
            }
        ]
        modalities = ['crystal']
        duration = 1 # Short duration for test
        
        # Execute session
        session_id = self.orchestrator.create_session(
            intention=intention,
            targets=targets,
            modalities=modalities,
            duration=duration
        )
        
        print(f"Session created: {session_id}")
        
        # Verify Blessing Routing
        routed_events = [e for e in self.events if isinstance(e, BlessingRouted)]
        self.assertTrue(len(routed_events) > 0, "BlessingRouted event not fired")
        
        event = routed_events[0]
        self.assertEqual(event.intention, intention)
        self.assertEqual(event.target_spec.target_type, TargetType.INDIVIDUAL)
        # Verify Natural Language Parsing
        self.assertEqual(event.target_spec.identifier, 'to John in NY')
        
        print("Blessing Router verification passed.")
        
        # Verify Crystal Activation
        crystal_events = [e for e in self.events if isinstance(e, CrystalBroadcastStarted)]
        self.assertTrue(len(crystal_events) > 0, "CrystalBroadcastStarted event not fired")
        
        c_event = crystal_events[0]
        self.assertEqual(c_event.intention, intention)
        self.assertEqual(c_event.hardware_level, 2)
        
        print("Crystal Service verification passed.")
        
        print("Phase 2 Integration Test Completed Successfully.")

if __name__ == '__main__':
    unittest.main()