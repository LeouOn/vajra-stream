"""
Demo of the Unified Architecture
Simulates a real usage scenario: "Healing for the Amazon Rainforest"
"""

import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.unified_orchestrator import UnifiedOrchestrator
from infrastructure.event_bus import DomainEvent
from modules.blessing_router import BlessingRouted, BlessingGenerated
from modules.crystal import CrystalBroadcastStarted, CrystalBroadcastCompleted

# Configure logging to show what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DemoSystem")

def print_event(event: DomainEvent):
    """Listener to print events as they occur"""
    print(f"\n[EVENT] {event.__class__.__name__}")
    print(f"  ID: {event.event_id}")
    print(f"  Timestamp: {event.timestamp}")
    # Filter out private attributes and large objects for cleaner output
    data = {k: v for k, v in event.__dict__.items() if not k.startswith('_')}
    print(f"  Data: {data}")

def main():
    print("============================================================")
    print("   VAJRA STREAM - UNIFIED ARCHITECTURE DEMO")
    print("============================================================")
    
    # 1. Initialize Orchestrator
    print("\n1. Initializing Unified Orchestrator...")
    orchestrator = UnifiedOrchestrator()
    
    # Subscribe to key events for visibility
    orchestrator.event_bus.subscribe(BlessingRouted, print_event)
    orchestrator.event_bus.subscribe(BlessingGenerated, print_event)
    orchestrator.event_bus.subscribe(CrystalBroadcastStarted, print_event)
    orchestrator.event_bus.subscribe(CrystalBroadcastCompleted, print_event)
    
    # 2. Define Complex Request
    intention = "Healing and Regeneration for the Amazon Rainforest"
    targets = [
        {
            'type': 'location',
            'identifier': 'Amazon Rainforest',
            'metadata': {
                'coordinates': '3.4653° S, 62.2159° W',
                'focus': 'regrowth, protection, biodiversity'
            }
        }
    ]
    modalities = ['crystal'] 
    duration = 5 # 5 seconds for demo
    
    print(f"\n2. Starting Session: '{intention}'")
    print(f"   Target: {targets[0]['identifier']}")
    print(f"   Modalities: {modalities}")
    
    # 3. Execute Session
    session_id = orchestrator.create_session(
        intention=intention,
        targets=targets,
        modalities=modalities,
        duration=duration
    )
    
    print(f"\nSession Created: {session_id}")
    print("Waiting for processing...")
    
    # Wait for duration + buffer
    time.sleep(duration + 2)
    
    print("\n3. Demo Completed")
    print("============================================================")

if __name__ == "__main__":
    main()