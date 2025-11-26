"""
WebSocket Server for Robot Communication
Handles real-time communication between robot and control systems
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class WebSocketServer:
    """WebSocket server for robot communication"""
    
    def __init__(self, host="localhost", port=8765, robot_instance=None):
        self.host = host
        self.port = port
        self.robot = robot_instance
        self.clients = set()
        self.server = None
        
    async def register_client(self, websocket, path):
        """Register a new client connection"""
        self.clients.add(websocket)
        client_ip = websocket.remote_address[0]
        logger.info(f"🔌 Client connected from {client_ip}")
        
        try:
            # Send initial robot status
            if self.robot:
                status = await self.robot.get_status()
                await websocket.send(json.dumps({
                    "type": "status",
                    "timestamp": time.time(),
                    "data": status
                }))
            
            # Listen for messages
            async for message in websocket:
                await self.handle_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 Client {client_ip} disconnected")
        except Exception as e:
            logger.error(f"❌ Client error: {e}")
        finally:
            self.clients.discard(websocket)
    
    async def handle_message(self, websocket, message):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            message_id = data.get("id", "no_id")
            
            logger.info(f"📥 Received {message_type} message: {message_id}")
            
            # Send acknowledgment
            await websocket.send(json.dumps({
                "type": "ack",
                "id": message_id,
                "timestamp": time.time()
            }))
            
            if message_type == "command":
                await self.handle_command(websocket, data)
            elif message_type == "mission":
                await self.handle_mission(websocket, data)
            elif message_type == "emergency":
                await self.handle_emergency(websocket, data)
            elif message_type == "ping":
                await self.handle_ping(websocket, data)
            else:
                logger.warning(f"⚠️  Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("❌ Invalid JSON message received")
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Invalid JSON format"
            }))
        except Exception as e:
            logger.error(f"❌ Message handling error: {e}")
            await websocket.send(json.dumps({
                "type": "error", 
                "message": str(e)
            }))
    
    async def handle_command(self, websocket, data):
        """Handle robot command"""
        if not self.robot:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Robot not available"
            }))
            return
        
        try:
            command_data = data.get("data", {})
            result = await self.robot.execute_command(command_data)
            
            await websocket.send(json.dumps({
                "type": "command_result",
                "id": data.get("id"),
                "result": result,
                "timestamp": time.time()
            }))
            
            # Broadcast status update to all clients
            await self.broadcast_status_update()
            
        except Exception as e:
            logger.error(f"❌ Command execution error: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "id": data.get("id"),
                "message": str(e)
            }))
    
    async def handle_mission(self, websocket, data):
        """Handle mission assignment"""
        logger.info(f"🎯 Mission received: {data.get('data', {}).get('type', 'unknown')}")
        
        # For simulation, just acknowledge mission
        await websocket.send(json.dumps({
            "type": "mission_accepted",
            "id": data.get("id"),
            "message": "Mission accepted and queued",
            "timestamp": time.time()
        }))
        
        # Simulate mission progress
        asyncio.create_task(self.simulate_mission_progress(data))
    
    async def handle_emergency(self, websocket, data):
        """Handle emergency procedures"""
        logger.warning(f"🚨 Emergency procedure: {data.get('data', {}).get('action', 'unknown')}")
        
        if self.robot:
            # Execute emergency stop
            await self.robot.execute_command({"action": "emergency_stop"})
        
        # Broadcast emergency status to all clients
        await self.broadcast_emergency()
        
        await websocket.send(json.dumps({
            "type": "emergency_response",
            "id": data.get("id"),
            "message": "Emergency procedure executed",
            "timestamp": time.time()
        }))
    
    async def handle_ping(self, websocket, data):
        """Handle ping for connection testing"""
        await websocket.send(json.dumps({
            "type": "pong",
            "id": data.get("id"),
            "timestamp": time.time(),
            "server_time": datetime.now().isoformat()
        }))
    
    async def broadcast_status_update(self):
        """Broadcast robot status to all connected clients"""
        if not self.robot or not self.clients:
            return
        
        try:
            status = await self.robot.get_status()
            message = {
                "type": "status_update",
                "timestamp": time.time(),
                "data": status
            }
            
            # Send to all connected clients
            disconnected_clients = set()
            for client in self.clients:
                try:
                    await client.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(client)
            
            # Remove disconnected clients
            self.clients -= disconnected_clients
            
        except Exception as e:
            logger.error(f"❌ Status broadcast error: {e}")
    
    async def broadcast_emergency(self):
        """Broadcast emergency alert to all clients"""
        message = {
            "type": "emergency_alert",
            "timestamp": time.time(),
            "message": "Emergency stop activated - all operations halted"
        }
        
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
        
        self.clients -= disconnected_clients
    
    async def simulate_mission_progress(self, mission_data):
        """Simulate mission execution progress"""
        mission_id = mission_data.get("id", "unknown")
        mission_type = mission_data.get("data", {}).get("type", "delivery")
        
        # Simulate mission stages
        stages = [
            {"stage": "planning", "progress": 10, "message": "Route planning"},
            {"stage": "moving", "progress": 30, "message": "Moving to destination"}, 
            {"stage": "loading", "progress": 50, "message": "Loading cargo"},
            {"stage": "delivering", "progress": 80, "message": "Delivering cargo"},
            {"stage": "returning", "progress": 95, "message": "Returning to base"},
            {"stage": "complete", "progress": 100, "message": "Mission completed"}
        ]
        
        for stage in stages:
            await asyncio.sleep(2)  # Simulate stage duration
            
            progress_message = {
                "type": "mission_progress",
                "mission_id": mission_id,
                "timestamp": time.time(),
                "progress": stage
            }
            
            # Broadcast to all clients
            disconnected_clients = set()
            for client in self.clients:
                try:
                    await client.send(json.dumps(progress_message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(client)
            
            self.clients -= disconnected_clients
    
    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"🚀 Starting WebSocket server on {self.host}:{self.port}")
        
        try:
            self.server = await websockets.serve(
                self.register_client,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10
            )
            
            logger.info(f"✅ WebSocket server running on ws://{self.host}:{self.port}")
            
            # Start periodic status broadcasts
            asyncio.create_task(self.periodic_status_broadcast())
            
        except Exception as e:
            logger.error(f"❌ Failed to start WebSocket server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        if self.server:
            logger.info("🛑 Stopping WebSocket server...")
            self.server.close()
            await self.server.wait_closed()
            logger.info("✅ WebSocket server stopped")
    
    async def periodic_status_broadcast(self):
        """Periodically broadcast robot status"""
        while True:
            try:
                await asyncio.sleep(5)  # Broadcast every 5 seconds
                await self.broadcast_status_update()
            except Exception as e:
                logger.error(f"❌ Periodic broadcast error: {e}")
                await asyncio.sleep(1)

# WebSocket server instance
websocket_server = None

async def start_websocket_server(robot_instance, host="localhost", port=8765):
    """Start WebSocket server with robot instance"""
    global websocket_server
    
    websocket_server = WebSocketServer(host, port, robot_instance)
    await websocket_server.start_server()
    return websocket_server

async def stop_websocket_server():
    """Stop WebSocket server"""
    global websocket_server
    
    if websocket_server:
        await websocket_server.stop_server()
        websocket_server = None