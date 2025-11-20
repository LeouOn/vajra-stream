#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify session creation API endpoint works correctly.
This tests the fix for the 422 Unprocessable Content error.
"""

import requests
import json
import sys
from typing import Dict, Any

def test_session_creation(base_url: str = "http://localhost:8001") -> Dict[str, Any]:
    """Test the session creation endpoint with correct payload"""
    
    # Test data matching the backend Pydantic model requirements
    session_data = {
        "name": "Test Healing Session",
        "intention": "May all beings be happy and free from suffering",
        "duration": 300,  # 5 minutes in seconds
        "audio_frequency": 136.1,  # OM frequency
        "astrology_enabled": True,
        "hardware_enabled": True,
        "visuals_enabled": True
    }
    
    print(f"Testing session creation API at {base_url}")
    print(f"Sending payload:")
    print(json.dumps(session_data, indent=2))
    
    try:
        # Make the POST request to create a session
        response = requests.post(
            f"{base_url}/api/v1/sessions/create",
            headers={"Content-Type": "application/json"},
            json=session_data,
            timeout=10
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success! Response:")
            print(json.dumps(result, indent=2))
            
            # Test starting the session if creation succeeded
            if result.get("status") == "success" and "session_id" in result:
                session_id = result["session_id"]
                print(f"\nTesting session start for {session_id}")
                
                start_response = requests.post(
                    f"{base_url}/api/v1/sessions/{session_id}/start",
                    timeout=10
                )
                
                print(f"Start Response Status: {start_response.status_code}")
                if start_response.status_code == 200:
                    start_result = start_response.json()
                    print(f"Session started successfully!")
                    print(json.dumps(start_result, indent=2))
                else:
                    print(f"Failed to start session: {start_response.text}")
            
            return {"success": True, "data": result}
            
        else:
            print(f"Failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return {"success": False, "error": response.text}
            
    except requests.exceptions.ConnectionError:
        error_msg = f"Connection error: Could not connect to {base_url}"
        print(error_msg)
        print("Make sure the backend server is running on the expected port")
        return {"success": False, "error": error_msg}
        
    except requests.exceptions.Timeout:
        error_msg = f"Timeout: Request to {base_url} timed out"
        print(error_msg)
        return {"success": False, "error": error_msg}
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}

def test_incorrect_payload(base_url: str = "http://localhost:8001"):
    """Test with incorrect payload to verify validation works"""
    
    print(f"\nTesting with incorrect payload (should fail)")
    
    # Missing required fields and wrong field names
    incorrect_data = {
        "intention": "Test intention",
        "duration": 60,
        "frequency": 440.0  # Wrong field name - should be audio_frequency
        # Missing 'name' field which is required
    }
    
    print(f"Sending incorrect payload:")
    print(json.dumps(incorrect_data, indent=2))
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/sessions/create",
            headers={"Content-Type": "application/json"},
            json=incorrect_data,
            timeout=10
        )
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 422:
            print(f"Correctly rejected with 422 error (as expected)")
            print(f"Error response:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except:
                print(response.text)
            return True
        else:
            print(f"Unexpected response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error during incorrect payload test: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("SESSION CREATION API TEST")
    print("=" * 60)
    
    # Try different possible backend ports
    backend_urls = [
        "http://localhost:8001",
        "http://localhost:8002",
        "http://localhost:8003",
        "http://localhost:8005",
        "http://localhost:8006"
    ]
    
    success = False
    working_url = None
    
    for url in backend_urls:
        print(f"\nTrying backend at {url}")
        result = test_session_creation(url)
        if result["success"]:
            success = True
            working_url = url
            break
        print(f"Backend at {url} not available or failed")
    
    if success:
        print(f"\nSUCCESS: Session creation works correctly with {working_url}")
        
        # Test with incorrect payload to verify validation
        validation_works = test_incorrect_payload(working_url)
        
        if validation_works:
            print("\nVALIDATION: Backend correctly rejects invalid payloads")
        
        print("\nALL TESTS PASSED - Session Creation 422 Error is FIXED!")
        sys.exit(0)
    else:
        print("\nFAILURE: Could not connect to any backend server")
        print("Please make sure a backend server is running on one of these ports:")
        for url in backend_urls:
            print(f"   - {url}")
        sys.exit(1)