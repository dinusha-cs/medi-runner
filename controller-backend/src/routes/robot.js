/**
 * Robot Control Routes
 * Handles robot commands, status, and configuration
 */

const express = require('express');
const Joi = require('joi');
const router = express.Router();

const logger = require('../utils/logger');
const robotCommService = require('../services/robotCommService');
const { validateRequest } = require('../middleware/validation');
const rateLimiter = require('../middleware/rateLimiter');

// Rate limiting for robot commands
const commandLimiter = rateLimiter({
    windowMs: 1000, // 1 second
    max: 10, // 10 commands per second
    message: 'Too many robot commands, please slow down'
});

// Validation schemas
const commandSchema = Joi.object({
    action: Joi.string().valid(
        'move', 'stop', 'set_mode', 'calibrate', 
        'emergency_stop', 'get_status', 'set_pid_values',
        'get_pid_values', 'reset_pid', 'start_line_following',
        'stop_line_following'
    ).required(),
    data: Joi.object({
        direction: Joi.string().valid('forward', 'backward', 'left', 'right'),
        speed: Joi.number().min(0).max(100),
        duration: Joi.number().min(0).max(10),
        mode: Joi.string().valid('manual', 'autonomous', 'line_following'),
        kp: Joi.number().min(0).max(10),
        ki: Joi.number().min(0).max(10),
        kd: Joi.number().min(0).max(10),
        base_speed: Joi.number().min(0).max(100)
    }).optional()
});

const configSchema = Joi.object({
    component: Joi.string().valid('motor', 'sensor', 'vision').required(),
    settings: Joi.object().required()
});

/**
 * GET /api/robot/status
 * Get current robot status
 */
router.get('/status', async (req, res) => {
    try {
        const status = robotCommService.getRobotStatus();
        const connectionStatus = robotCommService.getConnectionStatus();
        
        res.json({
            robot: status,
            connection: connectionStatus,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        logger.error('Error getting robot status:', error);
        res.status(500).json({
            error: 'Failed to get robot status',
            code: 'STATUS_ERROR'
        });
    }
});

/**
 * POST /api/robot/command
 * Send command to robot
 */
router.post('/command', commandLimiter, validateRequest(commandSchema), async (req, res) => {
    try {
        const { action, data } = req.body;
        const username = req.user?.username || 'anonymous';
        
        logger.info(`Robot command from ${username}: ${action}`, data);
        
        // Send command to robot
        const result = await robotCommService.sendCommand({
            type: 'command',
            action,
            data: data || {},
            timestamp: Date.now(),
            user: username
        });
        
        res.json({
            success: true,
            message: 'Command sent successfully',
            action,
            result
        });
        
    } catch (error) {
        logger.error('Error sending robot command:', error);
        
        if (error.message.includes('not connected')) {
            return res.status(503).json({
                error: 'Robot not connected',
                code: 'ROBOT_DISCONNECTED'
            });
        }
        
        res.status(500).json({
            error: 'Failed to send command',
            code: 'COMMAND_ERROR',
            details: error.message
        });
    }
});

/**
 * POST /api/robot/emergency-stop
 * Emergency stop robot (no rate limiting)
 */
router.post('/emergency-stop', async (req, res) => {
    try {
        const username = req.user?.username || 'anonymous';
        
        logger.warn(`EMERGENCY STOP activated by ${username}`);
        
        await robotCommService.emergencyStop();
        
        res.json({
            success: true,
            message: 'Emergency stop activated'
        });
        
    } catch (error) {
        logger.error('Error activating emergency stop:', error);
        res.status(500).json({
            error: 'Failed to activate emergency stop',
            code: 'EMERGENCY_STOP_ERROR'
        });
    }
});

/**
 * PUT /api/robot/config
 * Update robot configuration
 */
router.put('/config', validateRequest(configSchema), async (req, res) => {
    try {
        const { component, settings } = req.body;
        const username = req.user?.username || 'anonymous';
        
        logger.info(`Robot config update from ${username}:`, { component, settings });
        
        await robotCommService.updateConfig(component, settings);
        
        res.json({
            success: true,
            message: 'Configuration updated',
            component,
            settings
        });
        
    } catch (error) {
        logger.error('Error updating robot config:', error);
        res.status(500).json({
            error: 'Failed to update configuration',
            code: 'CONFIG_ERROR'
        });
    }
});

/**
 * GET /api/robot/capabilities
 * Get robot capabilities and available commands
 */
router.get('/capabilities', (req, res) => {
    res.json({
        capabilities: {
            movement: {
                directions: ['forward', 'backward', 'left', 'right'],
                speed_range: [0, 100],
                max_duration: 10
            },
            modes: ['manual', 'autonomous', 'line_following'],
            sensors: {
                ir_array: {
                    count: 5,
                    position: 'front'
                },
                camera: {
                    resolution: '640x480',
                    fps: 30
                }
            },
            vision: {
                sign_detection: true,
                object_detection: true,
                line_guidance: true
            }
        },
        commands: {
            movement: ['move', 'stop'],
            control: ['set_mode', 'calibrate', 'emergency_stop'],
            status: ['get_status']
        },
        configurable_components: ['motor', 'sensor', 'vision']
    });
});

/**
 * POST /api/robot/calibrate
 * Calibrate robot sensors
 */
router.post('/calibrate', async (req, res) => {
    try {
        const { component } = req.body;
        const username = req.user?.username || 'anonymous';
        
        logger.info(`Calibration started by ${username} for component: ${component || 'all'}`);
        
        await robotCommService.sendCommand({
            type: 'command',
            action: 'calibrate',
            data: { component: component || 'all' },
            timestamp: Date.now(),
            user: username
        });
        
        res.json({
            success: true,
            message: 'Calibration started',
            component: component || 'all'
        });
        
    } catch (error) {
        logger.error('Error starting calibration:', error);
        res.status(500).json({
            error: 'Failed to start calibration',
            code: 'CALIBRATION_ERROR'
        });
    }
});

/**
 * GET /api/robot/logs
 * Get recent robot logs
 */
router.get('/logs', async (req, res) => {
    try {
        const { limit = 100, level = 'info' } = req.query;
        
        // In a real implementation, this would fetch logs from the robot
        // For now, return mock data
        const logs = robotCommService.getRecentLogs(parseInt(limit), level);
        
        res.json({
            logs,
            total: logs.length,
            level,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        logger.error('Error fetching robot logs:', error);
        res.status(500).json({
            error: 'Failed to fetch logs',
            code: 'LOGS_ERROR'
        });
    }
});

/**
 * POST /api/robot/test-connection
 * Test connection to robot
 */
router.post('/test-connection', async (req, res) => {
    try {
        const connectionStatus = await robotCommService.testConnection();
        
        res.json({
            connected: connectionStatus.connected,
            latency: connectionStatus.latency,
            last_seen: connectionStatus.lastSeen,
            robot_info: connectionStatus.robotInfo
        });
        
    } catch (error) {
        logger.error('Error testing robot connection:', error);
        res.status(500).json({
            error: 'Connection test failed',
            code: 'CONNECTION_TEST_ERROR',
            connected: false
        });
    }
});

/**
 * GET /api/robot/statistics
 * Get robot usage statistics
 */
router.get('/statistics', async (req, res) => {
    try {
        const stats = robotCommService.getStatistics();
        
        res.json({
            statistics: stats,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        logger.error('Error getting robot statistics:', error);
        res.status(500).json({
            error: 'Failed to get statistics',
            code: 'STATISTICS_ERROR'
        });
    }
});

/**
 * GET /api/robot/pid
 * Get current PID controller values
 */
router.get('/pid', async (req, res) => {
    try {
        const result = await robotCommService.sendCommand({
            type: 'command',
            action: 'get_pid_values',
            data: {},
            timestamp: Date.now()
        });
        
        res.json({
            success: true,
            pid_values: result
        });
        
    } catch (error) {
        logger.error('Error getting PID values:', error);
        res.status(500).json({
            error: 'Failed to get PID values',
            code: 'PID_GET_ERROR'
        });
    }
});

/**
 * PUT /api/robot/pid
 * Update PID controller values
 */
router.put('/pid', async (req, res) => {
    try {
        const { kp, ki, kd } = req.body;
        const username = req.user?.username || 'anonymous';
        
        logger.info(`PID update from ${username}: Kp=${kp}, Ki=${ki}, Kd=${kd}`);
        
        const result = await robotCommService.sendCommand({
            type: 'command',
            action: 'set_pid_values',
            data: { kp, ki, kd },
            timestamp: Date.now(),
            user: username
        });
        
        res.json({
            success: true,
            message: 'PID values updated',
            pid_values: result
        });
        
    } catch (error) {
        logger.error('Error updating PID values:', error);
        res.status(500).json({
            error: 'Failed to update PID values',
            code: 'PID_UPDATE_ERROR'
        });
    }
});

/**
 * POST /api/robot/pid/reset
 * Reset PID controller state
 */
router.post('/pid/reset', async (req, res) => {
    try {
        const username = req.user?.username || 'anonymous';
        
        logger.info(`PID reset by ${username}`);
        
        const result = await robotCommService.sendCommand({
            type: 'command',
            action: 'reset_pid',
            data: {},
            timestamp: Date.now(),
            user: username
        });
        
        res.json({
            success: true,
            message: 'PID controller reset',
            result
        });
        
    } catch (error) {
        logger.error('Error resetting PID controller:', error);
        res.status(500).json({
            error: 'Failed to reset PID controller',
            code: 'PID_RESET_ERROR'
        });
    }
});

/**
 * POST /api/robot/line-following/start
 * Start line following with PID control
 */
router.post('/line-following/start', async (req, res) => {
    try {
        const { base_speed = 50 } = req.body;
        const username = req.user?.username || 'anonymous';
        
        logger.info(`Line following started by ${username} with base speed ${base_speed}`);
        
        const result = await robotCommService.sendCommand({
            type: 'command',
            action: 'start_line_following',
            data: { base_speed },
            timestamp: Date.now(),
            user: username
        });
        
        res.json({
            success: true,
            message: 'Line following started',
            base_speed,
            result
        });
        
    } catch (error) {
        logger.error('Error starting line following:', error);
        res.status(500).json({
            error: 'Failed to start line following',
            code: 'LINE_FOLLOWING_START_ERROR'
        });
    }
});

/**
 * POST /api/robot/line-following/stop
 * Stop line following
 */
router.post('/line-following/stop', async (req, res) => {
    try {
        const username = req.user?.username || 'anonymous';
        
        logger.info(`Line following stopped by ${username}`);
        
        const result = await robotCommService.sendCommand({
            type: 'command',
            action: 'stop_line_following',
            data: {},
            timestamp: Date.now(),
            user: username
        });
        
        res.json({
            success: true,
            message: 'Line following stopped',
            result
        });
        
    } catch (error) {
        logger.error('Error stopping line following:', error);
        res.status(500).json({
            error: 'Failed to stop line following',
            code: 'LINE_FOLLOWING_STOP_ERROR'
        });
    }
});

module.exports = router;
