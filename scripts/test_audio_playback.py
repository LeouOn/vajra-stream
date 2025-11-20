#!/usr/bin/env python3
"""
Test Audio Playback API Endpoint

This script tests the audio playback functionality by sending a POST request
to the /api/v1/audio/play endpoint with a sample payload.
"""

import requests
import json
import sys
import time
from datetime import datetime

def test_audio_generate():
    """Test audio generation endpoint first"""
    
    # API endpoint
    url = "http://localhost:8003/api/v1/audio/generate"
    
    # Test payload
    payload = {
        "frequency": 528,
        "duration": 5,
        "volume": 0.8,
        "prayer_bowl_mode": True,
        "harmonic_strength": 0.3,
        "modulation_depth": 0.05
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Testing Audio Generation API")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 50)
    
    try:
        # Send POST request
        print(f"Sending POST request to {url}...")
        start_time = time.time()
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"Response received in {response_time:.2f} seconds")
        print(f"Status Code: {response.status_code}")
        
        # Check if request was successful
        if response.status_code == 200:
            print("SUCCESS: Audio generation endpoint returned 200 OK")
            
            # Parse response
            try:
                response_data = response.json()
                print(f"Response Data: {json.dumps(response_data, indent=2)}")
                
                # Check for expected fields
                if "status" in response_data:
                    print(f"Status field found: {response_data['status']}")
                else:
                    print("WARNING: No 'status' field in response")
                    
                if "message" in response_data:
                    print(f"Message field found: {response_data['message']}")
                else:
                    print("WARNING: No 'message' field in response")
                    
                return True
                
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

def test_audio_playback():
    """Test audio playback endpoint"""
    
    # API endpoint
    url = "http://localhost:8003/api/v1/audio/play"
    
    # Test payload
    payload = {
        "hardware_level": 2
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"\nTesting Audio Playback API")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 50)
    
    try:
        # Send POST request
        print(f"Sending POST request to {url}...")
        start_time = time.time()
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"Response received in {response_time:.2f} seconds")
        print(f"Status Code: {response.status_code}")
        
        # Check if request was successful
        if response.status_code == 200:
            print("SUCCESS: Audio playback endpoint returned 200 OK")
            
            # Parse response
            try:
                response_data = response.json()
                print(f"Response Data: {json.dumps(response_data, indent=2)}")
                
                # Check for expected fields
                if "status" in response_data:
                    print(f"Status field found: {response_data['status']}")
                else:
                    print("WARNING: No 'status' field in response")
                    
                if "message" in response_data:
                    print(f"Message field found: {response_data['message']}")
                else:
                    print("WARNING: No 'message' field in response")
                    
                return True
                
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

def test_audio_status():
    """Test audio status endpoint to verify playback state"""
    
    url = "http://localhost:8003/api/v1/audio/status"
    
    print(f"\nTesting Audio Status Endpoint")
    print(f"URL: {url}")
    print("-" * 50)
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print("Audio status endpoint working")
            response_data = response.json()
            print(f"Status Response: {json.dumps(response_data, indent=2)}")
            return True
        else:
            print(f"Status endpoint returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Could not check audio status: {e}")
        return False

def main():
    """Main test function"""
    print(f"Vajra.Stream Audio Playback Test")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 50)
    
    # Test audio generation first
    generate_success = test_audio_generate()
    
    # Test audio playback
    playback_success = test_audio_playback()
    
    # Test audio status
    status_success = test_audio_status()
    
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)
    
    if generate_success:
        print("Audio Generation Test: PASSED")
    else:
        print("Audio Generation Test: FAILED")
        
    if playback_success:
        print("Audio Playback Test: PASSED")
    else:
        print("Audio Playback Test: FAILED")
        
    if status_success:
        print("Audio Status Test: PASSED")
    else:
        print("Audio Status Test: FAILED")
    
    overall_success = generate_success and playback_success and status_success
    
    if overall_success:
        print("\nOVERALL RESULT: ALL TESTS PASSED")
        print("Audio playback functionality is working correctly")
        return 0
    else:
        print("\nOVERALL RESULT: SOME TESTS FAILED")
        print("Audio playback functionality needs attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())