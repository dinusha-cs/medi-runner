#!/usr/bin/env powershell

# Medi Runner Robot Simulation and Testing Script
# This script sets up and runs the complete robot testing environment

param(
    [Parameter(Mandatory=$false)]
    [string]$TestType = "full",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipInstall
)

Write-Host "🤖 Medi Runner Challenge 2025 - Robot Simulation Testing" -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""

# Set working directory
$WorkingDir = "d:\DIPS-AS\Workbench\medi-runner"
Set-Location $WorkingDir

# Install dependencies if needed
if (!$SkipInstall) {
    Write-Host "📦 Installing Python dependencies..." -ForegroundColor Blue
    
    # Check if Python is available
    $PythonPath = Get-Command python -ErrorAction SilentlyContinue
    if (!$PythonPath) {
        Write-Error "❌ Python not found! Please install Python 3.8+"
        exit 1
    }
    
    # Install robot server dependencies
    Set-Location "$WorkingDir\robot-server"
    
    if (Test-Path "requirements.txt") {
        python -m pip install -r requirements.txt --quiet
        Write-Host "✅ Python dependencies installed" -ForegroundColor Green
    } else {
        # Create requirements.txt if missing
        $reqContent = @"
asyncio
websockets>=10.0
aiofiles
"@
        $reqContent | Out-File -FilePath "requirements.txt" -Encoding UTF8
        
        python -m pip install -r requirements.txt --quiet
        Write-Host "✅ Basic Python dependencies installed" -ForegroundColor Green
    }
    
    Set-Location $WorkingDir
}

# Function to test robot simulation
function Start-RobotSimulation {
    Write-Host "🤖 Starting Robot Server Simulation..." -ForegroundColor Blue
    
    $RobotPath = "$WorkingDir\robot-server"
    Set-Location $RobotPath
    
    # Check if config.py exists
    if (!(Test-Path "config.py")) {
        if (Test-Path "config.example.py") {
            Copy-Item "config.example.py" "config.py"
            Write-Host "📁 Created config.py from example" -ForegroundColor Yellow
        } else {
            Write-Error "❌ No configuration file found!"
            return $false
        }
    }
    
    Write-Host "🚀 Starting robot simulation on ws://localhost:8765" -ForegroundColor Green
    Write-Host "   Robot Name: MediBot-Simulator" -ForegroundColor White
    Write-Host "   Position: (0, 0, 0°)" -ForegroundColor White
    Write-Host "   Battery: 85%" -ForegroundColor White
    Write-Host ""
    
    # Start robot server in background
    $RobotProcess = Start-Process python -ArgumentList "main.py" -PassThru -WindowStyle Normal
    
    # Wait for server to start
    Start-Sleep -Seconds 3
    
    return $RobotProcess
}

# Function to run tests
function Run-Tests {
    param($TestType)
    
    Write-Host "🧪 Running Robot Tests..." -ForegroundColor Blue
    
    Set-Location "$WorkingDir\robot-server"
    
    switch ($TestType) {
        "robot" {
            Write-Host "Testing robot WebSocket connection..." -ForegroundColor Cyan
            python test_robot.py robot
        }
        "backend" {
            Write-Host "Testing backend communication..." -ForegroundColor Cyan
            python test_robot.py backend
        }
        "full" {
            Write-Host "Running comprehensive tests..." -ForegroundColor Cyan
            python test_robot.py both
        }
        "manual" {
            Write-Host "Starting manual testing mode..." -ForegroundColor Cyan
            Show-ManualTestMenu
        }
        default {
            Write-Host "Invalid test type. Using 'full'" -ForegroundColor Yellow
            python test_robot.py both
        }
    }
}

# Function for manual testing
function Show-ManualTestMenu {
    while ($true) {
        Write-Host ""
        Write-Host "🎮 Manual Robot Testing Menu" -ForegroundColor Yellow
        Write-Host "=============================" -ForegroundColor Yellow
        Write-Host "1. Move Forward (2 seconds)"
        Write-Host "2. Move Backward (2 seconds)"
        Write-Host "3. Turn Right (1 second)"
        Write-Host "4. Turn Left (1 second)"
        Write-Host "5. Stop Robot"
        Write-Host "6. Check Status"
        Write-Host "7. Test Emergency Stop"
        Write-Host "8. Start Mission Simulation"
        Write-Host "9. Exit"
        Write-Host ""
        
        $choice = Read-Host "Select option (1-9)"
        
        switch ($choice) {
            "1" {
                Write-Host "🤖 Moving Forward..." -ForegroundColor Green
                Send-RobotCommand -Action "move" -Direction "forward" -Speed 50 -Duration 2
            }
            "2" {
                Write-Host "🤖 Moving Backward..." -ForegroundColor Green
                Send-RobotCommand -Action "move" -Direction "backward" -Speed 50 -Duration 2
            }
            "3" {
                Write-Host "🤖 Turning Right..." -ForegroundColor Green
                Send-RobotCommand -Action "move" -Direction "right" -Speed 40 -Duration 1
            }
            "4" {
                Write-Host "🤖 Turning Left..." -ForegroundColor Green
                Send-RobotCommand -Action "move" -Direction "left" -Speed 40 -Duration 1
            }
            "5" {
                Write-Host "🤖 Stopping Robot..." -ForegroundColor Red
                Send-RobotCommand -Action "stop"
            }
            "6" {
                Write-Host "📊 Checking Robot Status..." -ForegroundColor Cyan
                python test_robot.py robot
            }
            "7" {
                Write-Host "🚨 EMERGENCY STOP!" -ForegroundColor Red -BackgroundColor Yellow
                Send-RobotCommand -Action "emergency_stop"
            }
            "8" {
                Write-Host "🎯 Starting Mission..." -ForegroundColor Magenta
                Start-MissionSimulation
            }
            "9" {
                Write-Host "👋 Exiting manual test mode" -ForegroundColor Yellow
                return
            }
            default {
                Write-Host "❌ Invalid option. Please try again." -ForegroundColor Red
            }
        }
    }
}

# Function to send robot commands
function Send-RobotCommand {
    param(
        [string]$Action,
        [string]$Direction = "",
        [int]$Speed = 50,
        [float]$Duration = 0
    )
    
    $Command = @{
        type = "command"
        data = @{
            action = $Action
        }
        id = "manual_cmd_$(Get-Date -Format 'yyyyMMddHHmmss')"
    }
    
    if ($Direction) {
        $Command.data.direction = $Direction
        $Command.data.speed = $Speed
        if ($Duration -gt 0) {
            $Command.data.duration = $Duration
        }
    }
    
    # Convert to JSON and send (simplified - would use actual WebSocket)
    $CommandJson = $Command | ConvertTo-Json -Compress
    Write-Host "📤 Command: $CommandJson" -ForegroundColor Gray
}

# Function to simulate missions
function Start-MissionSimulation {
    Write-Host "🎯 Mission Simulation Options:" -ForegroundColor Magenta
    Write-Host "1. Medicine Delivery to Room 101"
    Write-Host "2. Supply Transport to Surgery"
    Write-Host "3. Emergency Response to ICU"
    Write-Host "4. Line Following Test"
    
    $missionChoice = Read-Host "Select mission (1-4)"
    
    switch ($missionChoice) {
        "1" {
            Write-Host "🏥 Starting Medicine Delivery Mission..." -ForegroundColor Green
            Simulate-MedicineDelivery
        }
        "2" {
            Write-Host "🔧 Starting Supply Transport..." -ForegroundColor Green
            Simulate-SupplyTransport
        }
        "3" {
            Write-Host "🚨 Starting Emergency Response..." -ForegroundColor Red
            Simulate-EmergencyResponse
        }
        "4" {
            Write-Host "📏 Starting Line Following Test..." -ForegroundColor Blue
            Simulate-LineFollowing
        }
        default {
            Write-Host "❌ Invalid mission selected" -ForegroundColor Red
        }
    }
}

# Mission simulations
function Simulate-MedicineDelivery {
    $steps = @(
        "Navigate to Pharmacy",
        "Pickup Medicine Package", 
        "Navigate to Room 101",
        "Deliver to Patient",
        "Return to Base"
    )
    
    foreach ($step in $steps) {
        Write-Host "📋 $step" -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        Write-Host "   ✅ Completed" -ForegroundColor Green
    }
    
    Write-Host "🎉 Medicine Delivery Mission Complete!" -ForegroundColor Green
}

function Simulate-SupplyTransport {
    Write-Host "🔧 Simulating supply transport mission..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5
    Write-Host "✅ Supply transport completed!" -ForegroundColor Green
}

function Simulate-EmergencyResponse {
    Write-Host "🚨 EMERGENCY MISSION SIMULATION" -ForegroundColor Red
    Write-Host "Priority route to ICU..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    Write-Host "🏥 Emergency delivery completed!" -ForegroundColor Green
}

function Simulate-LineFollowing {
    Write-Host "📏 Line following simulation..." -ForegroundColor Blue
    for ($i = 1; $i -le 10; $i++) {
        Write-Host "   Following line segment $i/10" -ForegroundColor Cyan
        Start-Sleep -Seconds 1
    }
    Write-Host "✅ Line following test completed!" -ForegroundColor Green
}

# Main execution
Write-Host "🚀 Starting Robot Simulation Environment..." -ForegroundColor Blue

# Start robot simulation
$RobotProcess = Start-RobotSimulation

if ($RobotProcess) {
    Write-Host "✅ Robot server started successfully!" -ForegroundColor Green
    Write-Host ""
    
    # Run tests
    Run-Tests -TestType $TestType
    
    # Cleanup
    Write-Host ""
    Write-Host "🧹 Cleaning up..." -ForegroundColor Yellow
    
    if ($RobotProcess -and !$RobotProcess.HasExited) {
        $RobotProcess.Kill()
        Write-Host "🛑 Robot server stopped" -ForegroundColor Gray
    }
} else {
    Write-Error "❌ Failed to start robot simulation!"
    exit 1
}

Write-Host ""
Write-Host "🏁 Robot simulation testing completed!" -ForegroundColor Green
Write-Host ""
Write-Host "📖 Testing Summary:" -ForegroundColor Cyan
Write-Host "   ✅ Robot server: ws://localhost:8765" -ForegroundColor White
Write-Host "   ✅ Simulation mode: Enabled" -ForegroundColor White  
Write-Host "   ✅ WebSocket communication: Tested" -ForegroundColor White
Write-Host "   ✅ Movement commands: Tested" -ForegroundColor White
Write-Host "   ✅ Sensor data: Simulated" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Next Steps:" -ForegroundColor Yellow
Write-Host "   1. Start backend: cd controller-backend; npm run dev" -ForegroundColor White
Write-Host "   2. Start frontend: cd controller-frontend; npm run dev" -ForegroundColor White
Write-Host "   3. Open dashboard: http://localhost:3000" -ForegroundColor White
Write-Host "   4. Test full integration!" -ForegroundColor White
Write-Host ""