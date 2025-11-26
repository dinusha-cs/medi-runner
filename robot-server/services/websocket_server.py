"""
WebSocket Server for Robot Communication
Handles real-time communication with the control backend.
"""

import asyncio
import json
import time
from typing import Callable, Set, Dict, Any, Optional

try:
    import websockets
except ImportError:
    # Mock websockets for testing
    class MockWebSocket:
        def __init__(self): pass
        async def send(self, data): pass
        async def recv(self): return '{}'
        def close(self): pass
    
    class MockWebSockets:
        @staticmethod
        async def serve(handler, host, port): pass
    
    websockets = MockWebSockets()

from config import WS_HOST, WS_PORT, WS_MAX_CONNECTIONS, COMMUNICATION
from utils.logger import setup_logger


class WebSocketServer:
    """
    WebSocket server for real-time robot communication.
    """
    
    def __init__(self, message_handler: Callable, host: str = WS_HOST, port: int = WS_PORT):
        self.logger = setup_logger('WebSocketServer')
        self.message_handler = message_handler
        
        self.host = host
        self.port = port
        self.server = None
        
        # Connected clients
        self.clients: Set = set()
        self.max_connections = WS_MAX_CONNECTIONS
        
        # Server statistics
        self.stats = {
            'connections_total': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'start_time': None
        }
    
    async def start(self):
        """
        Start the WebSocket server.
        """
        try:
            self.stats['start_time'] = time.time()
            
            self.logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
            
            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10,
                max_size=1024*1024  # 1MB message limit
            )
            
            self.logger.info(f"WebSocket server started successfully")
            
            # Wait for server to be closed
            await self.server.wait_closed()
            
        except Exception as e:
            self.logger.error(f"Error starting WebSocket server: {e}")
            raise
    
    async def stop(self):
        """
        Stop the WebSocket server.
        """
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.logger.info("WebSocket server stopped")
        
        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients],
                return_exceptions=True
            )
            self.clients.clear()
    
    async def _handle_client(self, websocket, path):
        """
        Handle new client connection.
        """
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        
        # Check connection limits
        if len(self.clients) >= self.max_connections:
            self.logger.warning(f"Connection limit reached, rejecting {client_id}")
            await websocket.close(code=1013, reason="Server busy")
            return
        
        # Add client to active connections
        self.clients.add(websocket)
        self.stats['connections_total'] += 1
        
        self.logger.info(f"Client connected: {client_id} (total: {len(self.clients)})")
        
        try:
            # Send welcome message
            welcome = {
                'type': 'welcome',
                'message': 'Connected to Medi Runner Robot',
                'server_time': time.time(),
                'capabilities': ['movement', 'sensors', 'camera', 'missions']
            }
            await self._send_to_client(websocket, welcome)
            
            # Handle client messages
            async for message in websocket:
                try:
                    await self._process_message(websocket, message)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON from {client_id}: {e}")
                    await self._send_error(websocket, "Invalid JSON format")
                except Exception as e:
                    self.logger.error(f"Error processing message from {client_id}: {e}")
                    await self._send_error(websocket, "Message processing error")
                    self.stats['errors'] += 1
        
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            self.logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Remove client from active connections
            if websocket in self.clients:
                self.clients.remove(websocket)
            
            self.logger.info(f"Client {client_id} cleaned up (remaining: {len(self.clients)})")
    
    async def _process_message(self, websocket, raw_message: str):
        """
        Process incoming message from client.
        """
        self.stats['messages_received'] += 1
        
        # Parse JSON message
        message = json.loads(raw_message)
        
        # Add metadata
        message['client_address'] = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        message['received_time'] = time.time()
        
        # Validate message structure
        if not isinstance(message, dict):
            raise ValueError("Message must be a JSON object")
        
        if 'type' not in message:
            raise ValueError("Message must have a 'type' field")
        
        # Log message (exclude sensitive data)
        log_message = {k: v for k, v in message.items() if k not in ['auth_token']}
        self.logger.debug(f"Received message: {log_message}")
        
        # Call message handler
        await self.message_handler(websocket, message)
    
    async def _send_to_client(self, websocket, message: Dict[str, Any]):
        """
        Send message to specific client.
        """
        try:
            if websocket.open:
                json_message = json.dumps(message)
                await websocket.send(json_message)
                self.stats['messages_sent'] += 1
        except Exception as e:
            self.logger.error(f"Error sending message to client: {e}")
            # Remove client if sending fails
            if websocket in self.clients:
                self.clients.remove(websocket)
    
    async def _send_error(self, websocket, error_message: str):
        """
        Send error message to client.
        """
        error_response = {
            'type': 'error',
            'message': error_message,
            'timestamp': time.time()
        }
        await self._send_to_client(websocket, error_response)
    
    async def broadcast(self, message: Dict[str, Any], exclude: Optional[Set] = None):
        """
        Broadcast message to all connected clients.
        
        Args:
            message: Message to broadcast
            exclude: Set of clients to exclude from broadcast
        """
        if not self.clients:
            return
        
        exclude = exclude or set()
        target_clients = self.clients - exclude
        
        if target_clients:
            # Add timestamp if not present
            if 'timestamp' not in message:
                message['timestamp'] = time.time()
            
            # Send to all clients in parallel
            tasks = []
            for client in list(target_clients):  # Create copy to avoid modification during iteration
                if client.open:
                    tasks.append(self._send_to_client(client, message))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def send_to_client_by_id(self, client_id: str, message: Dict[str, Any]):
        """
        Send message to specific client by ID.
        """
        for client in self.clients:
            if f"{client.remote_address[0]}:{client.remote_address[1]}" == client_id:
                await self._send_to_client(client, message)
                return True
        return False
    
    def get_client_count(self) -> int:
        """
        Get number of connected clients.
        """
        return len(self.clients)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get server statistics.
        """
        uptime = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        
        return {
            **self.stats,
            'clients_connected': len(self.clients),
            'uptime_seconds': uptime,
            'messages_per_second': self.stats['messages_received'] / max(uptime, 1)
        }
