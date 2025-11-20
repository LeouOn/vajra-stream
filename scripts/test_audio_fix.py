 #!/usr/bin/env python3
"""
Simple test script to verify backend audio playback functionality
"""

import sys
import os
import asyncio
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_audio_service():
    """Test audio service directly"""
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
            "duration": 3.0,     # 3 seconds
            "intention": "testing audio playback",
            "pure_sine": False
        }
        
        result = await audio_service.generate_audio(config)
        
        if "error" in result:
            print(f"FAIL: Audio generation failed: {result['error']}")
            return False
        else:
            print(f"PASS: Audio generated successfully: {result['duration']}s at {result['frequency']}Hz")
            print(f"   Sample count: {len(result['audio_data'])}")
            
            # Test audio playback
            print("\n2. Testing audio playback...")
            print("   You should hear audio playing through your system speakers...")
            playback_result = await audio_service.play_audio(result['audio_data'])
            
            if "error" in playback_result:
                print(f"FAIL: Audio playback failed: {playback_result['error']}")
                return False
            else:
                print(f"PASS: Audio playback status: {playback_result['status']}")
                print(f"   Message: {playback_result['message']}")
                
                # Wait for playback to complete
                print("   Waiting for audio to play...")
                await asyncio.sleep(4)  # Wait a bit longer than audio duration
                
                # Check if still playing
                status = audio_service.get_status()
                print(f"   Final status: {'Playing' if status['is_playing'] else 'Stopped'}")
                
                return True
                
    except Exception as e:
        print(f"ERROR: Error testing audio service: {e}")
        return False

async def test_vajra_service():
    """Test vajra service audio functionality"""
    print("\n" + "="*60)
    print("TESTING VAJRA SERVICE AUDIO")
    print("="*60)
    
    try:
        from backend.core.services.vajra_service import vajra_service, AudioConfig
        
        # Test audio generation and playback
        print("\n1. Testing prayer bowl audio generation...")
        config = AudioConfig(
            frequency=136.1,  # OM frequency
            duration=3.0,      # 3 seconds
            volume=0.8,
            prayer_bowl_mode=True,
            harmonic_strength=0.3,
            modulation_depth=0.05
        )
        
        audio_data = await vajra_service.generate_prayer_bowl_audio(config)
        
        if audio_data is None:
            print("FAIL: Audio generation failed")
            return False
        else:
            print(f"PASS: Prayer bowl audio generated successfully")
            print(f"   Shape: {audio_data.shape}")
            print(f"   Duration: {len(audio_data) / 44100:.2f} seconds")
            
            # Test audio broadcasting
            print("\n2. Testing audio broadcast...")
            print("   You should hear audio playing through your system speakers...")
            
            success = await vajra_service.broadcast_audio(audio_data, hardware_level=2)
            
            if success:
                print("PASS: Audio broadcast successful")
                print("   Waiting for playback to complete...")
                await asyncio.sleep(4)  # Wait for audio to finish
                return True
            else:
                print("FAIL: Audio broadcast failed")
                return False
                
    except Exception as e:
        print(f"ERROR: Error testing vajra service: {e}")
        return False

async def main():
    """Main test function"""
    print("\n" + "="*60)
    print("BACKEND AUDIO PLAYBACK TEST")
    print("="*60)
    print("\nThis test verifies that backend can produce audible sound")
    print("through system speakers using the sounddevice library.")
    print("\nPlease ensure your speakers/headphones are connected and volume is at a comfortable level.")
    
    # Run tests
    test1 = await test_audio_service()
    await asyncio.sleep(1)
    test2 = await test_vajra_service()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    print(f"Audio Service: {'PASS' if test1 else 'FAIL'}")
    print(f"Vajra Service: {'PASS' if test2 else 'FAIL'}")
    
    if test1 and test2:
        print("\nSUCCESS: All tests passed! The backend should now play audio through system speakers.")
        print("If you didn't hear audio, please check:")
        print("• Speakers/headphones are connected and powered on")
        print("• System volume is at an appropriate level")
        print("• No other applications are blocking audio output")
    else:
        print("\nWARNING: Some tests failed. Please check error messages above.")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\nError running tests: {e}")