#!/usr/bin/env python3
"""
Test Data Loading API Endpoint

This script tests the data loading functionality by fetching data from
the /api/v1/populations/ endpoint and verifying that the expected
populations (California, Myanmar, Congo) are present.
"""

import requests
import json
import sys
import time
from datetime import datetime

def test_populations_data():
    """Test populations data loading endpoint"""
    
    # API endpoint
    url = "http://localhost:8003/api/v1/populations/"
    
    print(f"Testing Populations Data Loading API")
    print(f"URL: {url}")
    print("-" * 50)
    
    try:
        # Send GET request
        print(f"Sending GET request to {url}...")
        start_time = time.time()
        
        response = requests.get(url, timeout=10)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"Response received in {response_time:.2f} seconds")
        print(f"Status Code: {response.status_code}")
        
        # Check if request was successful
        if response.status_code == 200:
            print("SUCCESS: Populations endpoint returned 200 OK")
            
            # Parse response
            try:
                response_data = response.json()
                print(f"Response is valid JSON")
                
                # Check if response is a list
                if isinstance(response_data, list):
                    print(f"Response is a list with {len(response_data)} populations")
                    
                    # Extract population names
                    population_names = []
                    for pop in response_data:
                        if isinstance(pop, dict) and "name" in pop:
                            population_names.append(pop["name"])
                    
                    print(f"Found populations: {population_names}")
                    
                    # Check for expected populations
                    expected_populations = ["California", "Myanmar", "Congo"]
                    found_populations = []
                    missing_populations = []
                    
                    for expected in expected_populations:
                        found = False
                        for name in population_names:
                            if expected.lower() in name.lower():
                                found_populations.append(expected)
                                found = True
                                break
                        if not found:
                            missing_populations.append(expected)
                    
                    print(f"\nVerification Results:")
                    print(f"Expected populations: {expected_populations}")
                    print(f"Found populations: {found_populations}")
                    print(f"Missing populations: {missing_populations}")
                    
                    if not missing_populations:
                        print("SUCCESS: All expected populations are present")
                        return True
                    else:
                        print(f"WARNING: Missing populations: {missing_populations}")
                        return False
                        
                else:
                    print(f"WARNING: Response is not a list, got {type(response_data)}")
                    print(f"Response Data: {json.dumps(response_data, indent=2)}")
                    return False
                    
            except json.JSONDecodeError:
                print("WARNING: Response is not valid JSON")
                print(f"Raw Response: {response.text}")
                return False
                
        else:
            print(f"ERROR: Expected 200 OK, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Connection failed - is the server running on port 8003?")
        return False
        
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request failed: {e}")
        return False
        
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False

def test_populations_statistics():
    """Test populations statistics endpoint"""
    
    url = "http://localhost:8003/api/v1/populations/statistics/overall"
    
    print(f"\nTesting Populations Statistics Endpoint")
    print(f"URL: {url}")
    print("-" * 50)
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print("Populations statistics endpoint working")
            response_data = response.json()
            print(f"Statistics Response: {json.dumps(response_data, indent=2)}")
            
            # Check for expected fields
            if "total_populations" in response_data:
                print(f"Total populations: {response_data['total_populations']}")
            else:
                print("WARNING: No 'total_populations' field in response")
                
            if "active_populations" in response_data:
                print(f"Active populations: {response_data['active_populations']}")
            else:
                print("WARNING: No 'active_populations' field in response")
                
            return True
        else:
            print(f"Statistics endpoint returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Could not check populations statistics: {e}")
        return False

def test_populations_health():
    """Test populations health endpoint"""
    
    url = "http://localhost:8003/api/v1/populations/health"
    
    print(f"\nTesting Populations Health Endpoint")
    print(f"URL: {url}")
    print("-" * 50)
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print("Populations health endpoint working")
            response_data = response.json()
            print(f"Health Response: {json.dumps(response_data, indent=2)}")
            return True
        else:
            print(f"Health endpoint returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Could not check populations health: {e}")
        return False

def main():
    """Main test function"""
    print(f"Vajra.Stream Data Loading Test")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 50)
    
    # Test populations data loading
    data_success = test_populations_data()
    
    # Test populations statistics
    stats_success = test_populations_statistics()
    
    # Test populations health
    health_success = test_populations_health()
    
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)
    
    if data_success:
        print("Populations Data Loading Test: PASSED")
    else:
        print("Populations Data Loading Test: FAILED")
        
    if stats_success:
        print("Populations Statistics Test: PASSED")
    else:
        print("Populations Statistics Test: FAILED")
        
    if health_success:
        print("Populations Health Test: PASSED")
    else:
        print("Populations Health Test: FAILED")
    
    overall_success = data_success and stats_success and health_success
    
    if overall_success:
        print("\nOVERALL RESULT: ALL TESTS PASSED")
        print("Data loading functionality is working correctly")
        return 0
    else:
        print("\nOVERALL RESULT: SOME TESTS FAILED")
        print("Data loading functionality needs attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())