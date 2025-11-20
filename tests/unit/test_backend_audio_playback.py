#!/usr/bin/env python3
"""
Test script to verify backend audio playback functionality
Tests both the audio service and vajra service implementations
"""

import sys
import os
import asyncio
import time
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_audio_service():
    """Test the audio service directly"""
    print("\n" + "="*60)
    print("TESTING BACKEND AUDIO SERVICE")
    print("="*60)
    
    try:
        from backend.core.services.audio_service import audio_service
        
        # Test audio generation
        print("\n1. Testing audio generation...")
        config = {
            "type": "prayer_bowl",
            "frequency": 528.0,  # Love frequency
            "duration": 5.0,     # 5 seconds
            "intention": "testing audio playback",
            "pure_sine": False
        }
        
        result = await audio_service.generate_audio(config)
        
        if "error" in result:
            print(f"❌ Audio generation failed: {result['error']}")
            return False
        else:
            print(f"✅ Audio generated successfully: {result['duration']}s at {result['frequency']}Hz")
            print(f"   Sample count: {len(result['audio_data'])}")
            
            # Test audio playback
            print("\n2. Testing audio playback...")
            playback_result = await audio_service.play_audio(result['audio_data'])
            
            if "error" in playback_result:
                print(f"❌ Audio playback failed: {playback_result['error']}")
                return False
            else:
                print(f"✅ Audio playback status: {playback_result['status']}")
                print(f"   Message: {playback_result['message']}")
                
                # Wait for playback to complete
                print("   Waiting for audio to play...")
                await asyncio.sleep(6)  # Wait a bit longer than the audio duration
                
                # Check if still playing
                status = audio_service.get_status()
                print(f"   Final status: {'Playing' if status['is_playing'] else 'Stopped'}")
                
                return True
                
    except Exception as e:
        print(f"❌ Error testing audio service: {e}")
        return False

async def test_vajra_service():
    """Test the vajra service audio functionality"""
    print("\n" + "="*60)
    print("TESTING VAJRA SERVICE AUDIO")
    print("="*60)
    
    try:
        from backend.core.services.vajra_service import vajra_service, AudioConfig
        
        # Test audio generation and playback
        print("\n1. Testing prayer bowl audio generation...")
        config = AudioConfig(
            frequency=136.1,  # OM frequency
            duration=5.0,      # 5 seconds
            volume=0.8,
            prayer_bowl_mode=True,
            harmonic_strength=0.3,
            modulation_depth=0.05
        )
        
        audio_data = await vajra_service.generate_prayer_bowl_audio(config)
        
        if audio_data is None:
            print("❌ Audio generation failed")
            return False
        else:
            print(f"✅ Prayer bowl audio generated successfully")
            print(f"   Shape: {audio_data.shape}")
            print(f"   Duration: {len(audio_data) / 44100:.2f} seconds")
            
            # Test audio broadcasting
            print("\n2. Testing audio broadcast...")
            print("   You should hear audio playing through your system speakers...")
            
            success = await vajra_service.broadcast_audio(audio_data, hardware_level=2)
            
            if success:
                print("✅ Audio broadcast successful")
                print("   Waiting for playback to complete...")
                await asyncio.sleep(6)  # Wait for audio to finish
                return True
            else:
                print("❌ Audio broadcast failed")
                return False
                
    except Exception as e:
        print(f"❌ Error testing vajra service: {e}")
        return False

async def test_api_endpoints():
    """Test the API endpoints for audio functionality"""
    print("\n" + "="*60)
    print("TESTING API ENDPOINTS")
    print("="*60)
    
    try:
        import aiohttp
        import json
        
        # Test the generate endpoint
        print("\n1. Testing audio generation endpoint...")
        
        async with aiohttp.ClientSession() as session:
            # Generate audio
            generate_data = {
                "frequency": 432.0,
                "duration": 3.0,
                "volume": 0.7,
                "prayer_bowl_mode": True,
                "harmonic_strength": 0.3,
                "modulation_depth": 0.05
            }
            
            async with session.post(
                'http://localhost:8001/api/v1/audio/generate',
                json=generate_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Audio generation endpoint: {result['status']}")
                    print(f"   Message: {result['message']}")
                    
                    # Wait a moment for generation
                    await asyncio.sleep(2)
                    
                    # Test playback endpoint
                    print("\n2. Testing audio playback endpoint...")
                    print("   You should hear audio playing through your system speakers...")
                    
                    play_data = {"hardware_level": 2}
                    
                    async with session.post(
                        'http://localhost:8001/api/v1/audio/play',
                        json=play_data
                    ) as play_response:
                        if play_response.status == 200:
                            play_result = await play_response.json()
                            print(f"✅ Audio playback endpoint: {play_result['status']}")
                            print(f"   Message: {play_result['message']}")
                            print(f"   Hardware level: {play_result['hardware_level']}")
                            print(f"   Audio duration: {play_result['audio_duration']:.2f}s")
                            
                            # Wait for playback
                            print("   Waiting for playback to complete...")
                            await asyncio.sleep(5)
                            return True
                        else:
                            error_text = await play_response.text()
                            print(f"❌ Audio playback endpoint failed: {play_response.status} - {error_text}")
                            return False
                else:
                    error_text = await response.text()
                    print(f"❌ Audio generation endpoint failed: {response.status} - {error_text}")
                    return False
                    
    except ImportError:
        print("⚠️  aiohttp not available, skipping API endpoint tests")
        return True
    except Exception as e:
        print(f"❌ Error testing API endpoints: {e}")
        return False

async def main():
    """Main test function"""
    print("\n" + "="*60)
    print("BACKEND AUDIO PLAYBACK TEST SUITE")
    print("="*60)
    print("\nThis test verifies that the backend can produce audible sound")
    print("through the system speakers using the sounddevice library.")
    print("\nPlease ensure your speakers/headphones are connected and volume is at a comfortable level.")
    
    # Run all tests
    tests = [
        ("Audio Service", test_audio_service),
        ("Vajra Service", test_vajra_service),
        ("API Endpoints", test_api_endpoints)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"RUNNING: {test_name}")
        print(f"{'='*60}")
        
        try:
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                print(f"\n✅ {test_name} PASSED")
            else:
                print(f"\n❌ {test_name} FAILED")
                
        except Exception as e:
            print(f"\n❌ {test_name} ERROR: {e}")
            results.append((test_name, False))
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The backend should now play audio through system speakers.")
        print("If you didn't hear audio, please check:")
        print("• Speakers/headphones are connected and powered on")
        print("• System volume is at an appropriate level")
        print("• No other applications are blocking audio output")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\nError running tests: {e}")