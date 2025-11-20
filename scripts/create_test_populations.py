#!/usr/bin/env python3
"""
Create Test Populations

This script creates the test populations (California, Myanmar, Congo) 
that are expected by the data loading test.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from backend.core.services.population_manager import (
    get_population_manager,
    PopulationCategory,
    SourceType
)

def create_test_populations():
    """Create test populations"""
    manager = get_population_manager()
    
    # Create California population
    california = manager.create_population(
        name="California",
        description="Missing persons from California",
        category=PopulationCategory.MISSING_PERSONS,
        source_type=SourceType.MANUAL,
        intentions=["safety", "reunion", "love"],
        priority=7
    )
    print(f"Created California population: {california.id}")
    
    # Create Myanmar population
    myanmar = manager.create_population(
        name="Myanmar",
        description="Genocide victims from Myanmar",
        category=PopulationCategory.CONFLICT_ZONES,
        source_type=SourceType.MANUAL,
        intentions=["peace", "healing", "justice"],
        priority=8
    )
    print(f"Created Myanmar population: {myanmar.id}")
    
    # Create Congo population
    congo = manager.create_population(
        name="Congo",
        description="Refugees from Congo",
        category=PopulationCategory.REFUGEES,
        source_type=SourceType.MANUAL,
        intentions=["safety", "shelter", "peace"],
        priority=6
    )
    print(f"Created Congo population: {congo.id}")
    
    # Get all populations to verify
    all_populations = manager.get_all_populations()
    print(f"\nTotal populations created: {len(all_populations)}")
    for pop in all_populations:
        print(f"  - {pop.name} ({pop.category.value})")
    
    return len(all_populations)

if __name__ == "__main__":
    print("Creating test populations...")
    count = create_test_populations()
    print(f"\nSuccessfully created {count} populations")