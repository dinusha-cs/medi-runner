/**
 * Streaming Service
 * Handles video streaming from robot camera and other real-time data
 */

const EventEmitter = require('events');
const logger = require('../utils/logger');

class StreamService extends EventEmitter {
    constructor() {
        super();
        
        // Active streams
        this.streams = new Map();
        
        // Stream configurations
        this.configs = {
            camera: {
                quality: 'medium',
                fps: 30,
                resolution: '640x480'
            },
            sensors: {
                updateRate: 10, // Hz
                includeRaw: false
            }
        };
        
        // Statistics
        this.stats = {
            totalStreams: 0,
            activeStreams: 0,
            bytesStreamed: 0,
            framesStreamed: 0
        };
    }
    
    /**
     * Initialize streaming service
     */
    initialize() {
        logger.info('Streaming service initialized');
    }
    
    /**
     * Start camera stream
     */
    startCameraStream(streamId, config = {}) {
        const streamConfig = {
            ...this.configs.camera,
            ...config,
            type: 'camera',
            id: streamId,
            startTime: Date.now(),
            clients: new Set()
        };
        
        this.streams.set(streamId, streamConfig);
        this.stats.totalStreams++;
        this.stats.activeStreams++;
        
        logger.info(`Camera stream started: ${streamId}`);
        this.emit('stream_started', { id: streamId, type: 'camera' });
        
        return streamConfig;
    }
    
    /**
     * Start sensor data stream
     */
    startSensorStream(streamId, config = {}) {
        const streamConfig = {
            ...this.configs.sensors,
            ...config,
            type: 'sensors',
            id: streamId,
            startTime: Date.now(),
            clients: new Set()
        };
        
        this.streams.set(streamId, streamConfig);
        this.stats.totalStreams++;
        this.stats.activeStreams++;
        
        logger.info(`Sensor stream started: ${streamId}`);
        this.emit('stream_started', { id: streamId, type: 'sensors' });
        
        return streamConfig;
    }
    
    /**
     * Stop stream
     */
    stopStream(streamId) {
        const stream = this.streams.get(streamId);
        
        if (!stream) {
            throw new Error(`Stream not found: ${streamId}`);
        }
        
        this.streams.delete(streamId);
        this.stats.activeStreams--;
        
        logger.info(`Stream stopped: ${streamId}`);
        this.emit('stream_stopped', { id: streamId, type: stream.type });
    }
    
    /**
     * Add client to stream
     */
    addClient(streamId, clientId) {
        const stream = this.streams.get(streamId);
        
        if (!stream) {
            throw new Error(`Stream not found: ${streamId}`);
        }
        
        stream.clients.add(clientId);
        logger.debug(`Client ${clientId} added to stream ${streamId}`);
    }
    
    /**
     * Remove client from stream
     */
    removeClient(streamId, clientId) {
        const stream = this.streams.get(streamId);
        
        if (stream) {
            stream.clients.delete(clientId);
            logger.debug(`Client ${clientId} removed from stream ${streamId}`);
            
            // Stop stream if no clients
            if (stream.clients.size === 0) {
                this.stopStream(streamId);
            }
        }
    }
    
    /**
     * Process camera frame
     */
    processCameraFrame(streamId, frameData) {
        const stream = this.streams.get(streamId);
        
        if (!stream || stream.type !== 'camera') {
            return;
        }
        
        // Update statistics
        this.stats.framesStreamed++;
        this.stats.bytesStreamed += frameData.length || 0;
        
        // Broadcast to clients
        this.emit('camera_frame', {
            streamId,
            data: frameData,
            timestamp: Date.now(),
            clients: Array.from(stream.clients)
        });
    }
    
    /**
     * Process sensor data
     */
    processSensorData(streamId, sensorData) {
        const stream = this.streams.get(streamId);
        
        if (!stream || stream.type !== 'sensors') {
            return;
        }
        
        // Broadcast to clients
        this.emit('sensor_data', {
            streamId,
            data: sensorData,
            timestamp: Date.now(),
            clients: Array.from(stream.clients)
        });
    }
    
    /**
     * Get stream info
     */
    getStreamInfo(streamId) {
        const stream = this.streams.get(streamId);
        
        if (!stream) {
            return null;
        }
        
        return {
            id: stream.id,
            type: stream.type,
            config: {
                quality: stream.quality,
                fps: stream.fps,
                resolution: stream.resolution,
                updateRate: stream.updateRate
            },
            startTime: stream.startTime,
            uptime: Date.now() - stream.startTime,
            clientCount: stream.clients.size
        };
    }
    
    /**
     * Get all active streams
     */
    getActiveStreams() {
        return Array.from(this.streams.keys()).map(id => this.getStreamInfo(id));
    }
    
    /**
     * Get streaming statistics
     */
    getStatistics() {
        return {
            ...this.stats,
            activeStreamTypes: {
                camera: Array.from(this.streams.values()).filter(s => s.type === 'camera').length,
                sensors: Array.from(this.streams.values()).filter(s => s.type === 'sensors').length
            }
        };
    }
    
    /**
     * Update stream configuration
     */
    updateStreamConfig(streamId, config) {
        const stream = this.streams.get(streamId);
        
        if (!stream) {
            throw new Error(`Stream not found: ${streamId}`);
        }
        
        Object.assign(stream, config);
        
        logger.info(`Stream config updated: ${streamId}`);
        this.emit('stream_config_updated', { id: streamId, config });
    }
}

// Export singleton instance
const streamService = new StreamService();
module.exports = streamService;
