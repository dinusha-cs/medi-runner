/**
 * Authentication Routes
 * Handles user registration, login, and JWT token management
 */

const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const Joi = require('joi');
const router = express.Router();

const logger = require('../utils/logger');
const { validateRequest } = require('../middleware/validation');
const rateLimiter = require('../middleware/rateLimiter');

// Mock user database (replace with real database in production)
const users = new Map();
const teams = new Map();

// Validation schemas
const loginSchema = Joi.object({
    username: Joi.string().alphanum().min(3).max(30).required(),
    password: Joi.string().min(6).required()
});

const registerSchema = Joi.object({
    username: Joi.string().alphanum().min(3).max(30).required(),
    password: Joi.string().min(6).required(),
    email: Joi.string().email(),
    teamName: Joi.string().min(3).max(50).required(),
    role: Joi.string().valid('pilot', 'copilot', 'innovation_lead').required()
});

// Rate limiting for auth endpoints
const authLimiter = rateLimiter({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 5, // 5 attempts per window
    message: 'Too many authentication attempts, please try again later'
});

/**
 * POST /api/auth/register
 * Register a new user and team
 */
router.post('/register', authLimiter, validateRequest(registerSchema), async (req, res) => {
    try {
        const { username, password, email, teamName, role } = req.body;
        
        // Check if user already exists
        if (users.has(username)) {
            return res.status(409).json({
                error: 'Username already exists',
                code: 'USER_EXISTS'
            });
        }
        
        // Check if team already exists
        let team = teams.get(teamName);
        if (!team) {
            // Create new team
            team = {
                name: teamName,
                createdAt: new Date(),
                members: [],
                settings: {
                    robotName: `${teamName}-robot`,
                    difficulty: 'beginner'
                }
            };
            teams.set(teamName, team);
        }
        
        // Hash password
        const saltRounds = 12;
        const hashedPassword = await bcrypt.hash(password, saltRounds);
        
        // Create user
        const user = {
            username,
            email,
            password: hashedPassword,
            teamName,
            role,
            createdAt: new Date(),
            isActive: true
        };
        
        users.set(username, user);
        team.members.push({
            username,
            role,
            joinedAt: new Date()
        });
        
        // Generate JWT token
        const token = jwt.sign(
            { 
                username, 
                teamName, 
                role,
                userId: username // Simple ID for this demo
            },
            process.env.JWT_SECRET || 'medi-runner-secret-key',
            { expiresIn: '24h' }
        );
        
        logger.info(`New user registered: ${username} (${role}) for team ${teamName}`);
        
        res.status(201).json({
            message: 'User registered successfully',
            token,
            user: {
                username,
                email,
                teamName,
                role,
                createdAt: user.createdAt
            },
            team: {
                name: teamName,
                memberCount: team.members.length,
                settings: team.settings
            }
        });
        
    } catch (error) {
        logger.error('Registration error:', error);
        res.status(500).json({
            error: 'Registration failed',
            code: 'REGISTRATION_ERROR'
        });
    }
});

/**
 * POST /api/auth/login
 * Authenticate user and return JWT token
 */
router.post('/login', authLimiter, validateRequest(loginSchema), async (req, res) => {
    try {
        const { username, password } = req.body;
        
        // Find user
        const user = users.get(username);
        if (!user) {
            return res.status(401).json({
                error: 'Invalid credentials',
                code: 'INVALID_CREDENTIALS'
            });
        }
        
        // Check if user is active
        if (!user.isActive) {
            return res.status(403).json({
                error: 'Account is disabled',
                code: 'ACCOUNT_DISABLED'
            });
        }
        
        // Verify password
        const isValidPassword = await bcrypt.compare(password, user.password);
        if (!isValidPassword) {
            return res.status(401).json({
                error: 'Invalid credentials',
                code: 'INVALID_CREDENTIALS'
            });
        }
        
        // Get team info
        const team = teams.get(user.teamName);
        
        // Generate JWT token
        const token = jwt.sign(
            { 
                username, 
                teamName: user.teamName, 
                role: user.role,
                userId: username
            },
            process.env.JWT_SECRET || 'medi-runner-secret-key',
            { expiresIn: '24h' }
        );
        
        logger.info(`User logged in: ${username}`);
        
        res.json({
            message: 'Login successful',
            token,
            user: {
                username,
                email: user.email,
                teamName: user.teamName,
                role: user.role,
                createdAt: user.createdAt
            },
            team: team ? {
                name: team.name,
                memberCount: team.members.length,
                settings: team.settings
            } : null
        });
        
    } catch (error) {
        logger.error('Login error:', error);
        res.status(500).json({
            error: 'Login failed',
            code: 'LOGIN_ERROR'
        });
    }
});

/**
 * POST /api/auth/logout
 * Logout user (for session cleanup)
 */
router.post('/logout', (req, res) => {
    // In a real implementation, you might invalidate the token
    // For JWT, client-side deletion is usually sufficient
    
    logger.info('User logged out');
    
    res.json({
        message: 'Logout successful'
    });
});

/**
 * GET /api/auth/me
 * Get current user information
 */
router.get('/me', require('../middleware/auth').required, (req, res) => {
    const { username, teamName, role } = req.user;
    const user = users.get(username);
    const team = teams.get(teamName);
    
    if (!user) {
        return res.status(404).json({
            error: 'User not found',
            code: 'USER_NOT_FOUND'
        });
    }
    
    res.json({
        user: {
            username,
            email: user.email,
            teamName,
            role,
            createdAt: user.createdAt
        },
        team: team ? {
            name: team.name,
            memberCount: team.members.length,
            members: team.members,
            settings: team.settings
        } : null
    });
});

/**
 * PUT /api/auth/team/settings
 * Update team settings
 */
router.put('/team/settings', require('../middleware/auth').required, (req, res) => {
    try {
        const { teamName } = req.user;
        const { robotName, difficulty } = req.body;
        
        const team = teams.get(teamName);
        if (!team) {
            return res.status(404).json({
                error: 'Team not found',
                code: 'TEAM_NOT_FOUND'
            });
        }
        
        // Update team settings
        if (robotName) team.settings.robotName = robotName;
        if (difficulty) team.settings.difficulty = difficulty;
        
        logger.info(`Team settings updated for ${teamName}`);
        
        res.json({
            message: 'Team settings updated',
            settings: team.settings
        });
        
    } catch (error) {
        logger.error('Team settings update error:', error);
        res.status(500).json({
            error: 'Failed to update team settings',
            code: 'UPDATE_ERROR'
        });
    }
});

/**
 * GET /api/auth/teams
 * Get list of all teams (for admin or leaderboard)
 */
router.get('/teams', (req, res) => {
    const teamList = Array.from(teams.values()).map(team => ({
        name: team.name,
        memberCount: team.members.length,
        createdAt: team.createdAt,
        robotName: team.settings.robotName
    }));
    
    res.json({
        teams: teamList,
        totalTeams: teamList.length
    });
});

module.exports = router;
