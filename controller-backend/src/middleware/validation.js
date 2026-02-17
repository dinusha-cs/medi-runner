/**
 * Validation Middleware
 * Request validation using Joi schemas
 */

const Joi = require('joi');
const logger = require('../utils/logger');

/**
 * Create validation middleware for request body
 */
const validateRequest = (schema) => {
    return (req, res, next) => {
        const { error, value } = schema.validate(req.body, {
            abortEarly: false,
            stripUnknown: true
        });
        
        if (error) {
            const validationErrors = error.details.map(detail => ({
                field: detail.path.join('.'),
                message: detail.message,
                type: detail.type
            }));
            
            logger.warn('Validation failed:', validationErrors);
            
            return res.status(400).json({
                error: 'Validation failed',
                code: 'VALIDATION_ERROR',
                details: validationErrors
            });
        }
        
        // Replace request body with validated and sanitized data
        req.body = value;
        next();
    };
};

/**
 * Create validation middleware for query parameters
 */
const validateQuery = (schema) => {
    return (req, res, next) => {
        const { error, value } = schema.validate(req.query, {
            abortEarly: false,
            stripUnknown: true
        });
        
        if (error) {
            const validationErrors = error.details.map(detail => ({
                field: detail.path.join('.'),
                message: detail.message,
                type: detail.type
            }));
            
            return res.status(400).json({
                error: 'Query validation failed',
                code: 'QUERY_VALIDATION_ERROR',
                details: validationErrors
            });
        }
        
        req.query = value;
        next();
    };
};

/**
 * Create validation middleware for URL parameters
 */
const validateParams = (schema) => {
    return (req, res, next) => {
        const { error, value } = schema.validate(req.params, {
            abortEarly: false
        });
        
        if (error) {
            const validationErrors = error.details.map(detail => ({
                field: detail.path.join('.'),
                message: detail.message,
                type: detail.type
            }));
            
            return res.status(400).json({
                error: 'Parameter validation failed',
                code: 'PARAM_VALIDATION_ERROR',
                details: validationErrors
            });
        }
        
        req.params = value;
        next();
    };
};

/**
 * Common validation schemas
 */
const commonSchemas = {
    // UUID validation
    uuid: Joi.string().guid({ version: 'uuidv4' }).required(),
    
    // Pagination
    pagination: Joi.object({
        page: Joi.number().integer().min(1).default(1),
        limit: Joi.number().integer().min(1).max(100).default(10),
        sort: Joi.string().valid('asc', 'desc').default('desc'),
        sortBy: Joi.string().default('createdAt')
    }),
    
    // Coordinates
    coordinates: Joi.object({
        x: Joi.number().required(),
        y: Joi.number().required(),
        z: Joi.number().default(0)
    }),
    
    // Waypoint
    waypoint: Joi.object({
        x: Joi.number().required(),
        y: Joi.number().required(),
        action: Joi.string().optional(),
        tasks: Joi.array().items(Joi.object({
            type: Joi.string().required(),
            duration: Joi.number().min(0).optional(),
            parameters: Joi.object().optional()
        })).default([]),
        timeout: Joi.number().min(1).max(300).optional(),
        priority: Joi.string().valid('low', 'normal', 'high').default('normal')
    }),
    
    // Mission data
    mission: Joi.object({
        name: Joi.string().min(3).max(100).required(),
        description: Joi.string().max(500).optional(),
        type: Joi.string().valid('delivery', 'patrol', 'inspection', 'custom').required(),
        waypoints: Joi.array().items(Joi.object({
            x: Joi.number().required(),
            y: Joi.number().required(),
            action: Joi.string().optional(),
            tasks: Joi.array().optional()
        })).min(1).max(50).required(),
        priority: Joi.string().valid('low', 'normal', 'high', 'emergency').default('normal'),
        parameters: Joi.object().optional()
    })
};

/**
 * Validate file upload
 */
const validateFile = (options = {}) => {
    const {
        maxSize = 10 * 1024 * 1024, // 10MB
        allowedTypes = ['image/jpeg', 'image/png', 'application/json'],
        required = false
    } = options;
    
    return (req, res, next) => {
        if (!req.file && required) {
            return res.status(400).json({
                error: 'File upload required',
                code: 'FILE_REQUIRED'
            });
        }
        
        if (req.file) {
            // Check file size
            if (req.file.size > maxSize) {
                return res.status(400).json({
                    error: 'File too large',
                    code: 'FILE_TOO_LARGE',
                    maxSize,
                    actualSize: req.file.size
                });
            }
            
            // Check file type
            if (!allowedTypes.includes(req.file.mimetype)) {
                return res.status(400).json({
                    error: 'Invalid file type',
                    code: 'INVALID_FILE_TYPE',
                    allowedTypes,
                    actualType: req.file.mimetype
                });
            }
        }
        
        next();
    };
};

/**
 * Sanitize input data
 */
const sanitize = {
    /**
     * Remove HTML tags and dangerous characters
     */
    html: (value) => {
        if (typeof value !== 'string') return value;
        return value.replace(/<[^>]*>/g, '').trim();
    },
    
    /**
     * Sanitize for SQL injection (basic)
     */
    sql: (value) => {
        if (typeof value !== 'string') return value;
        return value.replace(/[';"\\]/g, '');
    },
    
    /**
     * Normalize whitespace
     */
    whitespace: (value) => {
        if (typeof value !== 'string') return value;
        return value.replace(/\s+/g, ' ').trim();
    }
};

/**
 * Create sanitization middleware
 */
const createSanitizeMiddleware = (sanitizers = []) => {
    return (req, res, next) => {
        const sanitizeObject = (obj) => {
            for (const key in obj) {
                if (typeof obj[key] === 'string') {
                    sanitizers.forEach(sanitizer => {
                        if (typeof sanitize[sanitizer] === 'function') {
                            obj[key] = sanitize[sanitizer](obj[key]);
                        }
                    });
                } else if (typeof obj[key] === 'object' && obj[key] !== null) {
                    sanitizeObject(obj[key]);
                }
            }
        };
        
        // Sanitize request body
        if (req.body && typeof req.body === 'object') {
            sanitizeObject(req.body);
        }
        
        // Sanitize query parameters
        if (req.query && typeof req.query === 'object') {
            sanitizeObject(req.query);
        }
        
        next();
    };
};

module.exports = {
    validateRequest,
    validateQuery,
    validateParams,
    validateFile,
    commonSchemas,
    sanitize,
    createSanitizeMiddleware
};
