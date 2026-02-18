#!/usr/bin/env python3
"""
Test suite for the Medi-Runner Robot REST API.

Covers:
    - Movement endpoints (forward / backward / left / right)
    - Stop endpoint
    - Status endpoint
    - Buzzer endpoint
    - Health check
    - Input validation & edge cases
    - Motor controller unit tests

Run:
    cd robot-server
    pytest tests/test_api.py -v
"""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Ensure robot-server is on the path so config / robot imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api_server import app, _buzz
from robot.motor_controller import MotorController


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client():
    """Provide an async HTTP test client with motor initialised."""
    import api_server

    # Manually initialise the motor (ASGITransport does not trigger lifespan)
    api_server.motor = MotorController(simulation_mode=True)
    await api_server.motor.initialize()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await api_server.motor.cleanup()
    api_server.motor = None


@pytest.fixture
def motor():
    """Provide an initialised MotorController in simulation mode."""
    mc = MotorController(simulation_mode=True)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(mc.initialize())
    yield mc
    loop.run_until_complete(mc.cleanup())


# ===================================================================
# 1. Movement endpoint tests
# ===================================================================
class TestMoveForward:
    """POST /api/robot/forward"""

    @pytest.mark.anyio
    async def test_forward_default_speed(self, client):
        resp = await client.post("/api/robot/forward")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["action"] == "forward"
        assert "data" in body
        assert body["data"]["direction"] == "forward"

    @pytest.mark.anyio
    async def test_forward_custom_speed(self, client):
        resp = await client.post("/api/robot/forward", json={"speed": 75})
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["speed"] == 75

    @pytest.mark.anyio
    async def test_forward_with_duration(self, client):
        resp = await client.post("/api/robot/forward", json={"speed": 40, "duration": 0.1})
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["duration"] == 0.1
        assert body["data"]["status"] == "completed"

    @pytest.mark.anyio
    async def test_forward_max_speed(self, client):
        resp = await client.post("/api/robot/forward", json={"speed": 100})
        assert resp.status_code == 200
        assert resp.json()["data"]["speed"] == 100

    @pytest.mark.anyio
    async def test_forward_min_speed(self, client):
        resp = await client.post("/api/robot/forward", json={"speed": 0})
        assert resp.status_code == 200
        assert resp.json()["data"]["speed"] == 0


class TestMoveBackward:
    """POST /api/robot/backward"""

    @pytest.mark.anyio
    async def test_backward_default(self, client):
        resp = await client.post("/api/robot/backward")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["action"] == "backward"
        assert body["data"]["direction"] == "backward"

    @pytest.mark.anyio
    async def test_backward_custom_speed(self, client):
        resp = await client.post("/api/robot/backward", json={"speed": 30})
        assert resp.status_code == 200
        assert resp.json()["data"]["speed"] == 30


class TestMoveLeft:
    """POST /api/robot/left"""

    @pytest.mark.anyio
    async def test_left_default(self, client):
        resp = await client.post("/api/robot/left")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["action"] == "left"
        assert body["data"]["direction"] == "left"

    @pytest.mark.anyio
    async def test_left_with_speed_and_duration(self, client):
        resp = await client.post("/api/robot/left", json={"speed": 60, "duration": 0.1})
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["speed"] == 60
        assert body["data"]["status"] == "completed"


class TestMoveRight:
    """POST /api/robot/right"""

    @pytest.mark.anyio
    async def test_right_default(self, client):
        resp = await client.post("/api/robot/right")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["action"] == "right"
        assert body["data"]["direction"] == "right"

    @pytest.mark.anyio
    async def test_right_custom_speed(self, client):
        resp = await client.post("/api/robot/right", json={"speed": 90})
        assert resp.status_code == 200
        assert resp.json()["data"]["speed"] == 90


# ===================================================================
# 2. Stop endpoint tests
# ===================================================================
class TestStop:
    """POST /api/robot/stop"""

    @pytest.mark.anyio
    async def test_stop(self, client):
        # Move first, then stop
        await client.post("/api/robot/forward", json={"speed": 50})
        resp = await client.post("/api/robot/stop")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["action"] == "stop"

    @pytest.mark.anyio
    async def test_stop_when_already_stopped(self, client):
        resp = await client.post("/api/robot/stop")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ===================================================================
# 3. Status endpoint tests
# ===================================================================
class TestStatus:
    """GET /api/robot/status"""

    @pytest.mark.anyio
    async def test_get_status(self, client):
        resp = await client.get("/api/robot/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["action"] == "status"
        data = body["data"]
        assert "motors" in data
        assert "position" in data

    @pytest.mark.anyio
    async def test_status_after_movement(self, client):
        await client.post("/api/robot/forward", json={"speed": 70})
        resp = await client.get("/api/robot/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["motors"]["is_moving"] is True
        assert data["motors"]["direction"] == "forward"

    @pytest.mark.anyio
    async def test_status_after_stop(self, client):
        await client.post("/api/robot/forward", json={"speed": 50})
        await client.post("/api/robot/stop")
        resp = await client.get("/api/robot/status")
        data = resp.json()["data"]
        assert data["motors"]["is_moving"] is False
        assert data["motors"]["direction"] == "stopped"


# ===================================================================
# 4. Buzzer endpoint tests
# ===================================================================
class TestBuzzer:
    """POST /api/robot/buzzer"""

    @pytest.mark.anyio
    async def test_buzzer_default(self, client):
        resp = await client.post("/api/robot/buzzer")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["action"] == "buzzer"
        assert body["data"]["times"] == 1

    @pytest.mark.anyio
    async def test_buzzer_multiple_beeps(self, client):
        resp = await client.post("/api/robot/buzzer", json={"times": 3, "duration": 0.05})
        assert resp.status_code == 200
        assert resp.json()["data"]["times"] == 3


# ===================================================================
# 5. Health check
# ===================================================================
class TestHealth:
    """GET /health"""

    @pytest.mark.anyio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "simulation_mode" in body
        assert "timestamp" in body


# ===================================================================
# 6. Input validation & edge-case tests
# ===================================================================
class TestValidation:

    @pytest.mark.anyio
    async def test_speed_above_max_rejected(self, client):
        resp = await client.post("/api/robot/forward", json={"speed": 150})
        assert resp.status_code == 422  # Pydantic validation error

    @pytest.mark.anyio
    async def test_speed_below_min_rejected(self, client):
        resp = await client.post("/api/robot/forward", json={"speed": -10})
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_negative_duration_rejected(self, client):
        resp = await client.post("/api/robot/forward", json={"duration": -1})
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_invalid_json_body(self, client):
        resp = await client.post(
            "/api/robot/forward",
            content="not-json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_get_on_post_endpoint(self, client):
        resp = await client.get("/api/robot/forward")
        assert resp.status_code == 405  # Method Not Allowed

    @pytest.mark.anyio
    async def test_nonexistent_endpoint(self, client):
        resp = await client.post("/api/robot/fly")
        assert resp.status_code in (404, 405)


# ===================================================================
# 7. Motor controller unit tests (no HTTP, pure async)
# ===================================================================
class TestMotorController:

    @pytest.mark.anyio
    async def test_initialize(self):
        mc = MotorController(simulation_mode=True)
        result = await mc.initialize()
        assert result is True
        assert mc.is_initialized is True
        await mc.cleanup()

    @pytest.mark.anyio
    async def test_move_forward(self):
        mc = MotorController(simulation_mode=True)
        await mc.initialize()
        result = await mc.move("forward", 50, 0)
        assert result["direction"] == "forward"
        assert result["speed"] == 50
        assert mc.is_moving is True
        assert mc.current_direction == "forward"
        await mc.cleanup()

    @pytest.mark.anyio
    async def test_move_backward(self):
        mc = MotorController(simulation_mode=True)
        await mc.initialize()
        result = await mc.move("backward", 60, 0)
        assert result["direction"] == "backward"
        assert mc.left_motor_speed == -60
        assert mc.right_motor_speed == -60
        await mc.cleanup()

    @pytest.mark.anyio
    async def test_move_left(self):
        mc = MotorController(simulation_mode=True)
        await mc.initialize()
        result = await mc.move("left", 50, 0)
        assert result["direction"] == "left"
        assert mc.left_motor_speed < 0  # left motor reverses
        assert mc.right_motor_speed > 0
        await mc.cleanup()

    @pytest.mark.anyio
    async def test_move_right(self):
        mc = MotorController(simulation_mode=True)
        await mc.initialize()
        result = await mc.move("right", 50, 0)
        assert result["direction"] == "right"
        assert mc.left_motor_speed > 0
        assert mc.right_motor_speed < 0  # right motor reverses
        await mc.cleanup()

    @pytest.mark.anyio
    async def test_stop(self):
        mc = MotorController(simulation_mode=True)
        await mc.initialize()
        await mc.move("forward", 70, 0)
        result = await mc.stop()
        assert result["status"] == "completed"
        assert mc.is_moving is False
        assert mc.left_motor_speed == 0
        assert mc.right_motor_speed == 0
        await mc.cleanup()

    @pytest.mark.anyio
    async def test_emergency_stop(self):
        mc = MotorController(simulation_mode=True)
        await mc.initialize()
        await mc.move("forward", 80, 0)
        result = await mc.emergency_stop()
        assert result["status"] == "executed"
        assert mc.is_moving is False
        assert mc.current_direction == "emergency_stopped"
        await mc.cleanup()

    @pytest.mark.anyio
    async def test_speed_clamped_to_100(self):
        mc = MotorController(simulation_mode=True)
        await mc.initialize()
        result = await mc.move("forward", 200, 0)
        assert result["speed"] == 100  # clamped
        await mc.cleanup()

    @pytest.mark.anyio
    async def test_speed_clamped_to_0(self):
        mc = MotorController(simulation_mode=True)
        await mc.initialize()
        result = await mc.move("forward", -50, 0)
        assert result["speed"] == 0  # clamped
        await mc.cleanup()

    @pytest.mark.anyio
    async def test_move_with_duration_autostops(self):
        mc = MotorController(simulation_mode=True)
        await mc.initialize()
        result = await mc.move("forward", 50, 0.15)
        # After duration the controller auto-stops
        assert mc.is_moving is False
        assert mc.current_direction == "stopped"
        await mc.cleanup()

    @pytest.mark.anyio
    async def test_get_status(self):
        mc = MotorController(simulation_mode=True)
        await mc.initialize()
        status = await mc.get_status()
        assert "motors" in status
        assert "position" in status
        assert status["status"] == "online"
        await mc.cleanup()

    @pytest.mark.anyio
    async def test_move_without_init_raises(self):
        mc = MotorController(simulation_mode=True)
        with pytest.raises(Exception, match="not initialized"):
            await mc.move("forward", 50, 0)

    @pytest.mark.anyio
    async def test_set_individual_motor_speeds(self):
        mc = MotorController(simulation_mode=True)
        await mc.initialize()
        result = await mc.set_speed(40, 60)
        assert result["left_speed"] == 40
        assert result["right_speed"] == 60
        await mc.cleanup()

    @pytest.mark.anyio
    async def test_pid_values_round_trip(self):
        mc = MotorController(simulation_mode=True)
        await mc.initialize()
        await mc.set_pid_values(kp=2.0, ki=0.5, kd=0.1)
        vals = await mc.get_pid_values()
        assert vals["kp"] == 2.0
        assert vals["ki"] == 0.5
        assert vals["kd"] == 0.1
        await mc.cleanup()

    @pytest.mark.anyio
    async def test_reset_pid(self):
        mc = MotorController(simulation_mode=True)
        await mc.initialize()
        await mc.set_pid_values(kp=5.0)
        result = await mc.reset_pid()
        assert result["status"] == "reset"
        await mc.cleanup()


# ===================================================================
# 8. Sequential movement tests (integration-style)
# ===================================================================
class TestSequentialMovements:
    """Verify the Stage-1 demo sequence via the API."""

    @pytest.mark.anyio
    async def test_demo_sequence(self, client):
        """
        Stage 1 demonstration:
            forward → stop → right → stop → left → stop → backward → stop
        """
        for direction in ("forward", "right", "left", "backward"):
            resp = await client.post(
                f"/api/robot/{direction}", json={"speed": 50, "duration": 0.05}
            )
            assert resp.status_code == 200
            assert resp.json()["success"] is True

            resp = await client.post("/api/robot/stop")
            assert resp.status_code == 200

        # Final status should be stopped
        resp = await client.get("/api/robot/status")
        data = resp.json()["data"]
        assert data["motors"]["is_moving"] is False

    @pytest.mark.anyio
    async def test_rapid_direction_changes(self, client):
        """Ensure rapid direction changes don't crash the controller."""
        directions = ["forward", "left", "right", "backward", "forward", "right"]
        for d in directions:
            resp = await client.post(f"/api/robot/{d}", json={"speed": 60})
            assert resp.status_code == 200
        resp = await client.post("/api/robot/stop")
        assert resp.status_code == 200


# ===================================================================
# 9. Response structure tests
# ===================================================================
class TestResponseStructure:

    @pytest.mark.anyio
    async def test_response_has_timestamp(self, client):
        resp = await client.post("/api/robot/forward")
        body = resp.json()
        assert "timestamp" in body
        assert isinstance(body["timestamp"], float)

    @pytest.mark.anyio
    async def test_response_has_all_fields(self, client):
        resp = await client.post("/api/robot/forward")
        body = resp.json()
        for key in ("success", "action", "message", "data", "timestamp"):
            assert key in body, f"Missing key: {key}"
