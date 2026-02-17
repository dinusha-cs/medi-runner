import { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { toast } from 'react-hot-toast';
import { useAppStore } from '@/store';
import { WebSocketMessage, Command } from '@/types';

export const useWebSocket = (url: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<Socket | null>(null);
  
  const {
    setConnectionStatus,
    updateHeartbeat,
    handleWebSocketMessage,
    addLog,
  } = useAppStore();

  useEffect(() => {
    // Initialize socket connection
    const socket = io(url, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      timeout: 10000,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      setIsConnected(true);
      setConnectionStatus('connected');
      updateHeartbeat();
      toast.success('Connected to robot controller');
      
      addLog({
        id: `log_${Date.now()}`,
        timestamp: new Date().toISOString(),
        level: 'info',
        source: 'system',
        message: 'WebSocket connection established',
      });
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
      setConnectionStatus('disconnected');
      toast.error('Disconnected from robot controller');
      
      addLog({
        id: `log_${Date.now()}`,
        timestamp: new Date().toISOString(),
        level: 'warn',
        source: 'system',
        message: 'WebSocket connection lost',
      });
    });

    socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      setConnectionStatus('disconnected');
      toast.error('Failed to connect to robot controller');
      
      addLog({
        id: `log_${Date.now()}`,
        timestamp: new Date().toISOString(),
        level: 'error',
        source: 'system',
        message: `Connection error: ${error.message}`,
      });
    });

    socket.on('reconnect', () => {
      toast.success('Reconnected to robot controller');
      addLog({
        id: `log_${Date.now()}`,
        timestamp: new Date().toISOString(),
        level: 'info',
        source: 'system',
        message: 'WebSocket reconnection successful',
      });
    });

    socket.on('reconnect_error', (error) => {
      console.error('WebSocket reconnection error:', error);
      toast.error('Failed to reconnect');
    });

    // Listen for all WebSocket messages
    socket.onAny((eventName: string, data: any) => {
      try {
        const message: WebSocketMessage = {
          type: eventName as any,
          data,
          timestamp: new Date().toISOString(),
        };
        
        handleWebSocketMessage(message);
        updateHeartbeat();
      } catch (error) {
        console.error('Error handling WebSocket message:', error);
        addLog({
          id: `log_${Date.now()}`,
          timestamp: new Date().toISOString(),
          level: 'error',
          source: 'system',
          message: `Error processing message: ${error}`,
        });
      }
    });

    // Cleanup on unmount
    return () => {
      socket.disconnect();
    };
  }, [url]);

  // Send command to server
  const sendCommand = (command: Omit<Command, 'id' | 'timestamp' | 'acknowledged' | 'completed'>) => {
    if (!socketRef.current || !isConnected) {
      toast.error('Not connected to robot controller');
      return false;
    }

    try {
      const fullCommand = useAppStore.getState().addCommand(command);
      socketRef.current.emit('command', fullCommand);
      
      addLog({
        id: `log_${Date.now()}`,
        timestamp: new Date().toISOString(),
        level: 'info',
        source: 'user',
        message: `Command sent: ${command.type}`,
        details: command.parameters,
      });
      
      return true;
    } catch (error) {
      console.error('Error sending command:', error);
      toast.error('Failed to send command');
      return false;
    }
  };

  // Send emergency stop
  const emergencyStop = () => {
    return sendCommand({
      type: 'emergency',
      parameters: { action: 'stop_all' },
    });
  };

  // Request system status
  const requestStatus = () => {
    if (socketRef.current && isConnected) {
      socketRef.current.emit('request_status');
    }
  };

  return {
    isConnected,
    sendCommand,
    emergencyStop,
    requestStatus,
    socket: socketRef.current,
  };
};