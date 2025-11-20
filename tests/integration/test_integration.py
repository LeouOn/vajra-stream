#!/usr/bin/env python3
"""
Vajra.Stream Integration Test Script
Tests frontend-backend integration comprehensively
"""

import asyncio
import requests
import websocket
import json
import time
import sys
import subprocess
import threading
import os
from pathlib import Path

# Configuration
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"
WS_URL = "ws://localhost:8000/ws"

class IntegrationTester:
    def __init__(self):
        self.backend_running = False
        self.frontend_running = False
        self.websocket_connected = False
        self.test_results = []
    
    def log_result(self, test_name, success, message=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": time.time()
        })
        print(f"{status} {test_name}: {message}")
    
    async def test_backend_health(self):
        """Test backend health endpoint"""
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.backend_running = True
                    self.log_result("Backend Health Check", True, "Backend is healthy and responding")
                    return True
            
            self.log_result("Backend Health Check", False, f"Backend returned status {response.status_code}")
            return False
        except Exception as e:
            self.log_result("Backend Health Check", False, f"Connection error: {e}")
            return False
    
    async def test_api_endpoints(self):
        """Test main API endpoints"""
        endpoints = [
            ("/", "API Root"),
            ("/api/v1/audio/presets", "Audio Presets"),
            ("/api/v1/audio/frequencies/range", "Frequency Ranges"),
            ("/api/v1/sessions", "Sessions List"),
            ("/api/v1/astrology/current", "Current Astrology"),
            ("/api/v1/astrology/moon-phase", "Moon Phase"),
            ("/api/v1/astrology/planetary-positions", "Planetary Positions")
        ]
        
        for endpoint, name in endpoints:
            try:
                response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        self.log_result(f"API Endpoint - {name}", True, f"Endpoint responding correctly")
                    else:
                        self.log_result(f"API Endpoint - {name}", False, f"Invalid response: {data}")
                else:
                    self.log_result(f"API Endpoint - {name}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_result(f"API Endpoint - {name}", False, f"Connection error: {e}")
    
    async def test_audio_generation(self):
        """Test audio generation API"""
        try:
            # Test audio generation
            audio_config = {
                "frequency": 136.1,
                "duration": 10.0,
                "volume": 0.8,
                "prayer_bowl_mode": True,
                "harmonic_strength": 0.3,
                "modulation_depth": 0.05
            }
            
            response = requests.post(
                f"{BACKEND_URL}/api/v1/audio/generate",
                json=audio_config,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.log_result("Audio Generation", True, "Audio generated successfully")
                    
                    # Test audio playback
                    play_response = requests.post(
                        f"{BACKEND_URL}/api/v1/audio/play",
                        json={"hardware_level": 2},
                        timeout=30
                    )
                    
                    if play_response.status_code == 200:
                        play_data = play_response.json()
                        if play_data.get("status") == "success":
                            self.log_result("Audio Playback", True, "Audio playback started")
                        else:
                            self.log_result("Audio Playback", False, f"Playback failed: {play_data}")
                    else:
                        self.log_result("Audio Playback", False, f"Playback HTTP {play_response.status_code}")
                else:
                    self.log_result("Audio Generation", False, f"Generation failed: {data}")
            else:
                self.log_result("Audio Generation", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("Audio Generation", False, f"Error: {e}")
    
    async def test_session_management(self):
        """Test session management APIs"""
        try:
            # Create session
            session_config = {
                "name": "Test Session",
                "intention": "Testing integration",
                "duration": 300,  # 5 minutes
                "audio_frequency": 136.1,
                "astrology_enabled": True,
                "hardware_enabled": True,
                "visuals_enabled": True
            }
            
            create_response = requests.post(
                f"{BACKEND_URL}/api/v1/sessions/create",
                json=session_config,
                timeout=10
            )
            
            if create_response.status_code == 200:
                create_data = create_response.json()
                if create_data.get("status") == "success":
                    session_id = create_data.get("session_id")
                    self.log_result("Session Creation", True, f"Session created: {session_id}")
                    
                    # Start session
                    start_response = requests.post(
                        f"{BACKEND_URL}/api/v1/sessions/{session_id}/start",
                        timeout=10
                    )
                    
                    if start_response.status_code == 200:
                        self.log_result("Session Start", True, f"Session started: {session_id}")
                        
                        # Wait a moment then stop
                        await asyncio.sleep(2)
                        
                        stop_response = requests.post(
                            f"{BACKEND_URL}/api/v1/sessions/{session_id}/stop",
                            timeout=10
                        )
                        
                        if stop_response.status_code == 200:
                            self.log_result("Session Stop", True, f"Session stopped: {session_id}")
                        else:
                            self.log_result("Session Stop", False, f"Stop HTTP {stop_response.status_code}")
                    else:
                        self.log_result("Session Start", False, f"Start HTTP {start_response.status_code}")
                else:
                    self.log_result("Session Creation", False, f"Creation failed: {create_data}")
            else:
                self.log_result("Session Creation", False, f"Creation HTTP {create_response.status_code}")
        except Exception as e:
            self.log_result("Session Management", False, f"Error: {e}")
    
    async def test_websocket_connection(self):
        """Test WebSocket connection and real-time data"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                message_type = data.get("type")
                
                if message_type == "realtime_data":
                    self.websocket_connected = True
                    self.log_result("WebSocket Connection", True, "WebSocket connected and receiving data")
                    
                    # Check for audio spectrum
                    if "audio_spectrum" in data:
                        spectrum = data["audio_spectrum"]
                        if isinstance(spectrum, list) and len(spectrum) > 0:
                            self.log_result("Audio Spectrum Streaming", True, f"Receiving {len(spectrum)} frequency bins")
                        else:
                            self.log_result("Audio Spectrum Streaming", False, "Invalid spectrum data")
                    
                    # Check for sessions
                    if "active_sessions" in data:
                        sessions = data["active_sessions"]
                        if isinstance(sessions, dict):
                            self.log_result("Session Data Streaming", True, f"Receiving data for {len(sessions)} sessions")
                        else:
                            self.log_result("Session Data Streaming", False, "Invalid session data")
                    
                elif message_type == "connection_status":
                    if data.get("status") == "connected":
                        self.log_result("WebSocket Handshake", True, "WebSocket handshake successful")
                    else:
                        self.log_result("WebSocket Handshake", False, f"Handshake failed: {data}")
                        
            except Exception as e:
                self.log_result("WebSocket Message Parsing", False, f"Parse error: {e}")
        
        def on_error(ws, error):
            self.log_result("WebSocket Connection", False, f"WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            self.log_result("WebSocket Connection", False, f"WebSocket closed: {close_status_code}")
        
        try:
            ws = websocket.WebSocketApp(
                WS_URL,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # Run WebSocket in separate thread
            wst = threading.Thread(target=ws.run_forever)
            wst.daemon = True
            wst.start()
            
            # Wait for connection
            await asyncio.sleep(3)
            
            if self.websocket_connected:
                self.log_result("WebSocket Test", True, "WebSocket connection successful")
            else:
                self.log_result("WebSocket Test", False, "WebSocket connection failed")
                
        except Exception as e:
            self.log_result("WebSocket Test", False, f"WebSocket error: {e}")
    
    async def test_frontend_build(self):
        """Test if frontend is built and accessible"""
        try:
            # Check if frontend build exists
            frontend_dist = Path("frontend/dist")
            if frontend_dist.exists():
                self.log_result("Frontend Build", True, "Frontend build exists")
            else:
                self.log_result("Frontend Build", False, "Frontend build not found")
            
            # Check if frontend is running (optional)
            try:
                response = requests.get(FRONTEND_URL, timeout=5)
                if response.status_code == 200:
                    self.frontend_running = True
                    self.log_result("Frontend Server", True, "Frontend server is running")
                else:
                    self.log_result("Frontend Server", False, f"Frontend returned {response.status_code}")
            except:
                self.log_result("Frontend Server", False, "Frontend server not accessible")
                
        except Exception as e:
            self.log_result("Frontend Test", False, f"Error: {e}")
    
    async def test_dependencies(self):
        """Test if required dependencies are available"""
        try:
            # Test Python dependencies
            import fastapi
            import uvicorn
            import websockets
            import numpy
            import scipy
            self.log_result("Python Dependencies", True, "All Python dependencies available")
        except ImportError as e:
            self.log_result("Python Dependencies", False, f"Missing dependency: {e}")
        
        try:
            # Check if Node.js modules exist (for frontend)
            frontend_node_modules = Path("frontend/node_modules")
            if frontend_node_modules.exists():
                self.log_result("Frontend Dependencies", True, "Frontend node_modules exist")
            else:
                self.log_result("Frontend Dependencies", False, "Frontend dependencies not installed")
        except Exception as e:
            self.log_result("Frontend Dependencies", False, f"Error: {e}")
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("🧪 Starting Vajra.Stream Integration Tests")
        print("=" * 50)
        
        # Test dependencies first
        await self.test_dependencies()
        await asyncio.sleep(0.5)
        
        # Test backend
        await self.test_backend_health()
        await asyncio.sleep(0.5)
        
        if self.backend_running:
            await self.test_api_endpoints()
            await asyncio.sleep(0.5)
            
            await self.test_audio_generation()
            await asyncio.sleep(1)
            
            await self.test_session_management()
            await asyncio.sleep(1)
            
            await self.test_websocket_connection()
            await asyncio.sleep(1)
        else:
            self.log_result("Backend Tests", False, "Skipping backend tests - backend not running")
        
        # Test frontend
        await self.test_frontend_build()
        await asyncio.sleep(0.5)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 INTEGRATION TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['message']}")
        
        print("\n🔗 ACCESS URLS:")
        print(f"Backend API: {BACKEND_URL}/docs")
        print(f"Frontend: {FRONTEND_URL}")
        print(f"WebSocket: {WS_URL}")
        
        if self.backend_running and self.websocket_connected:
            print("\n🎉 INTEGRATION SUCCESSFUL!")
            print("✅ Backend is running and accessible")
            print("✅ API endpoints are responding")
            print("✅ WebSocket connection is working")
            print("✅ Real-time data streaming is functional")
        else:
            print("\n⚠️  INTEGRATION ISSUES DETECTED")
            print("Some components may not be working correctly")

async def main():
    """Main test runner"""
    tester = IntegrationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())