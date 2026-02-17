/**
 * Logger Utility
 * Winston-based logging with multiple transports and formatting
 */

const winston = require('winston');
const path = require('path');

// Define log levels and colors
const levels = {
    error: 0,
    warn: 1,
    info: 2,
    debug: 3
};

const colors = {
    error: 'red',
    warn: 'yellow', 
    info: 'green',
    debug: 'blue'
};

// Add colors to winston
winston.addColors(colors);

// Create logs directory if it doesn't exist
const fs = require('fs');
const logDir = path.join(process.cwd(), 'logs');
if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
}

// Define custom format
const customFormat = winston.format.combine(
    winston.format.timestamp({
        format: 'YYYY-MM-DD HH:mm:ss'
    }),
    winston.format.errors({ stack: true }),
    winston.format.json()
);

// Console format for development
const consoleFormat = winston.format.combine(
    winston.format.timestamp({
        format: 'HH:mm:ss'
    }),
    winston.format.colorize({ all: true }),
    winston.format.printf(({ timestamp, level, message, ...meta }) => {
        let metaStr = '';
        if (Object.keys(meta).length > 0) {
            metaStr = ' ' + JSON.stringify(meta, null, 2);
        }
        return `${timestamp} [${level}]: ${message}${metaStr}`;
    })
);

// Create transports array
const transports = [];

// Console transport for all environments
transports.push(
    new winston.transports.Console({
        level: process.env.LOG_LEVEL || (process.env.NODE_ENV === 'production' ? 'info' : 'debug'),
        format: process.env.NODE_ENV === 'production' ? customFormat : consoleFormat,
        handleExceptions: true,
        handleRejections: true
    })
);

// File transports for production
if (process.env.NODE_ENV === 'production') {
    // Error log file
    transports.push(
        new winston.transports.File({
            filename: path.join(logDir, 'error.log'),
            level: 'error',
            format: customFormat,
            handleExceptions: true,
            handleRejections: true,
            maxsize: 5242880, // 5MB
            maxFiles: 5
        })
    );
    
    // Combined log file  
    transports.push(
        new winston.transports.File({
            filename: path.join(logDir, 'combined.log'),
            format: customFormat,
            maxsize: 5242880, // 5MB  
            maxFiles: 5
        })
    );
}

// Create logger instance
const logger = winston.createLogger({
    levels,
    level: process.env.LOG_LEVEL || (process.env.NODE_ENV === 'production' ? 'info' : 'debug'),
    format: customFormat,
    transports,
    exitOnError: false
});

// Create child logger for specific modules
logger.child = (meta) => {
    return {
        error: (message, additionalMeta = {}) => logger.error(message, { ...meta, ...additionalMeta }),
        warn: (message, additionalMeta = {}) => logger.warn(message, { ...meta, ...additionalMeta }),
        info: (message, additionalMeta = {}) => logger.info(message, { ...meta, ...additionalMeta }),
        debug: (message, additionalMeta = {}) => logger.debug(message, { ...meta, ...additionalMeta })
    };
};

// Stream interface for morgan middleware
logger.stream = {
    write: (message) => {
        // Remove trailing newline
        logger.info(message.trim());
    }
};

// Helper methods for structured logging
logger.logRequest = (req, res, responseTime) => {
    const meta = {
        method: req.method,
        url: req.originalUrl,
        statusCode: res.statusCode,
        responseTime: `${responseTime}ms`,
        ip: req.ip,
        userAgent: req.get('User-Agent'),
        user: req.user?.username
    };
    
    const level = res.statusCode >= 400 ? 'warn' : 'info';
    logger[level]('HTTP Request', meta);
};

logger.logError = (error, req = null) => {
    const meta = {
        error: {
            name: error.name,
            message: error.message,
            stack: error.stack
        }
    };
    
    if (req) {
        meta.request = {
            method: req.method,
            url: req.originalUrl,
            ip: req.ip,
            user: req.user?.username
        };
    }
    
    logger.error('Application Error', meta);
};

logger.logRobotCommand = (command, user, result = null, error = null) => {
    const meta = {
        command,
        user: user?.username,
        timestamp: new Date().toISOString()
    };
    
    if (result) {
        meta.result = result;
        logger.info('Robot Command Executed', meta);
    } else if (error) {
        meta.error = error.message;
        logger.error('Robot Command Failed', meta);
    } else {
        logger.info('Robot Command Sent', meta);
    }
};

logger.logMission = (action, mission, user = null) => {
    const meta = {
        action,
        mission: {
            id: mission.id,
            name: mission.name,
            type: mission.type,
            status: mission.status
        },
        user: user?.username,
        timestamp: new Date().toISOString()
    };
    
    logger.info(`Mission ${action}`, meta);
};

logger.logWebSocket = (event, socketId, user = null, data = null) => {
    const meta = {
        event,
        socketId,
        user: user?.username,
        timestamp: new Date().toISOString()
    };
    
    if (data) {
        meta.data = data;
    }
    
    logger.info('WebSocket Event', meta);
};

// Performance logging
logger.logPerformance = (operation, duration, metadata = {}) => {
    logger.info(`Performance: ${operation}`, {
        operation,
        duration: `${duration}ms`,
        ...metadata,
        timestamp: new Date().toISOString()
    });
};

// Security logging
logger.logSecurity = (event, level = 'warn', metadata = {}) => {
    logger[level](`Security: ${event}`, {
        event,
        ...metadata,
        timestamp: new Date().toISOString()
    });
};

module.exports = logger;