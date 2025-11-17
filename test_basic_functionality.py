#!/usr/bin/env python3
"""
Simple test script to verify Vajra Stream core functionality
Tests modules without requiring all optional dependencies
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_container():
    """Test that the container initializes"""
    print("🧪 Testing Container Initialization...")
    try:
        from container import container
        print("  ✅ Container imported successfully")

        # Test scalar waves
        print("\n🧪 Testing Scalar Waves Service...")
        status = container.scalar_waves.get_status()
        print(f"  ✅ Scalar Waves: {status}")

        # Test radionics
        print("\n🧪 Testing Radionics Service...")
        intentions = container.radionics.get_available_intentions()
        print(f"  ✅ Radionics: {len(intentions)} intentions available")

        # Test blessings
        print("\n🧪 Testing Blessings Service...")
        mantras = container.blessings.get_available_mantras()
        print(f"  ✅ Blessings: {len(mantras)} mantras available")

        return True
    except Exception as e:
        print(f"  ❌ Container test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_visualization_module():
    """Test visualization module (requires PIL)"""
    print("\n🧪 Testing Visualization Module...")
    try:
        from modules.visualization import VisualizationService
        viz = VisualizationService()
        status = viz.get_status()
        print(f"  ✅ Visualization module loaded")
        print(f"     Rothko available: {status.get('rothko_available')}")
        print(f"     Energetic viz available: {status.get('energetic_viz_available')}")
        return True
    except Exception as e:
        print(f"  ❌ Visualization test failed: {e}")
        return False


def test_anatomy_module():
    """Test anatomy module (requires PIL)"""
    print("\n🧪 Testing Anatomy Module...")
    try:
        from modules.anatomy import AnatomyService
        anatomy = AnatomyService()
        print(f"  ✅ Anatomy module loaded")
        print(f"     Visualization available: {anatomy.has_visualization}")
        return True
    except Exception as e:
        print(f"  ❌ Anatomy test failed: {e}")
        return False


def test_audio_module():
    """Test audio module (optional dependencies)"""
    print("\n🧪 Testing Audio Module...")
    try:
        from modules.audio import AudioService
        audio = AudioService()
        status = audio.get_status()
        print(f"  ✅ Audio module loaded")
        print(f"     Audio generator: {status['audio_generator']}")
        print(f"     TTS: {status['tts']}")
        return True
    except Exception as e:
        print(f"  ❌ Audio test failed: {e}")
        return False


def test_api_imports():
    """Test that API endpoints can be imported"""
    print("\n🧪 Testing API Endpoint Imports...")
    try:
        from backend.app.main import app
        print("  ✅ FastAPI app imported successfully")
        return True
    except Exception as e:
        print(f"  ❌ API import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("🔱 Vajra Stream - Basic Functionality Tests")
    print("=" * 60)
    print()

    results = {
        "Container": test_container(),
        "Visualization": test_visualization_module(),
        "Anatomy": test_anatomy_module(),
        "Audio": test_audio_module(),
        "API Imports": test_api_imports()
    }

    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name:20} {status}")

    passed = sum(results.values())
    total = len(results)

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! System is ready to use!")
        print("\nNext steps:")
        print("  1. Start the server: python start_web_server.py")
        print("  2. Open browser: http://localhost:8001/visualizations")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        print("\nMost likely issues:")
        print("  • PIL/Pillow not installed: pip install pillow")
        print("  • FastAPI not installed: pip install -r requirements-minimal.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
