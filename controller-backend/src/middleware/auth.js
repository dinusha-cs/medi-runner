/**
 * Authentication Middleware
 * JWT-based authentication for API endpoints
 */

const jwt = require('jsonwebtoken');
const logger = require('../utils/logger');

const JWT_SECRET = process.env.JWT_SECRET || 'medi-runner-secret-key';

/**
 * Verify JWT token
 */
function verifyToken(token) {
    try {
        return jwt.verify(token, JWT_SECRET);
    } catch (error) {
        throw new Error('Invalid token');
    }
}

/**
 * Extract token from request
 */
function extractToken(req) {
    // Check Authorization header
    const authHeader = req.headers.authorization;
    if (authHeader && authHeader.startsWith('Bearer ')) {
        return authHeader.substring(7);
    }
    
    // Check query parameter (for WebSocket connections)
    if (req.query && req.query.token) {
        return req.query.token;
    }
    
    // Check cookies
    if (req.cookies && req.cookies.token) {
        return req.cookies.token;
    }
    
    return null;
}

/**
 * Required authentication middleware
 */
const required = (req, res, next) => {
    try {
        const token = extractToken(req);
        
        if (!token) {
            return res.status(401).json({
                error: 'Authentication required',
                code: 'TOKEN_MISSING'
            });
        }
        
        const decoded = verifyToken(token);
        req.user = decoded;
        
        logger.debug(`Authenticated user: ${decoded.username}`);
        next();
        
    } catch (error) {
        logger.warn('Authentication failed:', error.message);
        
        return res.status(401).json({
            error: 'Authentication failed',
            code: 'TOKEN_INVALID',
            details: error.message
        });
    }
};

/**
 * Optional authentication middleware
 */
const optional = (req, res, next) => {
    try {
        const token = extractToken(req);
        
        if (token) {
            const decoded = verifyToken(token);
            req.user = decoded;
            logger.debug(`Authenticated user: ${decoded.username}`);
        }
        
        next();
        
    } catch (error) {
        // Continue without authentication if token is invalid
        logger.debug('Optional authentication failed:', error.message);
        next();
    }
};

/**
 * Role-based access control
 */
const requireRole = (roles) => {
    return (req, res, next) => {
        if (!req.user) {
            return res.status(401).json({
                error: 'Authentication required',
                code: 'TOKEN_MISSING'
            });
        }
        
        const userRole = req.user.role;
        
        if (!roles.includes(userRole)) {
            return res.status(403).json({
                error: 'Insufficient permissions',
                code: 'INSUFFICIENT_ROLE',
                required: roles,
                current: userRole
            });
        }
        
        next();
    };
};

/**
 * Team-based access control
 */
const requireTeam = (req, res, next) => {
    if (!req.user) {
        return res.status(401).json({
            error: 'Authentication required',
            code: 'TOKEN_MISSING'
        });
    }
    
    if (!req.user.teamName) {
        return res.status(403).json({
            error: 'Team membership required',
            code: 'NO_TEAM'
        });
    }
    
    next();
};

/**
 * WebSocket authentication helper
 */
const authenticateSocket = (socket, next) => {
    try {
        const token = socket.handshake.auth.token || socket.handshake.query.token;
        
        if (!token) {
            return next(new Error('Authentication required'));
        }
        
        const decoded = verifyToken(token);
        socket.user = decoded;
        
        logger.debug(`Socket authenticated: ${decoded.username}`);
        next();
        
    } catch (error) {
        logger.warn('Socket authentication failed:', error.message);
        next(new Error('Authentication failed'));
    }
};

/**
 * Generate JWT token
 */
const generateToken = (payload, options = {}) => {
    const defaultOptions = {
        expiresIn: '24h'
    };
    
    return jwt.sign(payload, JWT_SECRET, { ...defaultOptions, ...options });
};

/**
 * Refresh token middleware
 */
const refreshToken = (req, res, next) => {
    if (req.user) {
        // Check if token is close to expiration (less than 2 hours left)
        const now = Math.floor(Date.now() / 1000);
        const timeLeft = req.user.exp - now;
        
        if (timeLeft < 7200) { // 2 hours in seconds
            const newToken = generateToken({
                username: req.user.username,
                teamName: req.user.teamName,
                role: req.user.role,
                userId: req.user.userId
            });
            
            res.setHeader('X-New-Token', newToken);
            logger.debug(`Token refreshed for user: ${req.user.username}`);
        }
    }
    
    next();
};

module.exports = {
    required,
    optional,
    requireRole,
    requireTeam,
    authenticateSocket,
    generateToken,
    refreshToken,
    verifyToken,
    extractToken
};
