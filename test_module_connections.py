#!/usr/bin/env python3
"""
Test script to verify module connections and orchestrator initialization
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_orchestrator_initialization():
    """Test if UnifiedOrchestrator initializes correctly"""
    print("=" * 60)
    print("Testing UnifiedOrchestrator Initialization")
    print("=" * 60)
    
    try:
        from scripts.unified_orchestrator import UnifiedOrchestrator
        print("+ UnifiedOrchestrator import successful")
        
        orchestrator = UnifiedOrchestrator()
        print("+ UnifiedOrchestrator initialization successful")
        
        # Check services
        services = orchestrator.services
        print(f"+ Services initialized: {list(services.keys())}")
        
        # Check event bus
        if orchestrator.event_bus:
            print("+ Event bus initialized")
        else:
            print("- Event bus not initialized")
            
        return True
        
    except Exception as e:
        print(f"- UnifiedOrchestrator initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_orchestrator_bridge():
    """Test if OrchestratorBridge works correctly"""
    print("\n" + "=" * 60)
    print("Testing OrchestratorBridge")
    print("=" * 60)
    
    try:
        from backend.core.orchestrator_bridge import OrchestratorBridge
        print("+ OrchestratorBridge import successful")
        
        bridge = OrchestratorBridge()
        print("+ OrchestratorBridge singleton creation successful")
        
        # Initialize
        bridge.initialize()
        print("+ OrchestratorBridge initialization successful")
        
        # Check if orchestrator is available
        if bridge.orchestrator:
            print("+ UnifiedOrchestrator available through bridge")
        else:
            print("- UnifiedOrchestrator not available through bridge")
            
        return True
        
    except Exception as e:
        print(f"- OrchestratorBridge test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_connections():
    """Test individual service connections"""
    print("\n" + "=" * 60)
    print("Testing Service Connections")
    print("=" * 60)
    
    services_to_test = [
        ('modules.blessing_router', 'BlessingRouter'),
        ('modules.crystal', 'CrystalService'),
        ('modules.radionics_enhancer', 'RadionicsEnhancer'),
        ('modules.audio', 'AudioService'),
        ('modules.healing', 'HealingService'),
        ('modules.visualization', 'VisualizationService'),
    ]
    
    results = {}
    
    for module_name, class_name in services_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            service_class = getattr(module, class_name)
            print(f"+ {class_name} import successful")
            results[class_name] = True
        except Exception as e:
            print(f"- {class_name} import failed: {e}")
            results[class_name] = False
    
    return results

def test_event_bus():
    """Test event bus functionality"""
    print("\n" + "=" * 60)
    print("Testing Event Bus")
    print("=" * 60)
    
    try:
        from infrastructure.event_bus import EnhancedEventBus
        from modules.interfaces import DomainEvent
        from datetime import datetime
        import uuid
        
        print("+ Event bus import successful")
        
        # Create event bus
        event_bus = EnhancedEventBus()
        print("+ Event bus creation successful")
        
        # Test event subscription and publishing
        test_event_received = False
        
        def test_handler(event):
            nonlocal test_event_received
            test_event_received = True
            print(f"+ Event received: {event.__class__.__name__}")
        
        # Subscribe to test event
        event_bus.subscribe(DomainEvent, test_handler)
        print("+ Event subscription successful")
        
        # Create and publish test event
        class TestEvent(DomainEvent):
            def __init__(self):
                super().__init__(datetime.now(), str(uuid.uuid4()))
        
        test_event = TestEvent()
        event_bus.publish(test_event)
        
        if test_event_received:
            print("+ Event publishing and handling successful")
            return True
        else:
            print("- Event publishing failed - handler not called")
            return False
            
    except Exception as e:
        print(f"- Event bus test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_connection_manager():
    """Test WebSocket connection manager"""
    print("\n" + "=" * 60)
    print("Testing Connection Manager")
    print("=" * 60)
    
    try:
        from backend.websocket.connection_manager_stable_v2 import stable_connection_manager_v2
        print("+ Stable connection manager v2 import successful")
        
        # Check stats
        stats = stable_connection_manager_v2.get_connection_stats()
        print(f"+ Connection stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"- Connection manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_integration():
    """Test full integration with session creation"""
    print("\n" + "=" * 60)
    print("Testing Full Integration")
    print("=" * 60)
    
    try:
        from backend.core.orchestrator_bridge import orchestrator_bridge
        
        # Initialize bridge
        orchestrator_bridge.initialize()
        print("+ Bridge initialized for integration test")
        
        # Test session creation
        import asyncio
        
        async def test_session():
            session_id = await orchestrator_bridge.create_session(
                intention="Universal Peace",
                targets=[{'type': 'individual', 'identifier': 'All Beings'}],
                modalities=['crystal', 'audio'],
                duration=10
            )
            print(f"+ Session created: {session_id}")
            return session_id
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        session_id = loop.run_until_complete(test_session())
        loop.close()
        
        return session_id is not None
        
    except Exception as e:
        print(f"- Full integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("Module Connection Test Suite")
    print("Testing Vajra.Stream backend module connections...")
    
    results = {}
    
    # Run individual tests
    results['orchestrator'] = test_orchestrator_initialization()
    results['bridge'] = test_orchestrator_bridge()
    results['services'] = test_service_connections()
    results['event_bus'] = test_event_bus()
    results['connection_manager'] = test_connection_manager()
    results['integration'] = test_full_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        if test_name == 'services':
            # Handle services separately
            print(f"Services:")
            for service_name, success in result.items():
                status = "+" if success else "-"
                print(f"  {status} {service_name}")
        else:
            status = "+" if result else "-"
            print(f"{status} {test_name.replace('_', ' ').title()}")
    
    # Overall result
    all_passed = (
        results['orchestrator'] and
        results['bridge'] and
        results['event_bus'] and
        results['connection_manager'] and
        results['integration'] and
        all(results['services'].values())
    )
    
    print("\n" + "=" * 60)
    if all_passed:
        print("+ ALL TESTS PASSED - Module connections are working!")
    else:
        print("- SOME TESTS FAILED - Module connection issues detected")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())