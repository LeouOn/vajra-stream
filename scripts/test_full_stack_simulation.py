import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import types for checking
from infrastructure.event_bus import DomainEvent

# Mock ConnectionManager to capture broadcasts
class MockConnectionManager:
    def __init__(self):
        self.broadcasts = []

    async def broadcast(self, message: dict):
        # print(f"DEBUG: Broadcast received: {message}")
        self.broadcasts.append(message)

async def run_simulation():
    print("Starting Full Stack Simulation...")
    
    # 1. Setup Mocks
    mock_cm = MockConnectionManager()
    
    # Patch the singleton in the module where it is used
    with patch('backend.core.orchestrator_bridge.connection_manager', mock_cm):
        
        # 2. Initialize Bridge
        from backend.core.orchestrator_bridge import OrchestratorBridge
        bridge = OrchestratorBridge()
        
        # Reset singleton state for test
        bridge.initialized = False 
        bridge.orchestrator = None
        
        print("Initializing OrchestratorBridge...")
        bridge.initialize()
        
        # 3. Simulate START_SESSION
        print("\nSimulating START_SESSION...")
        intention = "Global Peace"
        try:
            session_id = await bridge.create_session(
                intention=intention,
                targets=[{'type': 'individual', 'identifier': 'All Beings'}],
                modalities=['crystal'],
                duration=10
            )
            print(f"Session created: {session_id}")
        except Exception as e:
            print(f"Error creating session: {e}")
            return
        
        # 4. Verify Events
        print("\nVerifying Events...")
        
        # Allow some time for async events to propagate
        await asyncio.sleep(0.5)
        
        events = mock_cm.broadcasts
        domain_events = [e for e in events if e.get('type') == 'domain_event']
        event_types = [e.get('event_type') for e in domain_events]
        
        print(f"Captured {len(domain_events)} domain events.")
        print(f"Event Types: {event_types}")
        
        # Check for specific events
        has_blessing = 'BlessingRouted' in event_types
        has_crystal = 'CrystalBroadcastStarted' in event_types
        
        # Check for Radionics event
        # We look for any event that might be the radionics one, or check if it's missing
        radionics_events = [e for e in domain_events if 'Radionics' in e.get('event_type', '') or 'Rate' in e.get('event_type', '')]
        has_radionics = len(radionics_events) > 0
        
        print(f"BlessingRouted: {'OK' if has_blessing else 'MISSING'}")
        print(f"CrystalBroadcastStarted: {'OK' if has_crystal else 'MISSING'}")
        print(f"Radionics Event: {'OK' if has_radionics else 'MISSING'}")
        
        if has_radionics:
            print(f"Radionics Event Data: {radionics_events[0]}")

        if has_blessing and has_crystal and has_radionics:
            print("\nSUCCESS: All expected events received.")
        else:
            print("\nPARTIAL SUCCESS: Some events missing.")
            if not has_radionics:
                print("NOTE: Radionics event is missing. This is expected if not yet implemented.")

if __name__ == "__main__":
    asyncio.run(run_simulation())