/**
 * Robot Communication Service
 * Manages WebSocket connection and communication with the robot server
 */

const WebSocket = require('ws');
const EventEmitter = require('events');
const logger = require('../utils/logger');

class RobotCommunicationService extends EventEmitter {
    constructor() {
        super();
        
        this.ws = null;
        this.robotUrl = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectInterval = 5000;
        this.heartbeatInterval = null;
        this.connectionTimeout = 10000;
        
        // Robot state
        this.robotStatus = {
            connected: false,
            lastSeen: null,
            battery: null,
            mode: 'unknown',
            position: null,
            sensors: null,
            mission: null
        };
        
        // Message queue for when robot is disconnected
        this.messageQueue = [];
        this.maxQueueSize = 100;
        
        // Statistics
        this.stats = {
            messagesReceived: 0,
            messagesSent: 0,
            reconnects: 0,
            errors: 0,
            uptime: 0,
            startTime: null
        };
        
        // Recent logs for debugging
        this.recentLogs = [];
        this.maxLogs = 1000;
    }
    
    /**
     * Initialize the service with configuration
     */
    initialize(config) {
        this.robotUrl = config.robotUrl;
        this.reconnectInterval = config.reconnectInterval || 5000;
        this.maxReconnectAttempts = config.maxReconnectAttempts || 10;
        
        logger.info(`Robot communication service initialized for ${this.robotUrl}`);
    }
    
    /**
     * Connect to robot WebSocket server
     */
    async connect() {
        if (!this.robotUrl) {
            throw new Error('Robot URL not configured');
        }
        
        try {
            logger.info(`Connecting to robot at ${this.robotUrl}`);
            
            this.ws = new WebSocket(this.robotUrl, {
                handshakeTimeout: this.connectionTimeout,
                perMessageDeflate: false
            });
            
            this.setupWebSocketHandlers();
            
            // Wait for connection or timeout
            await this.waitForConnection();
            
        } catch (error) {
            logger.error('Failed to connect to robot:', error);
            this.handleConnectionError(error);
            throw error;
        }
    }
    
    /**
     * Setup WebSocket event handlers
     */
    setupWebSocketHandlers() {
        this.ws.on('open', () => {
            logger.info('Connected to robot successfully');
            
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.robotStatus.connected = true;
            this.robotStatus.lastSeen = new Date();
            this.stats.startTime = Date.now();
            
            // Process queued messages
            this.processMessageQueue();
            
            // Start heartbeat
            this.startHeartbeat();
            
            this.emit('connect');
            this.addLog('info', 'Connected to robot');
        });
        
        this.ws.on('message', (data) => {
            try {
                const message = JSON.parse(data.toString());
                this.handleRobotMessage(message);
                this.stats.messagesReceived++;
                
            } catch (error) {
                logger.error('Error parsing robot message:', error);
                this.addLog('error', `Message parsing error: ${error.message}`);
                this.stats.errors++;
            }
        });
        
        this.ws.on('close', (code, reason) => {
            logger.warn(`Robot connection closed: ${code} - ${reason}`);
            this.handleDisconnection();
        });
        
        this.ws.on('error', (error) => {
            logger.error('Robot WebSocket error:', error);
            this.handleConnectionError(error);
        });
        
        this.ws.on('ping', () => {
            this.robotStatus.lastSeen = new Date();
        });
        
        this.ws.on('pong', () => {
            this.robotStatus.lastSeen = new Date();
        });
    }
    
    /**
     * Wait for WebSocket connection to be established
     */
    waitForConnection() {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Connection timeout'));
            }, this.connectionTimeout);
            
            this.ws.once('open', () => {
                clearTimeout(timeout);
                resolve();
            });
            
            this.ws.once('error', (error) => {
                clearTimeout(timeout);
                reject(error);
            });
        });
    }
    
    /**
     * Handle incoming messages from robot
     */
    handleRobotMessage(message) {
        const { type, data, timestamp } = message;
        
        this.robotStatus.lastSeen = new Date(timestamp || Date.now());
        
        switch (type) {
            case 'status':
                this.updateRobotStatus(data);
                this.emit('status', data);
                break;
                
            case 'ack':
                this.emit('acknowledgment', message);
                this.addLog('debug', `Command acknowledged: ${message.message_id}`);
                break;
                
            case 'error':
                logger.error('Robot error:', data);
                this.emit('error', new Error(data.message || 'Robot error'));
                this.addLog('error', `Robot error: ${data.message}`);
                break;
                
            case 'welcome':
                logger.info('Received welcome from robot:', data);
                this.emit('welcome', data);
                this.addLog('info', 'Received welcome message');
                break;
                
            case 'mission_update':
                this.robotStatus.mission = data;
                this.emit('mission_update', data);
                this.addLog('info', `Mission update: ${data.state}`);
                break;
                
            case 'sensor_data':
                this.robotStatus.sensors = data;
                this.emit('sensor_data', data);
                break;
                
            case 'camera_frame':
                this.emit('camera_frame', data);
                break;
                
            default:
                logger.warn('Unknown message type from robot:', type);
                this.addLog('warn', `Unknown message type: ${type}`);
        }
        
        // Emit all messages for general listening
        this.emit('message', message);
    }
    
    /**
     * Update robot status from incoming data
     */
    updateRobotStatus(statusData) {
        if (statusData.motor) {
            this.robotStatus.mode = statusData.motor.direction || this.robotStatus.mode;
        }
        
        if (statusData.sensors) {
            this.robotStatus.sensors = statusData.sensors;
        }
        
        if (statusData.navigation) {
            this.robotStatus.position = statusData.navigation.position;
            this.robotStatus.mode = statusData.navigation.mode || this.robotStatus.mode;
        }
        
        if (statusData.mission) {
            this.robotStatus.mission = statusData.mission;
        }
        
        // Calculate uptime
        if (this.stats.startTime) {
            this.stats.uptime = Date.now() - this.stats.startTime;
        }
    }
    
    /**
     * Send command to robot
     */
    async sendCommand(command) {
        if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            if (this.messageQueue.length < this.maxQueueSize) {
                this.messageQueue.push(command);
                logger.warn('Robot not connected, queuing command');
                this.addLog('warn', 'Command queued - robot not connected');
                return { queued: true };
            } else {
                throw new Error('Robot not connected and message queue is full');
            }
        }
        
        try {
            const message = {
                ...command,
                id: this.generateMessageId(),
                timestamp: Date.now()
            };
            
            this.ws.send(JSON.stringify(message));
            this.stats.messagesSent++;
            
            logger.debug('Command sent to robot:', command);
            this.addLog('debug', `Command sent: ${command.action || command.type}`);
            
            return { sent: true, messageId: message.id };
            
        } catch (error) {
            logger.error('Error sending command to robot:', error);
            this.stats.errors++;
            this.addLog('error', `Send error: ${error.message}`);
            throw error;
        }
    }
    
    /**
     * Send mission to robot
     */
    async sendMission(mission) {
        return this.sendCommand({
            type: 'mission',
            action: 'start',
            data: mission
        });
    }
    
    /**
     * Emergency stop robot
     */
    async emergencyStop() {
        return this.sendCommand({
            type: 'command',
            action: 'stop',
            data: { emergency: true }
        });
    }
    
    /**
     * Update robot configuration
     */
    async updateConfig(component, settings) {
        return this.sendCommand({
            type: 'config',
            data: {
                component,
                settings
            }
        });
    }
    
    /**
     * Process queued messages when connection is restored
     */
    processMessageQueue() {
        if (this.messageQueue.length === 0) return;
        
        logger.info(`Processing ${this.messageQueue.length} queued messages`);
        
        const queue = [...this.messageQueue];
        this.messageQueue = [];
        
        queue.forEach(async (command) => {
            try {
                await this.sendCommand(command);
            } catch (error) {
                logger.error('Error processing queued command:', error);
            }
        });
    }
    
    /**
     * Handle connection disconnection
     */
    handleDisconnection() {
        this.isConnected = false;
        this.robotStatus.connected = false;
        this.stopHeartbeat();
        
        this.emit('disconnect');
        this.addLog('warn', 'Robot disconnected');
        
        // Attempt to reconnect
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
        } else {
            logger.error('Max reconnection attempts reached');
            this.addLog('error', 'Max reconnection attempts reached');
        }
    }
    
    /**
     * Handle connection errors
     */
    handleConnectionError(error) {
        this.stats.errors++;
        this.addLog('error', `Connection error: ${error.message}`);
        
        if (this.isConnected) {
            this.handleDisconnection();
        } else {
            this.scheduleReconnect();
        }
    }
    
    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        this.reconnectAttempts++;
        
        const delay = Math.min(
            this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
            30000 // Max 30 seconds
        );
        
        logger.info(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
        this.addLog('info', `Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        setTimeout(() => {
            this.connect().catch((error) => {
                logger.error('Reconnection failed:', error);
            });
        }, delay);
        
        this.stats.reconnects++;
    }
    
    /**
     * Start heartbeat to keep connection alive
     */
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.ping();
            }
        }, 30000); // 30 seconds
    }
    
    /**
     * Stop heartbeat
     */
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    /**
     * Test connection to robot
     */
    async testConnection() {
        const startTime = Date.now();
        
        try {
            await this.sendCommand({
                type: 'ping',
                timestamp: startTime
            });
            
            const latency = Date.now() - startTime;
            
            return {
                connected: this.isConnected,
                latency,
                lastSeen: this.robotStatus.lastSeen,
                robotInfo: {
                    mode: this.robotStatus.mode,
                    battery: this.robotStatus.battery,
                    sensors: this.robotStatus.sensors
                }
            };
        } catch (error) {
            return {
                connected: false,
                error: error.message,
                lastSeen: this.robotStatus.lastSeen
            };
        }
    }
    
    /**
     * Disconnect from robot
     */
    async disconnect() {
        logger.info('Disconnecting from robot...');
        
        this.stopHeartbeat();
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.close(1000, 'Service shutdown');
        }
        
        this.isConnected = false;
        this.robotStatus.connected = false;
        
        this.addLog('info', 'Disconnected from robot');
    }
    
    /**
     * Generate unique message ID
     */
    generateMessageId() {
        return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Add log entry
     */
    addLog(level, message) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            level,
            message
        };
        
        this.recentLogs.push(logEntry);
        
        if (this.recentLogs.length > this.maxLogs) {
            this.recentLogs.shift();
        }
    }
    
    /**
     * Get recent logs
     */
    getRecentLogs(limit = 100, level = null) {
        let logs = this.recentLogs;
        
        if (level) {
            logs = logs.filter(log => log.level === level);
        }
        
        return logs.slice(-limit);
    }
    
    /**
     * Get current robot status
     */
    getRobotStatus() {
        return {
            ...this.robotStatus,
            uptime: this.stats.uptime
        };
    }
    
    /**
     * Get connection status
     */
    getConnectionStatus() {
        return {
            connected: this.isConnected,
            url: this.robotUrl,
            reconnectAttempts: this.reconnectAttempts,
            lastSeen: this.robotStatus.lastSeen,
            queuedMessages: this.messageQueue.length
        };
    }
    
    /**
     * Get service statistics
     */
    getStatistics() {
        return {
            ...this.stats,
            queueSize: this.messageQueue.length,
            logEntries: this.recentLogs.length
        };
    }
    
    /**
     * Set up event handlers
     */
    onMessage(handler) {
        this.on('message', handler);
    }
    
    onError(handler) {
        this.on('error', handler);
    }
    
    onConnect(handler) {
        this.on('connect', handler);
    }
    
    onDisconnect(handler) {
        this.on('disconnect', handler);
    }
}

// Export singleton instance
const robotCommService = new RobotCommunicationService();
module.exports = robotCommService;
