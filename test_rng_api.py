#!/usr/bin/env python3
"""
Test script for RNG Attunement API Endpoints
Tests all REST API endpoints
"""

import asyncio
import httpx
import time


API_BASE = "http://localhost:8001/api/v1"


async def test_rng_api():
    """Test RNG Attunement API endpoints"""

    print("=" * 60)
    print("RNG Attunement API Test")
    print("=" * 60)
    print()
    print(f"Testing API at: {API_BASE}")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:

        # Test 1: Health Check
        print("1. Testing health check endpoint...")
        try:
            response = await client.get(f"{API_BASE}/rng-attunement/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {data}")
                print("   ✅ Health check passed")
            else:
                print(f"   ❌ Health check failed")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        print()

        # Test 2: Create Session
        print("2. Testing session creation...")
        try:
            response = await client.post(
                f"{API_BASE}/rng-attunement/session/create",
                json={
                    "baseline_tone_arm": 5.0,
                    "sensitivity": 1.0
                }
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                session_id = data["session_id"]
                print(f"   Session ID: {session_id}")
                print("   ✅ Session created")
            else:
                print(f"   ❌ Session creation failed")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        print()

        # Test 3: Get Readings (multiple)
        print("3. Testing reading generation (10 readings)...")
        try:
            for i in range(10):
                response = await client.get(
                    f"{API_BASE}/rng-attunement/reading/{session_id}"
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"   Reading {i+1}:")
                    print(f"     Tone Arm:     {data['tone_arm']:.2f}")
                    print(f"     Needle Pos:   {data['needle_position']:+6.1f}")
                    print(f"     Needle State: {data['needle_state'].upper()}")
                    print(f"     Quality:      {data['quality'].upper()}")
                    print(f"     FN Score:     {data['floating_needle_score']:.3f}")

                    if data['needle_state'] == 'floating':
                        print(f"     🎯 FLOATING NEEDLE!")

                    # Small delay between readings
                    await asyncio.sleep(0.1)
                else:
                    print(f"   ❌ Reading {i+1} failed: {response.status_code}")
                    return False

            print("   ✅ All readings generated successfully")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        print()

        # Test 4: Get Session Summary
        print("4. Testing session summary...")
        try:
            response = await client.get(
                f"{API_BASE}/rng-attunement/session/{session_id}/summary"
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Summary:")
                print(f"     Total Readings:   {data['total_readings']}")
                print(f"     Floating Needles: {data['floating_needle_count']}")
                print(f"     Avg Tone Arm:     {data['avg_tone_arm']:.2f}")
                print(f"     Avg Coherence:    {data['avg_coherence']:.3f}")
                print(f"     Is Active:        {data['is_active']}")
                print("   ✅ Summary retrieved successfully")
            else:
                print(f"   ❌ Summary retrieval failed")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        print()

        # Test 5: Get All Sessions
        print("5. Testing session list...")
        try:
            response = await client.get(f"{API_BASE}/rng-attunement/sessions")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                sessions = response.json()
                print(f"   Active sessions: {len(sessions)}")
                print(f"   Session IDs: {sessions[:3]}...")  # Show first 3
                print("   ✅ Session list retrieved")
            else:
                print(f"   ❌ Session list failed")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        print()

        # Test 6: Get Needle States Info
        print("6. Testing needle states info...")
        try:
            response = await client.get(
                f"{API_BASE}/rng-attunement/info/needle-states"
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                states = response.json()
                print(f"   Needle states available: {len(states)}")
                for state in states[:3]:  # Show first 3
                    print(f"     - {state['state']}: {state['description'][:50]}...")
                print("   ✅ Needle states info retrieved")
            else:
                print(f"   ❌ Needle states info failed")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        print()

        # Test 7: Get Quality Levels Info
        print("7. Testing quality levels info...")
        try:
            response = await client.get(
                f"{API_BASE}/rng-attunement/info/quality-levels"
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                levels = response.json()
                print(f"   Quality levels available: {len(levels)}")
                for level in levels[:3]:  # Show first 3
                    print(f"     - {level['quality']}: {level['description'][:50]}...")
                print("   ✅ Quality levels info retrieved")
            else:
                print(f"   ❌ Quality levels info failed")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        print()

        # Test 8: Stop Session
        print("8. Testing session stop...")
        try:
            response = await client.post(
                f"{API_BASE}/rng-attunement/session/{session_id}/stop"
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {data}")
                print("   ✅ Session stopped successfully")
            else:
                print(f"   ❌ Session stop failed")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        print()

        # Test 9: Verify stopped session returns 404
        print("9. Testing reading after session stop...")
        try:
            response = await client.get(
                f"{API_BASE}/rng-attunement/reading/{session_id}"
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 404:
                print("   ✅ Correctly returns 404 for stopped session")
            else:
                print(f"   ❌ Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        print()

    print("=" * 60)
    print("TEST RESULT: ✅ ALL API TESTS PASSED")
    print("=" * 60)
    print()

    return True


if __name__ == "__main__":
    try:
        print("Starting API tests...")
        print("NOTE: Make sure the backend server is running:")
        print("  uvicorn backend.app.main:app --reload --port 8001")
        print()

        success = asyncio.run(test_rng_api())

        import sys
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH EXCEPTION:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1)
