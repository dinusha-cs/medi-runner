/**
 * Medi Runner Backend Server
 * Express.js application with WebSocket support for robot communication
 */

const express = require('express');
const http = require('http');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const { Server } = require('socket.io');
require('dotenv').config();

const logger = require('./utils/logger');

// Import services
const robotCommService = require('./services/robotCommService');
const missionService = require('./services/missionService');
const streamService = require('./services/streamService');

// Import routes
const authRoutes = require('./routes/auth');
const robotRoutes = require('./routes/robot');

// Import middleware
const authMiddleware = require('./middleware/auth');
const rateLimiters = require('./middleware/rateLimiter').rateLimiters;
const { globalErrorHandler, notFoundHandler } = require('./middleware/errorHandler');
const { createSanitizeMiddleware } = require('./middleware/validation');

class MediRunnerBackend {
    constructor() {
        this.app = express();
        this.server = http.createServer(this.app);
        this.io = new Server(this.server, {
            cors: {
                origin: process.env.FRONTEND_URL || 'http://localhost:3000',
                methods: ['GET', 'POST']
            }
        });
        
        this.port = process.env.PORT || 3001;
        this.robotWs = null;
        
        this.setupMiddleware();
        this.setupRoutes();
        this.setupWebSocket();
        this.setupServices();
        this.setupErrorHandling();
    }
    
    setupMiddleware() {
        // Trust proxy for correct IP addresses
        this.app.set('trust proxy', 1);
        
        // Security middleware
        this.app.use(helmet({
            contentSecurityPolicy: false, // Disable for development
            crossOriginEmbedderPolicy: false
        }));
        
        // Rate limiting for general API
        this.app.use('/api/', rateLimiters.moderate);
        
        // Strict rate limiting for auth endpoints
        this.app.use('/api/auth/', rateLimiters.strict);
        
        // CORS configuration
        this.app.use(cors({
            origin: process.env.FRONTEND_URL || 'http://localhost:3000',
            credentials: true,
            methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
            allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
        }));
        
        // Logging
        this.app.use(morgan('combined', {
            stream: { write: (message) => logger.info(message.trim()) }
        }));
        
        // Body parsing
        this.app.use(express.json({ 
            limit: '10mb',
            verify: (req, res, buf, encoding) => {
                // Store raw body for webhook verification if needed
                req.rawBody = buf;
            }
        }));
        this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));
        
        // Input sanitization
        this.app.use(createSanitizeMiddleware(['html', 'whitespace']));
        
        // Request logging middleware with duration
        this.app.use((req, res, next) => {
            const startTime = Date.now();
            
            res.on('finish', () => {
                const duration = Date.now() - startTime;
                const logLevel = res.statusCode >= 400 ? 'warn' : 'info';
                
                logger[logLevel]('Request completed', {
                    method: req.method,
                    url: req.originalUrl,
                    statusCode: res.statusCode,
                    duration: `${duration}ms`,
                    ip: req.ip,
                    userAgent: req.get('User-Agent'),
                    user: req.user?.username
                });
            });
            
            next();
        });
        
        // Static files (for uploads, etc.)
        this.app.use('/uploads', express.static('uploads'));
    }
    
    setupRoutes() {
        // Health check (no auth required)
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                version: process.env.npm_package_version || '1.0.0',
                environment: process.env.NODE_ENV || 'development',
                services: {
                    robotConnection: robotCommService.isConnected(),
                    missions: missionService.getStatistics(),
                    streaming: streamService.getStatistics()
                },
                uptime: process.uptime(),
                memory: process.memoryUsage()
            });
        });
        
        // API routes
        this.app.use('/api/auth', authRoutes);
        this.app.use('/api/robot', authMiddleware.optional, robotRoutes);
        
        // Streaming endpoint for video
        this.app.get('/api/stream/:streamId', authMiddleware.required, (req, res) => {
            const { streamId } = req.params;
            const streamInfo = streamService.getStreamInfo(streamId);
            
            if (!streamInfo) {
                return res.status(404).json({ error: 'Stream not found' });
            }
            
            res.json({
                stream: streamInfo,
                access: 'authorized'
            });
        });
        
        // Mission management endpoints
        this.app.get('/api/missions', authMiddleware.required, (req, res) => {
            try {
                const missions = missionService.getActiveMissions();
                const statistics = missionService.getStatistics();
                
                res.json({
                    success: true,
                    missions,
                    statistics
                });
            } catch (error) {
                res.status(500).json({
                    success: false,
                    error: error.message
                });
            }
        });
        
        // API status endpoint
        this.app.get('/api/status', authMiddleware.optional, (req, res) => {
            res.json({
                success: true,
                timestamp: new Date().toISOString(),
                robot: {
                    connected: robotCommService.isConnected(),
                    statistics: robotCommService.getStatistics()
                },
                missions: missionService.getStatistics(),
                streaming: streamService.getStatistics(),
                user: req.user ? {
                    username: req.user.username,
                    team: req.user.teamName,
                    role: req.user.role
                } : null
            });
        });
        
        // API documentation
        this.app.get('/api', (req, res) => {
            res.json({
                message: 'Medi Runner Challenge 2025 - Controller Backend API',
                version: process.env.npm_package_version || '1.0.0',
                environment: process.env.NODE_ENV || 'development',
                documentation: '/api/docs',
                endpoints: {
                    health: '/health',
                    status: '/api/status',
                    auth: '/api/auth/*',
                    robot: '/api/robot/*',
                    missions: '/api/missions',
                    streaming: '/api/stream/:streamId'
                },
                websocket: {
                    url: `ws://localhost:${this.port}`,
                    events: ['robot_command', 'mission_start', 'mission_stop', 'request_video_stream']
                }
            });
        });
        
        // Root endpoint
        this.app.get('/', (req, res) => {
            res.redirect('/api');
        });
    }
    
    setupWebSocket() {
        // WebSocket authentication middleware
        this.io.use(authMiddleware.authenticateSocket);
        
        // WebSocket rate limiting
        this.io.use(require('./middleware/rateLimiter').createSocketRateLimiter({
            windowMs: 1000,
            max: 20
        }));
        
        this.io.on('connection', (socket) => {
            logger.info('Client connected:', {
                socketId: socket.id,
                user: socket.user?.username,
                team: socket.user?.teamName,
                ip: socket.handshake.address
            });
            
            // Send initial status
            socket.emit('status', {
                robotConnected: robotCommService.isConnected(),
                activeStreams: streamService.getActiveStreams(),
                activeMissions: missionService.getActiveMissions(),
                timestamp: Date.now(),
                user: socket.user
            });
            
            // Handle robot control commands (with command rate limiting)
            socket.use(rateLimiters.command);
            
            socket.on('robot_command', async (data) => {
                try {
                    logger.info('Robot command received:', {
                        command: data,
                        user: socket.user?.username
                    });
                    
                    // Validate command structure
                    if (!data || !data.type) {
                        throw new Error('Invalid command format');
                    }
                    
                    // Forward command to robot
                    const result = await robotCommService.sendCommand(data);
                    
                    socket.emit('command_result', {
                        success: true,
                        command: data,
                        result,
                        timestamp: Date.now()
                    });
                    
                    // Broadcast to other clients
                    socket.broadcast.emit('robot_status_update', {
                        command: data.type,
                        status: 'executed',
                        user: socket.user?.username,
                        timestamp: Date.now()
                    });
                    
                } catch (error) {
                    logger.error('Robot command failed:', {
                        error: error.message,
                        command: data,
                        user: socket.user?.username
                    });
                    
                    socket.emit('command_result', {
                        success: false,
                        command: data,
                        error: error.message,
                        timestamp: Date.now()
                    });
                }
            });
            
            // Handle mission operations
            socket.on('mission_start', async (missionData) => {
                try {
                    const mission = await missionService.startMission({
                        ...missionData,
                        startedBy: socket.user?.username,
                        teamName: socket.user?.teamName
                    });
                    
                    socket.emit('mission_started', {
                        success: true,
                        mission,
                        timestamp: Date.now()
                    });
                    
                    // Broadcast mission start
                    this.io.emit('mission_update', {
                        type: 'started',
                        mission,
                        user: socket.user?.username,
                        timestamp: Date.now()
                    });
                    
                } catch (error) {
                    logger.error('Mission start failed:', {
                        error: error.message,
                        user: socket.user?.username
                    });
                    
                    socket.emit('mission_started', {
                        success: false,
                        error: error.message,
                        timestamp: Date.now()
                    });
                }
            });
            
            socket.on('mission_stop', async () => {
                try {
                    await missionService.stopCurrentMission();
                    this.io.emit('mission_update', {
                        type: 'stopped',
                        user: socket.user?.username,
                        timestamp: Date.now()
                    });
                } catch (error) {
                    socket.emit('error', { 
                        message: error.message,
                        timestamp: Date.now()
                    });
                }
            });
            
            // Handle video stream requests
            socket.on('request_video_stream', (data) => {
                try {
                    const streamId = data?.streamId || 'default_camera';
                    
                    // Add client to stream
                    streamService.addClient(streamId, socket.id);
                    
                    // Join socket room for streaming
                    socket.join(`stream_${streamId}`);
                    
                    logger.info('Client joined video stream:', {
                        socketId: socket.id,
                        streamId,
                        user: socket.user?.username
                    });
                    
                    socket.emit('stream_joined', {
                        streamId,
                        timestamp: Date.now()
                    });
                    
                } catch (error) {
                    socket.emit('error', {
                        message: error.message,
                        timestamp: Date.now()
                    });
                }
            });
            
            socket.on('stop_video_stream', (data) => {
                const streamId = data?.streamId || 'default_camera';
                
                streamService.removeClient(streamId, socket.id);
                socket.leave(`stream_${streamId}`);
                
                logger.info('Client left video stream:', {
                    socketId: socket.id,
                    streamId,
                    user: socket.user?.username
                });
            });
            
            // Handle disconnection
            socket.on('disconnect', (reason) => {
                logger.info('Client disconnected:', {
                    socketId: socket.id,
                    user: socket.user?.username,
                    reason
                });
                
                // Remove client from all streams
                streamService.getActiveStreams().forEach(stream => {
                    streamService.removeClient(stream.id, socket.id);
                });
            });
        });
    }
    
    setupServices() {
        // Initialize services
        robotCommService.initialize({
            robotUrl: process.env.ROBOT_WS_URL || 'ws://localhost:8765',
            reconnectInterval: 5000,
            maxReconnectAttempts: 10
        });
        missionService.initialize();
        streamService.initialize();
        
        // Handle robot data updates
        robotCommService.on('sensor_data', (data) => {
            this.io.emit('sensor_update', {
                ...data,
                timestamp: Date.now()
            });
        });
        
        robotCommService.on('camera_frame', (frame) => {
            // Process camera frame through streaming service
            streamService.processCameraFrame('default_camera', frame);
        });
        
        // Handle streaming service events
        streamService.on('camera_frame', (data) => {
            // Broadcast to specific stream room
            this.io.to(`stream_${data.streamId}`).emit('video_frame', {
                data: data.data,
                timestamp: data.timestamp
            });
        });
        
        robotCommService.on('status_update', (status) => {
            this.io.emit('robot_status_update', {
                ...status,
                timestamp: Date.now()
            });
        });
        
        // Handle mission updates
        missionService.on('mission_progress', (progress) => {
            this.io.emit('mission_progress', {
                ...progress,
                timestamp: Date.now()
            });
        });
        
        missionService.on('mission_complete', (result) => {
            this.io.emit('mission_complete', {
                ...result,
                timestamp: Date.now()
            });
        });
        
        // Handle connection events
        robotCommService.on('connected', () => {
            this.io.emit('robot_status_update', {
                type: 'connection',
                status: 'connected',
                timestamp: Date.now()
            });
        });
        
        robotCommService.on('disconnected', () => {
            this.io.emit('robot_status_update', {
                type: 'connection',
                status: 'disconnected',
                timestamp: Date.now()
            });
        });
        
        // Connect to robot if auto-connect is enabled
        if (process.env.AUTO_CONNECT_ROBOT === 'true') {
            const robotHost = process.env.ROBOT_HOST || 'localhost';
            const robotPort = process.env.ROBOT_PORT || 8765;
            
            setTimeout(() => {
                robotCommService.connect(`ws://${robotHost}:${robotPort}`)
                    .then(() => {
                        logger.info('Auto-connected to robot');
                    })
                    .catch((error) => {
                        logger.error('Auto-connect to robot failed:', error.message);
                    });
            }, 2000);
        }
    }
    
    setupErrorHandling() {
        // Handle 404 errors
        this.app.use(notFoundHandler);
        
        // Global error handler (must be last)
        this.app.use(globalErrorHandler);
        
        // Handle uncaught exceptions
        process.on('uncaughtException', (error) => {
            logger.error('Uncaught Exception:', error);
            this.gracefulShutdown('UNCAUGHT_EXCEPTION');
        });
        
        // Handle unhandled promise rejections
        process.on('unhandledRejection', (reason, promise) => {
            logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
            this.gracefulShutdown('UNHANDLED_REJECTION');
        });
        
        // Handle termination signals
        process.on('SIGTERM', () => {
            logger.info('SIGTERM received, shutting down gracefully');
            this.gracefulShutdown('SIGTERM');
        });
        
        process.on('SIGINT', () => {
            logger.info('SIGINT received, shutting down gracefully');
            this.gracefulShutdown('SIGINT');
        });
    }
    
    async gracefulShutdown(signal) {
        logger.info(`Graceful shutdown initiated by ${signal}`);
        
        this.server.close(() => {
            logger.info('HTTP server closed');
            
            // Close WebSocket connections
            this.io.close(() => {
                logger.info('WebSocket server closed');
                
                // Disconnect from robot
                robotCommService.disconnect().then(() => {
                    logger.info('Robot disconnected');
                    process.exit(0);
                }).catch((error) => {
                    logger.error('Error during robot disconnect:', error);
                    process.exit(1);
                });
            });
        });
        
        // Force close after timeout
        setTimeout(() => {
            logger.error('Could not close connections in time, forcefully shutting down');
            process.exit(1);
        }, 10000);
    }
    
    start() {
        this.server.listen(this.port, () => {
            logger.info(`Medi Runner Backend Server running on port ${this.port}`, {
                environment: process.env.NODE_ENV || 'development',
                version: process.env.npm_package_version || '1.0.0'
            });
            logger.info(`WebSocket available at ws://localhost:${this.port}/socket.io`);
            logger.info(`API available at http://localhost:${this.port}/api`);
        });
    }
    
    stop() {
        return new Promise((resolve) => {
            this.server.close(() => {
                logger.info('Server stopped');
                resolve();
            });
        });
    }
}

// Start server if this file is run directly
if (require.main === module) {
    const server = new MediRunnerBackend();
    server.start();
}

module.exports = MediRunnerBackend;

// Start server if this file is run directly
if (require.main === module) {
    const server = new MediRunnerBackend();
    server.start();
}

module.exports = MediRunnerBackend;
