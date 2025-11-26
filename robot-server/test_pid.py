#!/usr/bin/env python3
"""
Test script for PID control functionality
Tests the PID controller integration with the robot server
"""

import asyncio
import websockets
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_pid_commands():
    """Test PID-related commands"""
    uri = "ws://localhost:8765"

    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to robot server")

            # Test 1: Get current PID values
            logger.info("Test 1: Getting current PID values")
            command = {
                "type": "command",
                "id": "test_pid_1",
                "data": {
                    "action": "get_pid_values"
                },
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(command))
            response = await websocket.recv()
            result = json.loads(response)
            logger.info(f"PID values: {result}")

            # Test 2: Set PID values
            logger.info("Test 2: Setting PID values")
            command = {
                "type": "command",
                "id": "test_pid_2",
                "data": {
                    "action": "set_pid_values",
                    "kp": 1.5,
                    "ki": 0.1,
                    "kd": 0.2
                },
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(command))
            response = await websocket.recv()
            result = json.loads(response)
            logger.info(f"Set PID result: {result}")

            # Test 3: Reset PID
            logger.info("Test 3: Resetting PID controller")
            command = {
                "type": "command",
                "id": "test_pid_3",
                "data": {
                    "action": "reset_pid"
                },
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(command))
            response = await websocket.recv()
            result = json.loads(response)
            logger.info(f"Reset PID result: {result}")

            # Test 4: Start line following
            logger.info("Test 4: Starting line following")
            command = {
                "type": "command",
                "id": "test_pid_4",
                "data": {
                    "action": "start_line_following",
                    "base_speed": 40
                },
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(command))
            response = await websocket.recv()
            result = json.loads(response)
            logger.info(f"Start line following result: {result}")

            # Let it run for a few seconds
            await asyncio.sleep(3)

            # Test 5: Stop line following
            logger.info("Test 5: Stopping line following")
            command = {
                "type": "command",
                "id": "test_pid_5",
                "data": {
                    "action": "stop_line_following"
                },
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(command))
            response = await websocket.recv()
            result = json.loads(response)
            logger.info(f"Stop line following result: {result}")

            logger.info("All PID tests completed successfully!")

    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_pid_commands())