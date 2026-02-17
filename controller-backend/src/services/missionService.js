/**
 * Mission Management Service
 * Handles mission creation, execution tracking, and persistence
 */

const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const logger = require('../utils/logger');

class MissionService extends EventEmitter {
    constructor() {
        super();
        
        // In-memory storage (replace with database in production)
        this.missions = new Map();
        this.activeMission = null;
        this.missionHistory = [];
        
        // Mission templates
        this.templates = new Map();
        
        // Statistics
        this.stats = {
            totalMissions: 0,
            completedMissions: 0,
            failedMissions: 0,
            averageDuration: 0,
            totalDistance: 0
        };
        
        this.initializeTemplates();
    }
    
    /**
     * Initialize service
     */
    initialize() {
        logger.info('Mission service initialized');
    }
    
    /**
     * Initialize mission templates
     */
    initializeTemplates() {
        // Stage 1: Basic movement test
        this.templates.set('basic_movement', {
            name: 'Basic Movement Test',
            description: 'Test basic robot movement and control',
            difficulty: 'beginner',
            estimatedDuration: 120, // seconds
            waypoints: [
                { x: 0, y: 0, action: 'start', tasks: [{ type: 'wait', duration: 2 }] },
                { x: 100, y: 0, action: 'forward', tasks: [{ type: 'wait', duration: 1 }] },
                { x: 100, y: 100, action: 'turn_right', tasks: [{ type: 'wait', duration: 1 }] },
                { x: 0, y: 100, action: 'turn_left', tasks: [{ type: 'wait', duration: 1 }] },
                { x: 0, y: 0, action: 'return', tasks: [{ type: 'wait', duration: 2 }] }
            ]
        });
        
        // Stage 2: Line following
        this.templates.set('line_following', {
            name: 'Line Following Challenge',
            description: 'Follow line path through hospital corridors',
            difficulty: 'intermediate',
            estimatedDuration: 300,
            navigationMode: 'line_following',
            waypoints: [
                { x: 0, y: 0, action: 'start_line_following', tasks: [] },
                { x: 200, y: 0, action: 'checkpoint', tasks: [{ type: 'scan', duration: 3 }] },
                { x: 200, y: 200, action: 'intersection', tasks: [{ type: 'wait', duration: 2 }] },
                { x: 0, y: 200, action: 'checkpoint', tasks: [{ type: 'scan', duration: 3 }] },
                { x: 0, y: 0, action: 'finish', tasks: [{ type: 'wait', duration: 5 }] }
            ]
        });
        
        // Stage 3: Hospital delivery
        this.templates.set('hospital_delivery', {
            name: 'Medical Delivery Mission',
            description: 'Deliver supplies to different hospital zones',
            difficulty: 'advanced',
            estimatedDuration: 600,
            navigationMode: 'autonomous',
            waypoints: [
                { 
                    x: 0, y: 0, 
                    action: 'pickup', 
                    zone: 'pharmacy',
                    tasks: [{ type: 'delivery', item: 'medication', duration: 5 }] 
                },
                { 
                    x: 150, y: 100, 
                    action: 'deliver', 
                    zone: 'ward_a',
                    tasks: [{ type: 'delivery', item: 'medication', duration: 10 }] 
                },
                { 
                    x: 250, y: 200, 
                    action: 'deliver', 
                    zone: 'ward_b',
                    tasks: [{ type: 'delivery', item: 'supplies', duration: 8 }] 
                },
                { 
                    x: 100, y: 300, 
                    action: 'deliver', 
                    zone: 'emergency',
                    priority: 'high',
                    tasks: [{ type: 'delivery', item: 'emergency_kit', duration: 15 }] 
                },
                { 
                    x: 0, y: 0, 
                    action: 'return', 
                    zone: 'base',
                    tasks: [{ type: 'wait', duration: 5 }] 
                }
            ]
        });
        
        // Stage 4: Innovation challenge
        this.templates.set('innovation_challenge', {
            name: 'Innovation Challenge',
            description: 'Custom mission with advanced features',
            difficulty: 'expert',
            estimatedDuration: 900,
            navigationMode: 'mixed',
            customizable: true,
            waypoints: [] // To be filled by teams
        });
    }
    
    /**
     * Create new mission
     */
    async createMission(missionData) {
        try {
            const mission = {
                id: uuidv4(),
                name: missionData.name || 'Unnamed Mission',
                type: missionData.type || 'custom',
                description: missionData.description || '',
                waypoints: missionData.waypoints || [],
                tasks: missionData.tasks || [],
                parameters: missionData.parameters || {},
                priority: missionData.priority || 'normal',
                createdBy: missionData.userId || 'system',
                createdAt: new Date(),
                status: 'created',
                estimatedDuration: this.calculateEstimatedDuration(missionData),
                actualDuration: null,
                progress: 0,
                currentWaypoint: 0,
                startedAt: null,
                completedAt: null,
                error: null,
                results: {
                    waypointsCompleted: 0,
                    tasksCompleted: 0,
                    distanceTraveled: 0,
                    averageSpeed: 0
                }
            };
            
            // Validate mission
            this.validateMission(mission);
            
            // Store mission
            this.missions.set(mission.id, mission);
            this.stats.totalMissions++;
            
            logger.info(`Mission created: ${mission.id} - ${mission.name}`);
            this.emit('mission_created', mission);
            
            return mission;
            
        } catch (error) {
            logger.error('Error creating mission:', error);
            throw error;
        }
    }
    
    /**
     * Create mission from template
     */
    async createMissionFromTemplate(templateId, customizations = {}) {
        const template = this.templates.get(templateId);
        
        if (!template) {
            throw new Error(`Template not found: ${templateId}`);
        }
        
        const missionData = {
            name: customizations.name || template.name,
            type: templateId,
            description: customizations.description || template.description,
            waypoints: customizations.waypoints || template.waypoints,
            navigationMode: template.navigationMode,
            parameters: {
                ...template.parameters,
                ...customizations.parameters
            },
            ...customizations
        };
        
        return this.createMission(missionData);
    }
    
    /**
     * Start mission execution
     */
    async startMission(missionId) {
        const mission = this.missions.get(missionId);
        
        if (!mission) {
            throw new Error(`Mission not found: ${missionId}`);
        }
        
        if (mission.status === 'executing') {
            throw new Error('Mission is already executing');
        }
        
        if (this.activeMission && this.activeMission.status === 'executing') {
            throw new Error('Another mission is currently executing');
        }
        
        mission.status = 'executing';
        mission.startedAt = new Date();
        mission.progress = 0;
        mission.currentWaypoint = 0;
        
        this.activeMission = mission;
        
        logger.info(`Mission started: ${missionId}`);
        this.emit('mission_started', mission);
        
        return mission;
    }
    
    /**
     * Update mission progress
     */
    updateMissionProgress(missionId, progressData) {
        const mission = this.missions.get(missionId);
        
        if (!mission) {
            logger.error(`Mission not found for progress update: ${missionId}`);
            return;
        }
        
        // Update progress
        if (progressData.currentWaypoint !== undefined) {
            mission.currentWaypoint = progressData.currentWaypoint;
            mission.progress = mission.currentWaypoint / mission.waypoints.length;
        }
        
        if (progressData.results) {
            mission.results = { ...mission.results, ...progressData.results };
        }
        
        logger.debug(`Mission progress updated: ${missionId} - ${Math.round(mission.progress * 100)}%`);
        this.emit('mission_progress', mission);
    }
    
    /**
     * Complete mission
     */
    async completeMission(missionId, results = {}) {
        const mission = this.missions.get(missionId);
        
        if (!mission) {
            throw new Error(`Mission not found: ${missionId}`);
        }
        
        mission.status = 'completed';
        mission.completedAt = new Date();
        mission.actualDuration = mission.completedAt - mission.startedAt;
        mission.progress = 1.0;
        mission.results = { ...mission.results, ...results };
        
        // Update statistics
        this.stats.completedMissions++;
        this.updateAverageStats(mission);
        
        // Move to history
        this.missionHistory.push(mission);
        
        if (this.activeMission && this.activeMission.id === missionId) {
            this.activeMission = null;
        }
        
        logger.info(`Mission completed: ${missionId} in ${mission.actualDuration}ms`);
        this.emit('mission_completed', mission);
        
        return mission;
    }
    
    /**
     * Fail mission
     */
    async failMission(missionId, error) {
        const mission = this.missions.get(missionId);
        
        if (!mission) {
            throw new Error(`Mission not found: ${missionId}`);
        }
        
        mission.status = 'failed';
        mission.completedAt = new Date();
        mission.actualDuration = mission.completedAt - mission.startedAt;
        mission.error = error;
        
        this.stats.failedMissions++;
        
        // Move to history
        this.missionHistory.push(mission);
        
        if (this.activeMission && this.activeMission.id === missionId) {
            this.activeMission = null;
        }
        
        logger.error(`Mission failed: ${missionId} - ${error}`);
        this.emit('mission_failed', mission);
        
        return mission;
    }
    
    /**
     * Pause mission
     */
    async pauseMission(missionId) {
        const mission = this.missions.get(missionId);
        
        if (!mission) {
            throw new Error(`Mission not found: ${missionId}`);
        }
        
        if (mission.status !== 'executing') {
            throw new Error('Mission is not executing');
        }
        
        mission.status = 'paused';
        mission.pausedAt = new Date();
        
        logger.info(`Mission paused: ${missionId}`);
        this.emit('mission_paused', mission);
        
        return mission;
    }
    
    /**
     * Resume mission
     */
    async resumeMission(missionId) {
        const mission = this.missions.get(missionId);
        
        if (!mission) {
            throw new Error(`Mission not found: ${missionId}`);
        }
        
        if (mission.status !== 'paused') {
            throw new Error('Mission is not paused');
        }
        
        mission.status = 'executing';
        const pauseDuration = new Date() - mission.pausedAt;
        mission.totalPauseDuration = (mission.totalPauseDuration || 0) + pauseDuration;
        delete mission.pausedAt;
        
        logger.info(`Mission resumed: ${missionId}`);
        this.emit('mission_resumed', mission);
        
        return mission;
    }
    
    /**
     * Cancel mission
     */
    async cancelMission(missionId) {
        const mission = this.missions.get(missionId);
        
        if (!mission) {
            throw new Error(`Mission not found: ${missionId}`);
        }
        
        mission.status = 'cancelled';
        mission.completedAt = new Date();
        
        if (this.activeMission && this.activeMission.id === missionId) {
            this.activeMission = null;
        }
        
        logger.info(`Mission cancelled: ${missionId}`);
        this.emit('mission_cancelled', mission);
        
        return mission;
    }
    
    /**
     * Get mission by ID
     */
    getMission(missionId) {
        return this.missions.get(missionId);
    }
    
    /**
     * Get all missions
     */
    getAllMissions(filters = {}) {
        let missions = Array.from(this.missions.values());
        
        // Apply filters
        if (filters.status) {
            missions = missions.filter(m => m.status === filters.status);
        }
        
        if (filters.type) {
            missions = missions.filter(m => m.type === filters.type);
        }
        
        if (filters.createdBy) {
            missions = missions.filter(m => m.createdBy === filters.createdBy);
        }
        
        // Sort by creation date (newest first)
        missions.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
        
        return missions;
    }
    
    /**
     * Get active mission
     */
    getActiveMission() {
        return this.activeMission;
    }
    
    /**
     * Get mission templates
     */
    getTemplates() {
        return Array.from(this.templates.values());
    }
    
    /**
     * Get mission statistics
     */
    getStatistics() {
        return {
            ...this.stats,
            activeMissions: this.activeMission ? 1 : 0,
            totalInHistory: this.missionHistory.length,
            successRate: this.stats.totalMissions > 0 
                ? (this.stats.completedMissions / this.stats.totalMissions) * 100 
                : 0
        };
    }
    
    /**
     * Validate mission data
     */
    validateMission(mission) {
        if (!mission.waypoints || mission.waypoints.length === 0) {
            throw new Error('Mission must have at least one waypoint');
        }
        
        // Validate waypoints
        mission.waypoints.forEach((waypoint, index) => {
            if (typeof waypoint.x !== 'number' || typeof waypoint.y !== 'number') {
                throw new Error(`Waypoint ${index} must have valid x,y coordinates`);
            }
        });
    }
    
    /**
     * Calculate estimated duration
     */
    calculateEstimatedDuration(missionData) {
        const baseTime = 30; // 30 seconds per waypoint
        const waypointCount = missionData.waypoints ? missionData.waypoints.length : 0;
        const taskTime = missionData.tasks ? missionData.tasks.length * 15 : 0;
        
        return (baseTime * waypointCount) + taskTime;
    }
    
    /**
     * Update average statistics
     */
    updateAverageStats(mission) {
        const completed = this.stats.completedMissions;
        
        // Update average duration
        if (mission.actualDuration) {
            this.stats.averageDuration = (
                (this.stats.averageDuration * (completed - 1)) + mission.actualDuration
            ) / completed;
        }
        
        // Update total distance
        if (mission.results.distanceTraveled) {
            this.stats.totalDistance += mission.results.distanceTraveled;
        }
    }
}

// Export singleton instance
const missionService = new MissionService();
module.exports = missionService;
