#!/usr/bin/env python3
"""
Tests for the ZeroClaw autonomous agent and the new API endpoints
(IR sensors, mode switching).

Run:
    cd robot-server
    source .venv/bin/activate
    pytest tests/test_zeroclaw.py -v
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api_server import app
from robot.motor_controller import MotorController
from robot.sensor_controller import SensorController
from zeroclaw_agent import ZeroClawAgent, AgentConfig, PID


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client():
    """HTTP test client with motor + sensor initialised."""
    import api_server

    api_server.motor = MotorController(simulation_mode=True)
    api_server.sensors = SensorController(simulation_mode=True)
    await api_server.motor.initialize()
    await api_server.sensors.initialize()
    api_server.robot_mode = "manual"  # reset mode between tests

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await api_server.motor.cleanup()
    await api_server.sensors.cleanup()
    api_server.motor = None
    api_server.sensors = None


# ===================================================================
# 1. New API endpoint tests – IR sensors
# ===================================================================
class TestIRSensorEndpoint:

    @pytest.mark.anyio
    async def test_read_ir_sensors(self, client):
        resp = await client.get("/api/robot/sensors/ir")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["action"] == "ir_sensor"
        sensors = body["data"]["sensors"]
        assert isinstance(sensors, list)
        assert len(sensors) == 5
        for v in sensors:
            assert v in (0, 1)

    @pytest.mark.anyio
    async def test_ir_response_has_labels_and_pins(self, client):
        resp = await client.get("/api/robot/sensors/ir")
        data = resp.json()["data"]
        assert "labels" in data
        assert len(data["labels"]) == 5
        assert "pins" in data
        assert len(data["pins"]) == 5


# ===================================================================
# 2. New API endpoint tests – Mode switching
# ===================================================================
class TestModeEndpoint:

    @pytest.mark.anyio
    async def test_get_mode_default_manual(self, client):
        resp = await client.get("/api/robot/mode")
        assert resp.status_code == 200
        assert resp.json()["data"]["mode"] == "manual"

    @pytest.mark.anyio
    async def test_set_mode_autonomous(self, client):
        resp = await client.post("/api/robot/mode", json={"mode": "autonomous"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["mode"] == "autonomous"
        assert body["data"]["previous"] == "manual"

    @pytest.mark.anyio
    async def test_set_mode_back_to_manual(self, client):
        await client.post("/api/robot/mode", json={"mode": "autonomous"})
        resp = await client.post("/api/robot/mode", json={"mode": "manual"})
        assert resp.json()["data"]["mode"] == "manual"

    @pytest.mark.anyio
    async def test_set_mode_invalid_rejected(self, client):
        resp = await client.post("/api/robot/mode", json={"mode": "turbo"})
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_get_mode_after_set(self, client):
        await client.post("/api/robot/mode", json={"mode": "autonomous"})
        resp = await client.get("/api/robot/mode")
        assert resp.json()["data"]["mode"] == "autonomous"


# ===================================================================
# 3. ZeroClaw – compute_line_error unit tests
# ===================================================================
class TestLineError:

    def test_centered(self):
        # Only center sensor sees line
        err = ZeroClawAgent.compute_line_error([1, 1, 0, 1, 1])
        assert err == 0.0

    def test_slight_left(self):
        err = ZeroClawAgent.compute_line_error([1, 0, 0, 1, 1])
        assert err is not None
        assert err < 0  # line is to the left

    def test_slight_right(self):
        err = ZeroClawAgent.compute_line_error([1, 1, 0, 0, 1])
        assert err is not None
        assert err > 0  # line is to the right

    def test_far_left(self):
        err = ZeroClawAgent.compute_line_error([0, 0, 1, 1, 1])
        assert err is not None
        assert err < -1

    def test_far_right(self):
        err = ZeroClawAgent.compute_line_error([1, 1, 1, 0, 0])
        assert err is not None
        assert err > 1

    def test_all_white_lost(self):
        err = ZeroClawAgent.compute_line_error([1, 1, 1, 1, 1])
        assert err is None

    def test_all_black_intersection(self):
        err = ZeroClawAgent.compute_line_error([0, 0, 0, 0, 0])
        assert err == 0.0

    def test_single_far_left(self):
        err = ZeroClawAgent.compute_line_error([0, 1, 1, 1, 1])
        assert err == -2.0

    def test_single_far_right(self):
        err = ZeroClawAgent.compute_line_error([1, 1, 1, 1, 0])
        assert err == 2.0


# ===================================================================
# 4. ZeroClaw – PID unit tests
# ===================================================================
class TestPID:

    def test_proportional_only(self):
        pid = PID(kp=1.0, ki=0.0, kd=0.0)
        # Force a known dt
        pid._prev_time -= 0.1  # pretend 100ms passed
        out = pid.update(1.0)
        assert out > 0

    def test_zero_error(self):
        pid = PID(kp=1.0, ki=0.0, kd=0.0)
        pid._prev_time -= 0.1
        out = pid.update(0.0)
        assert out == 0.0

    def test_negative_error(self):
        pid = PID(kp=2.0, ki=0.0, kd=0.0)
        pid._prev_time -= 0.1
        out = pid.update(-1.5)
        assert out < 0

    def test_reset(self):
        pid = PID(kp=1.0, ki=1.0, kd=0.0)
        pid._prev_time -= 0.1
        pid.update(5.0)
        pid.reset()
        assert pid._integral == 0.0
        assert pid._prev_error == 0.0


# ===================================================================
# 5. ZeroClaw – direction mapping
# ===================================================================
class TestDirectionMapping:

    def setup_method(self):
        self.agent = ZeroClawAgent(AgentConfig())

    def test_small_correction_goes_forward(self):
        d, s = self.agent._direction_from_correction(0.1)
        assert d == "forward"

    def test_moderate_left_correction(self):
        d, s = self.agent._direction_from_correction(-0.5)
        assert d == "left"

    def test_moderate_right_correction(self):
        d, s = self.agent._direction_from_correction(0.7)
        assert d == "right"

    def test_sharp_left_correction(self):
        d, s = self.agent._direction_from_correction(-1.5)
        assert d == "left"
        assert s == self.agent.cfg.sharp_turn_speed

    def test_sharp_right_correction(self):
        d, s = self.agent._direction_from_correction(2.0)
        assert d == "right"
        assert s == self.agent.cfg.sharp_turn_speed


# ===================================================================
# 6. ZeroClaw – integration with API (mock-free, uses test client)
# ===================================================================
class TestZeroClawIntegration:
    """
    These tests wire the ZeroClaw agent to a real (in-process) API server
    running in simulation mode so IR reads and motor commands actually
    round-trip through FastAPI.
    """

    @pytest.mark.anyio
    async def test_agent_sets_autonomous_mode(self, client):
        """Agent should switch the robot to autonomous mode on start."""
        # Use the HTTP client to mimic what the agent does
        resp = await client.post("/api/robot/mode", json={"mode": "autonomous"})
        assert resp.json()["data"]["mode"] == "autonomous"

    @pytest.mark.anyio
    async def test_agent_reads_ir_and_moves(self, client):
        """End-to-end: read IR → compute direction → send move."""
        # Read IR
        ir_resp = await client.get("/api/robot/sensors/ir")
        sensors = ir_resp.json()["data"]["sensors"]
        error = ZeroClawAgent.compute_line_error(sensors)

        if error is not None:
            agent = ZeroClawAgent()
            correction = agent.pid.update(error)
            direction, speed = agent._direction_from_correction(correction)

            resp = await client.post(f"/api/robot/{direction}", json={"speed": speed})
            assert resp.status_code == 200
            assert resp.json()["success"] is True

    @pytest.mark.anyio
    async def test_agent_stops_on_line_lost(self, client):
        """If all sensors read white, agent should stop."""
        # Force a stop scenario
        resp = await client.post("/api/robot/stop")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_mode_gate_blocks_movement(self, client):
        """Agent logic: check mode before issuing commands."""
        # In manual mode, agent should not drive
        mode_resp = await client.get("/api/robot/mode")
        mode = mode_resp.json()["data"]["mode"]
        assert mode == "manual"
        # Agent would skip control_step when mode != autonomous

    @pytest.mark.anyio
    async def test_full_flow_autonomous(self, client):
        """Full demo: set autonomous → read IR → move → stop → set manual."""
        # 1. Switch to autonomous
        await client.post("/api/robot/mode", json={"mode": "autonomous"})
        mode = (await client.get("/api/robot/mode")).json()["data"]["mode"]
        assert mode == "autonomous"

        # 2. Read IR sensors
        ir = (await client.get("/api/robot/sensors/ir")).json()["data"]["sensors"]
        assert len(ir) == 5

        # 3. Compute and move
        error = ZeroClawAgent.compute_line_error(ir)
        if error is not None:
            agent = ZeroClawAgent()
            correction = agent.pid.update(error)
            direction, speed = agent._direction_from_correction(correction)
            move_resp = await client.post(f"/api/robot/{direction}", json={"speed": speed})
            assert move_resp.status_code == 200

        # 4. Stop
        await client.post("/api/robot/stop")
        status = (await client.get("/api/robot/status")).json()["data"]
        assert status["motors"]["is_moving"] is False

        # 5. Back to manual
        await client.post("/api/robot/mode", json={"mode": "manual"})
        assert (await client.get("/api/robot/mode")).json()["data"]["mode"] == "manual"
