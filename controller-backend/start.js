#!/usr/bin/env node

/**
 * Medi Runner Backend Server - Start Script
 * Demonstration of WebSocket communication over WiFi
 */

const MediRunnerBackend = require('./src/app');
const logger = require('./src/utils/logger');

// Environment configuration
const config = {
    PORT: process.env.PORT || 3001,
    NODE_ENV: process.env.NODE_ENV || 'development',
    ROBOT_HOST: process.env.ROBOT_HOST || 'localhost',
    ROBOT_PORT: process.env.ROBOT_PORT || 8765,
    AUTO_CONNECT_ROBOT: process.env.AUTO_CONNECT_ROBOT || 'false',
    JWT_SECRET: process.env.JWT_SECRET || 'medi-runner-demo-secret',
    FRONTEND_URL: process.env.FRONTEND_URL || 'http://localhost:3000'
};

console.log('🚀 Starting Medi Runner Backend Server...');
console.log('=========================================');
console.log();

// Display configuration
console.log('📋 Configuration:');
console.log(`   • Environment: ${config.NODE_ENV}`);
console.log(`   • Server Port: ${config.PORT}`);
console.log(`   • Frontend URL: ${config.FRONTEND_URL}`);
console.log(`   • Robot Host: ${config.ROBOT_HOST}:${config.ROBOT_PORT}`);
console.log(`   • Auto-connect Robot: ${config.AUTO_CONNECT_ROBOT}`);
console.log();

// Set environment variables
Object.entries(config).forEach(([key, value]) => {
    process.env[key] = value;
});

console.log('🔧 Features Enabled:');
console.log('   • ✅ WebSocket Communication over WiFi');
console.log('   • ✅ Robot Command Processing');
console.log('   • ✅ Mission Management System');
console.log('   • ✅ Real-time Sensor Data Streaming');
console.log('   • ✅ Video Stream Management');
console.log('   • ✅ JWT Authentication & Authorization');
console.log('   • ✅ Rate Limiting & Security Middleware');
console.log('   • ✅ Input Validation & Sanitization');
console.log('   • ✅ Comprehensive Error Handling');
console.log();

// Create and start server
try {
    const server = new MediRunnerBackend();
    
    console.log('🌐 Starting server...');
    server.start();
    
    console.log();
    console.log('📡 WebSocket Communication Architecture:');
    console.log('   Robot Server (Python) ←→ WiFi ←→ Backend (Node.js) ←→ Frontend Dashboard');
    console.log();
    console.log('🎯 Competition Ready Features:');
    console.log('   • Stage 1: Delivery mission support');
    console.log('   • Stage 2: Patrol route management');
    console.log('   • Stage 3: Inspection task coordination');
    console.log('   • Stage 4: Emergency response protocols');
    console.log();
    console.log('🔍 Available Endpoints:');
    console.log(`   • Health Check: http://localhost:${config.PORT}/health`);
    console.log(`   • API Documentation: http://localhost:${config.PORT}/api`);
    console.log(`   • WebSocket: ws://localhost:${config.PORT}/socket.io`);
    console.log();
    console.log('📊 Monitoring:');
    console.log(`   • Robot Status: http://localhost:${config.PORT}/api/status`);
    console.log(`   • Active Missions: http://localhost:${config.PORT}/api/missions`);
    console.log();
    
    if (config.NODE_ENV === 'development') {
        console.log('🧪 Development Mode:');
        console.log('   • Simulation mode enabled for testing without hardware');
        console.log('   • Detailed logging and error reporting');
        console.log('   • CORS enabled for frontend development');
        console.log();
    }
    
    console.log('✅ Backend server is ready for robot communication!');
    console.log('💡 Connect your robot to the same WiFi network and point it to:');
    console.log(`   ws://${config.ROBOT_HOST}:${config.PORT}`);
    console.log();
    
} catch (error) {
    console.error('💥 Failed to start server:', error.message);
    process.exit(1);
}

// Handle process signals
process.on('SIGINT', () => {
    console.log('\n👋 Shutting down gracefully...');
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n👋 Received SIGTERM, shutting down gracefully...');
    process.exit(0);
});"