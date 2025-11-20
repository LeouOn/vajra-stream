"""
WebSocket Stability Test Script
Tests connection stability over extended periods with various scenarios
"""

import asyncio
import websockets
import json
import time
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import statistics

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebSocketStabilityTester:
    def __init__(self, url: str = "ws://localhost:8008/ws"):
        self.url = url
        self.connections: List[websockets.WebSocketServerProtocol] = []
        self.stats = {
            'connections_made': 0,
            'connections_lost': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'reconnections': 0,
            'errors': 0,
            'connection_times': [],
            'message_latencies': [],
            'disconnection_codes': {},
            'test_start_time': None,
            'test_end_time': None
        }
        
    async def create_connection(self, connection_id: str) -> Dict[str, Any]:
        """Create a single WebSocket connection and track its statistics"""
        connection_stats = {
            'id': connection_id,
            'connected_at': None,
            'disconnected_at': None,
            'messages_sent': 0,
            'messages_received': 0,
            'latencies': [],
            'reconnect_count': 0,
            'errors': []
        }
        
        while True:  # Reconnection loop
            try:
                logger.info(f"Connection {connection_id}: Connecting to {self.url}")
                
                # Record connection attempt
                self.stats['connections_made'] += 1
                connection_stats['connected_at'] = time.time()
                
                async with websockets.connect(
                    self.url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                ) as websocket:
                    self.connections.append(websocket)
                    logger.info(f"Connection {connection_id}: Connected successfully")
                    
                    # Send initial message
                    await websocket.send(json.dumps({
                        "type": "ping",
                        "connection_id": connection_id,
                        "timestamp": time.time()
                    }))
                    connection_stats['messages_sent'] += 1
                    self.stats['messages_sent'] += 1
                    
                    # Message handling loop
                    try:
                        async for message in websocket:
                            try:
                                data = json.loads(message)
                                message_time = data.get('timestamp', time.time())
                                latency = time.time() - message_time
                                
                                connection_stats['messages_received'] += 1
                                connection_stats['latencies'].append(latency)
                                self.stats['messages_received'] += 1
                                self.stats['message_latencies'].append(latency)
                                
                                # Handle different message types
                                msg_type = data.get('type', 'unknown')
                                
                                if msg_type == 'connection_status':
                                    logger.info(f"Connection {connection_id}: Status - {data.get('status')}")
                                elif msg_type == 'pong':
                                    # Respond to ping
                                    pass
                                elif msg_type == 'realtime_data':
                                    # Track real-time data reception
                                    pass
                                elif msg_type == 'heartbeat':
                                    # Track heartbeat
                                    pass
                                else:
                                    logger.debug(f"Connection {connection_id}: Received {msg_type}")
                                    
                            except json.JSONDecodeError:
                                logger.warning(f"Connection {connection_id}: Invalid JSON received")
                                connection_stats['errors'].append("Invalid JSON")
                                self.stats['errors'] += 1
                                
                    except websockets.exceptions.ConnectionClosed as e:
                        connection_stats['disconnected_at'] = time.time()
                        connection_time = connection_stats['disconnected_at'] - connection_stats['connected_at']
                        self.stats['connection_times'].append(connection_time)
                        
                        # Track disconnection code
                        code_str = str(e.code)
                        self.stats['disconnection_codes'][code_str] = \
                            self.stats['disconnection_codes'].get(code_str, 0) + 1
                        
                        logger.warning(f"Connection {connection_id}: Closed with code {e.code}: {e.reason}")
                        self.stats['connections_lost'] += 1
                        
                        # Check if we should reconnect
                        if e.code == 1000:  # Normal closure
                            logger.info(f"Connection {connection_id}: Normal closure, not reconnecting")
                            break
                        else:
                            connection_stats['reconnect_count'] += 1
                            self.stats['reconnections'] += 1
                            
                            # Exponential backoff for reconnection
                            wait_time = min(2 ** connection_stats['reconnect_count'], 30)
                            logger.info(f"Connection {connection_id}: Reconnecting in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            
                    except Exception as e:
                        logger.error(f"Connection {connection_id}: Error - {e}")
                        connection_stats['errors'].append(str(e))
                        self.stats['errors'] += 1
                        await asyncio.sleep(5)  # Wait before retrying
                        
            except Exception as e:
                logger.error(f"Connection {connection_id}: Failed to connect - {e}")
                connection_stats['errors'].append(str(e))
                self.stats['errors'] += 1
                await asyncio.sleep(10)  # Wait before retrying
                
        return connection_stats
    
    async def run_stress_test(self, num_connections: int = 5, duration_minutes: int = 5):
        """Run stress test with multiple connections"""
        logger.info(f"Starting stress test: {num_connections} connections for {duration_minutes} minutes")
        self.stats['test_start_time'] = time.time()
        
        # Create connections
        tasks = []
        for i in range(num_connections):
            task = asyncio.create_task(self.create_connection(f"stress_{i}"))
            tasks.append(task)
            await asyncio.sleep(0.1)  # Stagger connections
        
        # Run for specified duration
        await asyncio.sleep(duration_minutes * 60)
        
        # Close connections
        for task in tasks:
            task.cancel()
        
        # Wait for tasks to complete
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            pass
        
        self.stats['test_end_time'] = time.time()
        logger.info("Stress test completed")
    
    async def run_message_flood_test(self, connection_id: str = "flood_test", messages_per_second: int = 10, duration_seconds: int = 30):
        """Test message handling capacity"""
        logger.info(f"Starting message flood test: {messages_per_second} msg/s for {duration_seconds}s")
        
        try:
            async with websockets.connect(self.url) as websocket:
                logger.info(f"Flood test connected")
                
                # Send messages at specified rate
                start_time = time.time()
                message_interval = 1.0 / messages_per_second
                
                for i in range(messages_per_second * duration_seconds):
                    message = {
                        "type": "ping",
                        "test_id": i,
                        "timestamp": time.time(),
                        "data": f"Test message {i}"
                    }
                    
                    send_time = time.time()
                    await websocket.send(json.dumps(message))
                    self.stats['messages_sent'] += 1
                    
                    # Wait for next message time
                    elapsed = time.time() - send_time
                    if elapsed < message_interval:
                        await asyncio.sleep(message_interval - elapsed)
                
                logger.info("Message flood test completed")
                
        except Exception as e:
            logger.error(f"Flood test failed: {e}")
            self.stats['errors'] += 1
    
    async def run_connection_churn_test(self, cycles: int = 10, connections_per_cycle: int = 3):
        """Test rapid connection/disconnection cycles"""
        logger.info(f"Starting connection churn test: {cycles} cycles, {connections_per_cycle} connections per cycle")
        
        for cycle in range(cycles):
            logger.info(f"Churn cycle {cycle + 1}/{cycles}")
            
            # Create connections
            tasks = []
            for i in range(connections_per_cycle):
                task = asyncio.create_task(self.create_connection(f"churn_{cycle}_{i}"))
                tasks.append(task)
                await asyncio.sleep(0.05)  # Small delay between connections
            
            # Let them run for a short time
            await asyncio.sleep(5)
            
            # Cancel connections
            for task in tasks:
                task.cancel()
            
            # Wait for cleanup
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                pass
            
            # Wait between cycles
            await asyncio.sleep(2)
        
        logger.info("Connection churn test completed")
    
    def generate_report(self) -> str:
        """Generate a detailed test report"""
        if not self.stats['test_start_time']:
            return "No test data available"
        
        end_time = self.stats['test_end_time'] or time.time()
        total_duration = end_time - self.stats['test_start_time']
        
        report = f"""
=== WebSocket Stability Test Report ===
Test Duration: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)

Connection Statistics:
- Connections Made: {self.stats['connections_made']}
- Connections Lost: {self.stats['connections_lost']}
- Active Connections: {len(self.connections)}
- Reconnections: {self.stats['reconnections']}

Message Statistics:
- Messages Sent: {self.stats['messages_sent']}
- Messages Received: {self.stats['messages_received']}
- Message Rate: {self.stats['messages_received']/total_duration:.2f} msg/s
- Errors: {self.stats['errors']}

Connection Times:
"""
        
        if self.stats['connection_times']:
            avg_time = statistics.mean(self.stats['connection_times'])
            min_time = min(self.stats['connection_times'])
            max_time = max(self.stats['connection_times'])
            report += f"- Average Connection Duration: {avg_time:.2f}s\n"
            report += f"- Min Connection Duration: {min_time:.2f}s\n"
            report += f"- Max Connection Duration: {max_time:.2f}s\n"
        
        if self.stats['message_latencies']:
            avg_latency = statistics.mean(self.stats['message_latencies'])
            min_latency = min(self.stats['message_latencies'])
            max_latency = max(self.stats['message_latencies'])
            report += f"\nMessage Latencies:\n"
            report += f"- Average Latency: {avg_latency*1000:.2f}ms\n"
            report += f"- Min Latency: {min_latency*1000:.2f}ms\n"
            report += f"- Max Latency: {max_latency*1000:.2f}ms\n"
        
        if self.stats['disconnection_codes']:
            report += f"\nDisconnection Codes:\n"
            for code, count in self.stats['disconnection_codes'].items():
                report += f"- Code {code}: {count} times\n"
        
        # Stability assessment
        stability_score = 100
        if self.stats['connections_made'] > 0:
            loss_rate = self.stats['connections_lost'] / self.stats['connections_made']
            stability_score -= loss_rate * 50
        
        if self.stats['messages_sent'] > 0:
            error_rate = self.stats['errors'] / self.stats['messages_sent']
            stability_score -= error_rate * 30
        
        stability_score = max(0, stability_score)
        
        report += f"\nStability Score: {stability_score:.1f}/100\n"
        
        if stability_score >= 90:
            report += "Assessment: EXCELLENT - Very stable connection\n"
        elif stability_score >= 75:
            report += "Assessment: GOOD - Generally stable with minor issues\n"
        elif stability_score >= 60:
            report += "Assessment: FAIR - Some stability issues\n"
        else:
            report += "Assessment: POOR - Significant stability issues\n"
        
        return report

async def main():
    """Main test runner"""
    tester = WebSocketStabilityTester()
    
    print("WebSocket Stability Test Suite")
    print("=============================")
    print()
    
    try:
        # Test 1: Basic stability test
        print("1. Running basic stability test (2 connections, 2 minutes)...")
        await tester.run_stress_test(num_connections=2, duration_minutes=2)
        
        # Test 2: Message flood test
        print("\n2. Running message flood test...")
        await tester.run_message_flood_test(messages_per_second=5, duration_seconds=20)
        
        # Test 3: Connection churn test
        print("\n3. Running connection churn test...")
        await tester.run_connection_churn_test(cycles=5, connections_per_cycle=2)
        
        # Generate report
        print("\n" + tester.generate_report())
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        print(tester.generate_report())
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        print(tester.generate_report())

if __name__ == "__main__":
    asyncio.run(main())