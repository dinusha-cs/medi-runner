/**
 * Global Error Handler Middleware
 * Centralized error handling for the Express application
 */

const logger = require('../utils/logger');

/**
 * Custom error classes
 */
class AppError extends Error {
    constructor(message, statusCode, code = null) {
        super(message);
        this.statusCode = statusCode;
        this.code = code;
        this.isOperational = true;
        
        Error.captureStackTrace(this, this.constructor);
    }
}

class ValidationError extends AppError {
    constructor(message, details = []) {
        super(message, 400, 'VALIDATION_ERROR');
        this.details = details;
    }
}

class AuthenticationError extends AppError {
    constructor(message = 'Authentication required') {
        super(message, 401, 'AUTHENTICATION_ERROR');
    }
}

class AuthorizationError extends AppError {
    constructor(message = 'Insufficient permissions') {
        super(message, 403, 'AUTHORIZATION_ERROR');
    }
}

class NotFoundError extends AppError {
    constructor(resource = 'Resource') {
        super(`${resource} not found`, 404, 'NOT_FOUND');
    }
}

class ConflictError extends AppError {
    constructor(message = 'Resource conflict') {
        super(message, 409, 'CONFLICT');
    }
}

class RateLimitError extends AppError {
    constructor(message = 'Rate limit exceeded') {
        super(message, 429, 'RATE_LIMIT_EXCEEDED');
    }
}

class ServiceError extends AppError {
    constructor(message = 'Service temporarily unavailable', service = 'unknown') {
        super(message, 503, 'SERVICE_ERROR');
        this.service = service;
    }
}

/**
 * Development error response
 */
function sendErrorDev(err, res) {
    res.status(err.statusCode || 500).json({
        error: {
            message: err.message,
            code: err.code,
            statusCode: err.statusCode,
            stack: err.stack,
            details: err.details,
            service: err.service,
            timestamp: new Date().toISOString()
        }
    });
}

/**
 * Production error response
 */
function sendErrorProd(err, res) {
    // Only send error details for operational errors
    if (err.isOperational) {
        const response = {
            error: {
                message: err.message,
                code: err.code,
                timestamp: new Date().toISOString()
            }
        };
        
        // Add additional details for specific error types
        if (err.details) {
            response.error.details = err.details;
        }
        
        if (err.service) {
            response.error.service = err.service;
        }
        
        res.status(err.statusCode || 500).json(response);
    } else {
        // Generic error message for programming errors
        logger.error('Programming error:', err);
        
        res.status(500).json({
            error: {
                message: 'Internal server error',
                code: 'INTERNAL_ERROR',
                timestamp: new Date().toISOString()
            }
        });
    }
}

/**
 * Handle specific error types
 */
function handleCastErrorDB(err) {
    const message = `Invalid ${err.path}: ${err.value}`;
    return new AppError(message, 400, 'INVALID_DATA');
}

function handleDuplicateFieldsDB(err) {
    const value = err.errmsg.match(/(["'])(\\?.)*?\1/)[0];
    const message = `Duplicate field value: ${value}. Please use another value!`;
    return new AppError(message, 400, 'DUPLICATE_FIELD');
}

function handleValidationErrorDB(err) {
    const errors = Object.values(err.errors).map(el => el.message);
    const message = `Invalid input data. ${errors.join('. ')}`;
    return new ValidationError(message, errors);
}

function handleJWTError() {
    return new AuthenticationError('Invalid token. Please log in again!');
}

function handleJWTExpiredError() {
    return new AuthenticationError('Your token has expired! Please log in again.');
}

/**
 * Main error handling middleware
 */
const globalErrorHandler = (err, req, res, next) => {
    // Set default error properties
    err.statusCode = err.statusCode || 500;
    err.status = err.status || 'error';
    
    // Log error
    const logLevel = err.statusCode >= 500 ? 'error' : 'warn';
    logger[logLevel]('Request error:', {
        message: err.message,
        statusCode: err.statusCode,
        code: err.code,
        url: req.originalUrl,
        method: req.method,
        ip: req.ip,
        userAgent: req.get('User-Agent'),
        user: req.user?.username,
        stack: err.stack
    });
    
    // Handle specific error types
    let error = { ...err };
    error.message = err.message;
    
    // MongoDB/Database errors
    if (err.name === 'CastError') error = handleCastErrorDB(error);
    if (err.code === 11000) error = handleDuplicateFieldsDB(error);
    if (err.name === 'ValidationError') error = handleValidationErrorDB(error);
    
    // JWT errors
    if (err.name === 'JsonWebTokenError') error = handleJWTError();
    if (err.name === 'TokenExpiredError') error = handleJWTExpiredError();
    
    // WebSocket errors
    if (err.name === 'WebSocketError') {
        error = new ServiceError('WebSocket connection error', 'websocket');
    }
    
    // Robot communication errors
    if (err.message && err.message.includes('Robot not connected')) {
        error = new ServiceError('Robot not connected', 'robot');
    }
    
    // Send error response
    if (process.env.NODE_ENV === 'development') {
        sendErrorDev(error, res);
    } else {
        sendErrorProd(error, res);
    }
};

/**
 * 404 handler middleware
 */
const notFoundHandler = (req, res, next) => {
    const err = new NotFoundError(`Can't find ${req.originalUrl} on this server!`);
    next(err);
};

/**
 * Async error wrapper
 */
const catchAsync = (fn) => {
    return (req, res, next) => {
        Promise.resolve(fn(req, res, next)).catch(next);
    };
};

/**
 * Operational error checker
 */
const isOperationalError = (error) => {
    if (error instanceof AppError) {
        return error.isOperational;
    }
    return false;
};

module.exports = {
    // Error classes
    AppError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    ServiceError,
    
    // Middleware
    globalErrorHandler,
    notFoundHandler,
    
    // Utilities
    catchAsync,
    isOperationalError
};

// Export default error handler
module.exports.default = globalErrorHandler;
