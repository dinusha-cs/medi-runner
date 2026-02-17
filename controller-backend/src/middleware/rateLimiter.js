/**
 * Rate Limiting Middleware
 * Prevents abuse by limiting request frequency
 */

const logger = require('../utils/logger');

/**
 * In-memory rate limiter (use Redis in production for distributed systems)
 */
class MemoryStore {
    constructor() {
        this.clients = new Map();
        
        // Clean up expired entries every minute
        setInterval(() => {
            this.cleanup();
        }, 60000);
    }
    
    get(key) {
        return this.clients.get(key);
    }
    
    set(key, value, ttl) {
        this.clients.set(key, {
            ...value,
            expires: Date.now() + ttl
        });
    }
    
    cleanup() {
        const now = Date.now();
        for (const [key, value] of this.clients.entries()) {
            if (value.expires < now) {
                this.clients.delete(key);
            }
        }
    }
    
    reset(key) {
        this.clients.delete(key);
    }
    
    size() {
        return this.clients.size;
    }
}

const defaultStore = new MemoryStore();

/**
 * Create rate limiter middleware
 */
const createRateLimiter = (options = {}) => {
    const {
        windowMs = 15 * 60 * 1000, // 15 minutes
        max = 100, // requests per window
        message = 'Too many requests, please try again later',
        statusCode = 429,
        headers = true,
        skipSuccessfulRequests = false,
        skipFailedRequests = false,
        keyGenerator = (req) => req.ip,
        skip = () => false,
        store = defaultStore,
        onLimitReached = null
    } = options;
    
    return (req, res, next) => {
        // Skip if condition is met
        if (skip(req, res)) {
            return next();
        }
        
        const key = keyGenerator(req);
        const now = Date.now();
        
        // Get current state for this key
        let state = store.get(key);
        
        if (!state || now > state.expires) {
            // Initialize or reset state
            state = {
                count: 0,
                resetTime: now + windowMs,
                expires: now + windowMs
            };
        }
        
        // Increment counter
        state.count++;
        
        // Store updated state
        store.set(key, state, windowMs);
        
        // Add headers if enabled
        if (headers) {
            res.setHeader('X-RateLimit-Limit', max);
            res.setHeader('X-RateLimit-Remaining', Math.max(0, max - state.count));
            res.setHeader('X-RateLimit-Reset', new Date(state.resetTime).toISOString());
        }
        
        // Check if limit exceeded
        if (state.count > max) {
            logger.warn(`Rate limit exceeded for ${key}: ${state.count}/${max}`);
            
            if (onLimitReached) {
                onLimitReached(req, res, options);
            }
            
            return res.status(statusCode).json({
                error: message,
                code: 'RATE_LIMIT_EXCEEDED',
                retryAfter: Math.ceil((state.resetTime - now) / 1000)
            });
        }
        
        // Handle response to update counters
        const originalSend = res.send;
        res.send = function(data) {
            const shouldSkip = (
                (skipSuccessfulRequests && res.statusCode < 400) ||
                (skipFailedRequests && res.statusCode >= 400)
            );
            
            if (shouldSkip) {
                // Decrement counter if we're skipping this request
                const currentState = store.get(key);
                if (currentState) {
                    currentState.count--;
                    store.set(key, currentState, windowMs);
                }
            }
            
            return originalSend.call(this, data);
        };
        
        next();
    };
};

/**
 * Predefined rate limiters
 */
const rateLimiters = {
    // Strict limiter for authentication endpoints
    strict: createRateLimiter({
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: 5, // 5 requests per window
        message: 'Too many authentication attempts, please try again later'
    }),
    
    // Moderate limiter for API endpoints
    moderate: createRateLimiter({
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: 100, // 100 requests per window
        message: 'Too many requests, please try again later'
    }),
    
    // Lenient limiter for general use
    lenient: createRateLimiter({
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: 1000, // 1000 requests per window
        message: 'Too many requests, please try again later'
    }),
    
    // Very strict limiter for sensitive operations
    sensitive: createRateLimiter({
        windowMs: 60 * 60 * 1000, // 1 hour
        max: 3, // 3 requests per hour
        message: 'Too many sensitive operations, please try again later'
    }),
    
    // Command rate limiter (very short window for robot commands)
    command: createRateLimiter({
        windowMs: 1000, // 1 second
        max: 10, // 10 commands per second
        message: 'Command rate limit exceeded, please slow down',
        keyGenerator: (req) => {
            // Use user ID if available, fallback to IP
            return req.user?.userId || req.ip;
        }
    })
};

/**
 * Create custom key generator that combines IP and user
 */
const createUserKeyGenerator = (req) => {
    const userId = req.user?.userId || 'anonymous';
    const ip = req.ip;
    return `${userId}:${ip}`;
};

/**
 * Rate limiter for WebSocket connections
 */
const createSocketRateLimiter = (options = {}) => {
    const {
        windowMs = 1000, // 1 second
        max = 20, // 20 events per second
        keyGenerator = (socket) => socket.user?.userId || socket.handshake.address
    } = options;
    
    const store = new MemoryStore();
    
    return (socket, next) => {
        const key = keyGenerator(socket);
        const now = Date.now();
        
        let state = store.get(key);
        
        if (!state || now > state.expires) {
            state = {
                count: 0,
                resetTime: now + windowMs,
                expires: now + windowMs
            };
        }
        
        state.count++;
        store.set(key, state, windowMs);
        
        if (state.count > max) {
            logger.warn(`Socket rate limit exceeded for ${key}: ${state.count}/${max}`);
            return next(new Error('Rate limit exceeded'));
        }
        
        next();
    };
};

/**
 * Get rate limiter statistics
 */
const getStats = () => {
    return {
        activeKeys: defaultStore.size(),
        timestamp: new Date().toISOString()
    };
};

/**
 * Reset rate limit for specific key
 */
const resetKey = (key) => {
    defaultStore.reset(key);
    logger.info(`Rate limit reset for key: ${key}`);
};

module.exports = createRateLimiter;
module.exports.rateLimiters = rateLimiters;
module.exports.createSocketRateLimiter = createSocketRateLimiter;
module.exports.createUserKeyGenerator = createUserKeyGenerator;
module.exports.getStats = getStats;
module.exports.resetKey = resetKey;
