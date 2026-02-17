# Multi-stage build for optimized production image
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache python3 make g++

# Copy package files
COPY package*.json ./

# Install dependencies with optimizations
RUN npm ci --only=production --ignore-scripts
RUN npm cache clean --force

# Production stage
FROM node:18-alpine AS production

# Create app user for security
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodeuser -u 1001

# Set working directory
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder --chown=nodeuser:nodejs /app/node_modules ./node_modules

# Copy application code
COPY --chown=nodeuser:nodejs . .

# Create logs directory
RUN mkdir -p logs && chown nodeuser:nodejs logs

# Performance optimizations
# Enable Node.js production optimizations
ENV NODE_ENV=production
ENV NODE_OPTIONS="--max-old-space-size=512 --optimize-for-size"

# Network optimizations for WebSocket
ENV UV_THREADPOOL_SIZE=16

# Expose port
EXPOSE 3001

# Switch to non-root user
USER nodeuser

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD node -e "const http = require('http'); \
    const req = http.request('http://localhost:3001/health', (res) => { \
        process.exit(res.statusCode === 200 ? 0 : 1); \
    }); req.on('error', () => process.exit(1)); req.end();"

# Start application
CMD ["node", "start-server.js"]