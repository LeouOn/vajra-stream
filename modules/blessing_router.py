"""
Blessing Router Module
Routes blessings to appropriate targets and channels
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Protocol
import uuid
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.interfaces import EventBus, DomainEvent
from modules.blessings import BlessingService, BlessingGenerated

class TargetType(Enum):
    INDIVIDUAL = "individual"
    LOCATION = "location"
    TEMPORAL = "temporal"
    POPULATION = "population"
    ENERGETIC = "energetic"

class DeliveryMethod(Enum):
    DIRECT = "direct"
    CRYSTAL = "crystal"
    RADIONICS = "radionics"
    AUDIO = "audio"

@dataclass
class TargetSpecification:
    target_type: TargetType
    identifier: str
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ResolvedTarget:
    name: str
    tradition: str
    attributes: Dict[str, Any]

@dataclass
class BlessingRouted(DomainEvent):
    """Event: Blessing has been routed"""
    intention: str
    target_spec: TargetSpecification
    delivery_method: DeliveryMethod

class TargetResolver(Protocol):
    def resolve(self, target_spec: TargetSpecification) -> ResolvedTarget:
        ...

class NaturalLanguageResolver:
    """Resolves targets from natural language descriptions"""
    def resolve(self, target_spec: TargetSpecification) -> ResolvedTarget:
        text = target_spec.identifier
        metadata = target_spec.metadata or {}
        
        # Pattern: "to [Name] in [Location]"
        location_match = re.search(r"to\s+(.+?)\s+in\s+(.+)", text, re.IGNORECASE)
        if location_match:
            name = location_match.group(1).strip()
            location = location_match.group(2).strip()
            metadata['location'] = location
            return ResolvedTarget(
                name=name,
                tradition=metadata.get('tradition', 'universal'),
                attributes=metadata
            )
            
        # Pattern: "for [Name]"
        for_match = re.search(r"for\s+(.+)", text, re.IGNORECASE)
        if for_match:
            name = for_match.group(1).strip()
            return ResolvedTarget(
                name=name,
                tradition=metadata.get('tradition', 'universal'),
                attributes=metadata
            )

        return ResolvedTarget(
            name=text,
            tradition=metadata.get('tradition', 'universal'),
            attributes=metadata
        )

class DefaultResolver:
    def resolve(self, target_spec: TargetSpecification) -> ResolvedTarget:
        metadata = target_spec.metadata or {}
        return ResolvedTarget(
            name=target_spec.identifier,
            tradition=metadata.get('tradition', 'universal'),
            attributes=metadata
        )

class BlessingRouter:
    """Routes blessings to appropriate targets and channels"""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus
        self.target_resolvers: Dict[TargetType, TargetResolver] = {}
        self.delivery_channels = {}
        # Initialize BlessingService with event_bus
        self.blessing_service = BlessingService(event_bus)
        self._register_default_resolvers()
    
    def _register_default_resolvers(self):
        """Register default target resolvers"""
        default_resolver = DefaultResolver()
        nl_resolver = NaturalLanguageResolver()
        
        for target_type in TargetType:
            if target_type == TargetType.INDIVIDUAL:
                self.target_resolvers[target_type] = nl_resolver
            else:
                self.target_resolvers[target_type] = default_resolver
            
    def route_blessing(
        self,
        intention: str,
        target_spec: TargetSpecification,
        delivery_method: DeliveryMethod = DeliveryMethod.DIRECT,
        timing: Optional[Dict] = None
    ) -> str:
        """Route blessing to appropriate target and channel"""
        
        blessing_id = str(uuid.uuid4())
        
        # Resolve target
        resolver = self.target_resolvers.get(target_spec.target_type)
        if not resolver:
            raise ValueError(f"No resolver for target type: {target_spec.target_type}")
        
        resolved_target = resolver.resolve(target_spec)
        
        # Generate blessing
        blessing = self.blessing_service.generate_blessing(
            target_name=resolved_target.name,
            intention=intention,
            tradition=resolved_target.tradition
        )
        
        # In a full implementation, we would route to specific delivery channels here
        # For now, we just log/event the routing
        
        # Publish events
        if self.event_bus:
            self.event_bus.publish(BlessingRouted(
                timestamp=datetime.now(),
                event_id=blessing_id,
                intention=intention,
                target_spec=target_spec,
                delivery_method=delivery_method
            ))
        
        return blessing_id