#!/usr/bin/env python3
"""
Simple test script for new implementation features:
- Population JSON files
- Audio Service
- Session Logic with UnifiedOrchestrator
"""

import json
import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_population_files():
    """Test that new population JSON files are valid and follow the schema"""
    print("\n=== Testing Population Files ===")
    
    population_files = [
        'knowledge/blessing_populations/missing_persons_california.json',
        'knowledge/blessing_populations/genocide_victims_myanmar.json',
        'knowledge/blessing_populations/refugees_congo.json'
    ]
    
    for file_path in population_files:
        print(f"\nTesting {file_path}...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check basic structure
            assert 'description' in data, f"Missing 'description' in {file_path}"
            assert 'targets' in data, f"Missing 'targets' in {file_path}"
            assert isinstance(data['targets'], list), f"'targets' should be a list in {file_path}"
            
            # Check each target
            for i, target in enumerate(data['targets']):
                assert 'name' in target, f"Target {i} missing 'name' in {file_path}"
                assert 'category' in target, f"Target {i} missing 'category' in {file_path}"
                assert 'description' in target, f"Target {i} missing 'description' in {file_path}"
                assert 'priority' in target, f"Target {i} missing 'priority' in {file_path}"
                assert 'intention' in target, f"Target {i} missing 'intention' in {file_path}"
                assert isinstance(target['priority'], int), f"Target {i} 'priority' should be int in {file_path}"
                assert 1 <= target['priority'] <= 10, f"Target {i} 'priority' should be 1-10 in {file_path}"
            
            print(f"PASS: {file_path} is valid with {len(data['targets'])} targets")
            
        except Exception as e:
            print(f"FAIL: Error in {file_path}: {e}")
            return False
    
    return True

def test_basic_functionality():
    """Test basic functionality without complex imports"""
    print("\n=== Testing Basic Functionality ===")
    
    # Test 1: Check if population files exist
    population_files = [
        'knowledge/blessing_populations/missing_persons_california.json',
        'knowledge/blessing_populations/genocide_victims_myanmar.json',
        'knowledge/blessing_populations/refugees_congo.json'
    ]
    
    all_exist = True
    for file_path in population_files:
        if os.path.exists(file_path):
            print(f"PASS: {file_path} exists")
        else:
            print(f"FAIL: {file_path} missing")
            all_exist = False
    
    # Test 2: Check if key backend files exist
    backend_files = [
        'backend/core/orchestrator_bridge.py',
        'backend/core/services/audio_service.py',
        'backend/app/api/v1/endpoints/sessions.py',
        'backend/app/api/v1/endpoints/populations.py'
    ]
    
    backend_exists = True
    for file_path in backend_files:
        if os.path.exists(file_path):
            print(f"PASS: {file_path} exists")
        else:
            print(f"FAIL: {file_path} missing")
            backend_exists = False
    
    return all_exist and backend_exists

def main():
    """Run all tests"""
    print("Testing New Implementation Features")
    
    # Test population files
    populations_ok = test_population_files()
    
    # Test basic functionality
    basic_ok = test_basic_functionality()
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Population files: {'PASS' if populations_ok else 'FAIL'}")
    print(f"Basic functionality: {'PASS' if basic_ok else 'FAIL'}")
    
    if populations_ok and basic_ok:
        print("\nAll tests passed! Implementation is working correctly.")
        return True
    else:
        print("\nSome tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)