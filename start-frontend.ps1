#!/usr/bin/env powershell

# Medi Runner Challenge 2025 - Frontend Build and Deploy Script
# This script builds and runs the frontend dashboard in Docker container

param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "development",
    
    [Parameter(Mandatory=$false)]
    [string]$BackendUrl = "http://localhost:3001",
    
    [Parameter(Mandatory=$false)]
    [string]$WebSocketUrl = "ws://localhost:3001",
    
    [Parameter(Mandatory=$false)]
    [switch]$NoBuild,
    
    [Parameter(Mandatory=$false)]
    [switch]$Production
)

Write-Host "🚀 Medi Runner Challenge 2025 - Frontend Deployment" -ForegroundColor Green
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host "Backend URL: $BackendUrl" -ForegroundColor Yellow
Write-Host "WebSocket URL: $WebSocketUrl" -ForegroundColor Yellow

# Set working directory
$WorkingDir = "d:\DIPS-AS\Workbench\medi-runner"
Set-Location $WorkingDir

# Environment configuration
if ($Production) {
    $ComposeFile = "docker-compose.full-stack.yml"
    $Environment = "production"
} else {
    $ComposeFile = "docker-compose.dev.yml"
}

Write-Host "`n📦 Building Docker images..." -ForegroundColor Blue

# Build frontend Docker image
if (!$NoBuild) {
    Write-Host "Building frontend image..." -ForegroundColor Cyan
    
    docker build `
        --file .\controller-frontend\Dockerfile.frontend `
        --build-arg NEXT_PUBLIC_API_URL=$BackendUrl `
        --build-arg NEXT_PUBLIC_WS_URL=$WebSocketUrl `
        --tag medi-runner-frontend:latest `
        .\controller-frontend\
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Frontend build failed!"
        exit 1
    }
    
    Write-Host "✅ Frontend image built successfully!" -ForegroundColor Green
}

# Create necessary directories
$Directories = @(
    "logs\frontend",
    "logs\backend",
    "logs\nginx",
    "data\uploads",
    "database\init"
)

foreach ($Dir in $Directories) {
    $FullPath = Join-Path $WorkingDir $Dir
    if (!(Test-Path $FullPath)) {
        New-Item -Path $FullPath -ItemType Directory -Force
        Write-Host "📁 Created directory: $Dir" -ForegroundColor Cyan
    }
}

# Start services
Write-Host "`n🚢 Starting Docker services..." -ForegroundColor Blue

if ($Production) {
    # Production deployment
    Write-Host "Starting production environment..." -ForegroundColor Magenta
    docker-compose -f $ComposeFile up -d
} else {
    # Development deployment - frontend only for now
    Write-Host "Starting development environment..." -ForegroundColor Magenta
    
    # Check if backend is running
    $BackendRunning = $false
    try {
        $Response = Invoke-WebRequest -Uri "$BackendUrl/health" -Method GET -TimeoutSec 5
        if ($Response.StatusCode -eq 200) {
            $BackendRunning = $true
            Write-Host "✅ Backend is already running at $BackendUrl" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️ Backend not detected at $BackendUrl" -ForegroundColor Yellow
    }
    
    # Run frontend container
    Write-Host "Starting frontend container..." -ForegroundColor Cyan
    
    docker run `
        --name medi-runner-frontend-dev `
        --rm `
        --detach `
        --publish 3000:3000 `
        --env NEXT_PUBLIC_API_URL=$BackendUrl `
        --env NEXT_PUBLIC_WS_URL=$WebSocketUrl `
        --env NODE_ENV=$Environment `
        medi-runner-frontend:latest
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Failed to start frontend container!"
        exit 1
    }
}

# Wait for services to be ready
Write-Host "`n⏳ Waiting for services to be ready..." -ForegroundColor Blue

$MaxRetries = 30
$RetryCount = 0
$FrontendReady = $false

do {
    Start-Sleep -Seconds 2
    $RetryCount++
    
    try {
        $Response = Invoke-WebRequest -Uri "http://localhost:3000" -Method GET -TimeoutSec 5
        if ($Response.StatusCode -eq 200) {
            $FrontendReady = $true
            break
        }
    } catch {
        # Service not ready yet
    }
    
    Write-Host "." -NoNewline -ForegroundColor Yellow
    
} while ($RetryCount -lt $MaxRetries)

Write-Host ""

if ($FrontendReady) {
    Write-Host "🎉 Frontend is ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Dashboard URLs:" -ForegroundColor Cyan
    Write-Host "   Frontend Dashboard: http://localhost:3000" -ForegroundColor White
    
    if ($Production) {
        Write-Host "   Nginx Proxy: http://localhost" -ForegroundColor White
        Write-Host "   Grafana Monitoring: http://localhost:3001" -ForegroundColor White
        Write-Host "   Prometheus Metrics: http://localhost:9090" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "📊 Container Status:" -ForegroundColor Cyan
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=medi-runner"
    
    Write-Host ""
    Write-Host "🔧 Useful Commands:" -ForegroundColor Cyan
    Write-Host "   View frontend logs: docker logs -f medi-runner-frontend-dev" -ForegroundColor White
    Write-Host "   Stop frontend: docker stop medi-runner-frontend-dev" -ForegroundColor White
    
    if ($Production) {
        Write-Host "   View all logs: docker-compose -f $ComposeFile logs -f" -ForegroundColor White
        Write-Host "   Stop all services: docker-compose -f $ComposeFile down" -ForegroundColor White
    }
    
} else {
    Write-Error "❌ Frontend failed to start within timeout period!"
    Write-Host ""
    Write-Host "🔍 Troubleshooting:" -ForegroundColor Yellow
    Write-Host "   Check frontend logs: docker logs medi-runner-frontend-dev" -ForegroundColor White
    Write-Host "   Check running containers: docker ps -a" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "✅ Medi Runner Frontend deployment completed successfully!" -ForegroundColor Green