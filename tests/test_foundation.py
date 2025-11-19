"""
Test Foundation
Verify that the event bus and basic service wrappers are working correctly together.
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.event_bus import EnhancedEventBus, DomainEvent
from config.enhanced_settings import EnhancedConfig
from modules.crystal import CrystalService, CrystalBroadcastStarted, CrystalBroadcastCompleted
from modules.blessing_router import BlessingRouter, BlessingRouted, TargetSpecification, TargetType, DeliveryMethod
from modules.enhanced_scalar_waves import EnhancedScalarWaveService, WaveSessionStarted

def test_event_bus_persistence():
    print("\n--- Testing Event Bus Persistence ---")
    
    # Setup
    persistence_path = "tests/test_events.jsonl"
    if os.path.exists(persistence_path):
        os.remove(persistence_path)
        
    event_bus = EnhancedEventBus(persistence_path=persistence_path)
    
    # Define test event
    class TestEvent(DomainEvent):
        def __init__(self, message: str):
            super().__init__()
            self.message = message
            
    # Subscribe
    received_events = []
    def handler(event):
        print(f"Received event: {event.message}")
        received_events.append(event)
        
    event_bus.subscribe(TestEvent, handler)
    
    # Publish
    event_bus.publish(TestEvent("Hello World"))
    
    # Verify
    assert len(received_events) == 1
    assert received_events[0].message == "Hello World"
    assert os.path.exists(persistence_path)
    
    # Verify persistence content
    with open(persistence_path, 'r') as f:
        line = f.readline()
        assert "Hello World" in line
        
    print("Event Bus Persistence: PASS")
    
    # Cleanup
    if os.path.exists(persistence_path):
        os.remove(persistence_path)

def test_crystal_service():
    print("\n--- Testing Crystal Service ---")
    
    event_bus = EnhancedEventBus()
    service = CrystalService(event_bus)
    
    events = []
    event_bus.subscribe(CrystalBroadcastStarted, lambda e: events.append(e))
    event_bus.subscribe(CrystalBroadcastCompleted, lambda e: events.append(e))
    
    # Execute
    result = service.broadcast_intention("Healing Light", duration=1)
    
    # Verify
    assert result['status'] == 'completed'
    assert len(events) == 2
    assert isinstance(events[0], CrystalBroadcastStarted)
    assert isinstance(events[1], CrystalBroadcastCompleted)
    assert events[0].intention == "Healing Light"
    
    print("Crystal Service: PASS")

def test_blessing_router():
    print("\n--- Testing Blessing Router ---")
    
    event_bus = EnhancedEventBus()
    router = BlessingRouter(event_bus)
    
    events = []
    event_bus.subscribe(BlessingRouted, lambda e: events.append(e))
    
    # Execute
    target = TargetSpecification(TargetType.INDIVIDUAL, "John Doe")
    router.route_blessing("Peace", target, DeliveryMethod.DIRECT)
    
    # Verify
    assert len(events) == 1
    assert isinstance(events[0], BlessingRouted)
    assert events[0].intention == "Peace"
    assert events[0].target_spec.identifier == "John Doe"
    
    print("Blessing Router: PASS")

def test_enhanced_scalar_waves():
    print("\n--- Testing Enhanced Scalar Waves ---")
    
    event_bus = EnhancedEventBus()
    service = EnhancedScalarWaveService(event_bus)
    
    events = []
    event_bus.subscribe(WaveSessionStarted, lambda e: events.append(e))
    
    # Execute
    # Using 'qrng' as it's usually fast/mockable or 'lorenz'
    session_id = service.create_wave_session("lorenz", count=100)
    
    # Verify
    assert session_id is not None
    assert len(events) == 1
    assert isinstance(events[0], WaveSessionStarted)
    assert events[0].session_id == session_id
    
    print("Enhanced Scalar Waves: PASS")

def test_configuration():
    print("\n--- Testing Configuration ---")
    
    config = EnhancedConfig('test')
    
    # Verify defaults
    assert config.get('audio.sample_rate') == 44100
    assert config.get('hardware.level') in [2, 3]
    
    print("Configuration: PASS")

if __name__ == "__main__":
    try:
        test_event_bus_persistence()
        test_configuration()
        test_crystal_service()
        test_blessing_router()
        test_enhanced_scalar_waves()
        print("\nAll Foundation Tests Passed!")
    except Exception as e:
        print(f"\nTest Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)