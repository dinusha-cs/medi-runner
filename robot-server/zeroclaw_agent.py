#!/usr/bin/env python3
"""
ZeroClaw Agent – Autonomous Line-Following Controller
=====================================================

Reads the TCRT5000 5-channel IR array and Pi camera via the Robot
Controller REST API and issues movement commands to follow the black
line on the floor.  Only active when the robot is in **autonomous** mode.

Architecture
------------
    Controller Frontend  ──►  Robot Controller API  ◄──  ZeroClaw Agent
                                   (FastAPI)
    * Frontend handles manual control
    * ZeroClaw handles autonomous line-following

Hardware (all pins pre-wired – see docs/medi-runner-guide.md):
    IR Array  : GPIO 5, 6, 13, 19, 26  (S1-S5, 0 = black line)
    Motor L298N: ENA=20 IN1=23 IN2=22 IN3=27 IN4=17 ENB=16
    Buzzer    : GPIO 24
    Camera    : CSI ribbon → Pi Camera V1.3 5MP

Usage
-----
    # Start the Robot Controller API first
    python api_server.py

    # In a second terminal, start ZeroClaw
    python zeroclaw_agent.py                    # default http://localhost:8000
    python zeroclaw_agent.py --url http://PI:8000 --speed 55
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ZeroClaw")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass
class AgentConfig:
    """Tuneable parameters for the line-following agent."""

    api_url: str = "http://localhost:8000"
    base_speed: int = 50
    turn_speed: int = 40
    sharp_turn_speed: int = 30
    loop_interval: float = 0.05          # 20 Hz control loop
    lost_line_timeout: float = 2.0       # seconds before stop
    intersection_pause: float = 0.8      # pause at all-black intersection
    # PID gains
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0


# ---------------------------------------------------------------------------
# PID helper
# ---------------------------------------------------------------------------
class PID:
    """Minimal PID controller for line offset correction."""

    def __init__(self, kp: float, ki: float, kd: float):
        self.kp, self.ki, self.kd = kp, ki, kd
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = time.monotonic()

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = time.monotonic()

    def update(self, error: float) -> float:
        now = time.monotonic()
        dt = now - self._prev_time
        if dt <= 0:
            return 0.0
        self._integral += error * dt
        self._integral = max(-100, min(100, self._integral))
        derivative = (error - self._prev_error) / dt
        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        self._prev_error = error
        self._prev_time = now
        return max(-100, min(100, output))


# ---------------------------------------------------------------------------
# ZeroClaw Agent
# ---------------------------------------------------------------------------
class ZeroClawAgent:
    """
    Autonomous line-following agent.

    Reads IR sensors from the Robot Controller API, computes a steering
    correction, and posts movement commands back through the same API.
    """

    def __init__(self, config: AgentConfig | None = None):
        self.cfg = config or AgentConfig()
        self.client = httpx.AsyncClient(base_url=self.cfg.api_url, timeout=5.0)
        self.pid = PID(self.cfg.kp, self.cfg.ki, self.cfg.kd)
        self.running = False
        self._lost_since: Optional[float] = None

    # ---- API helpers (thin wrappers) ----

    async def _post(self, path: str, **kwargs) -> dict:
        resp = await self.client.post(path, json=kwargs if kwargs else None)
        resp.raise_for_status()
        return resp.json()

    async def _get(self, path: str) -> dict:
        resp = await self.client.get(path)
        resp.raise_for_status()
        return resp.json()

    async def api_forward(self, speed: int):
        return await self._post("/api/robot/forward", speed=speed)

    async def api_backward(self, speed: int):
        return await self._post("/api/robot/backward", speed=speed)

    async def api_left(self, speed: int):
        return await self._post("/api/robot/left", speed=speed)

    async def api_right(self, speed: int):
        return await self._post("/api/robot/right", speed=speed)

    async def api_stop(self):
        return await self._post("/api/robot/stop")

    async def api_buzzer(self, times: int = 1, duration: float = 0.3):
        return await self._post("/api/robot/buzzer", times=times, duration=duration)

    async def read_ir(self) -> list[int]:
        data = await self._get("/api/robot/sensors/ir")
        return data["data"]["sensors"]           # [S1..S5]

    async def get_mode(self) -> str:
        data = await self._get("/api/robot/mode")
        return data["data"]["mode"]

    async def set_mode(self, mode: str):
        return await self._post("/api/robot/mode", mode=mode)

    # ---- Line-following logic ----

    @staticmethod
    def compute_line_error(sensors: list[int]) -> Optional[float]:
        """
        Convert 5-channel IR reading into a line-position error.

        Sensors: [S1(far-left), S2(left), S3(center), S4(right), S5(far-right)]
        Convention: 0 = black line detected, 1 = white floor

        Returns a float in [-2, +2]  (negative = line is to the left)
        or None when the line is completely lost (all white).
        """
        s1, s2, s3, s4, s5 = sensors

        # All white → line lost
        if s1 == 1 and s2 == 1 and s3 == 1 and s4 == 1 and s5 == 1:
            return None

        # All black → intersection / cross-line
        if s1 == 0 and s2 == 0 and s3 == 0 and s4 == 0 and s5 == 0:
            return 0.0  # treat as centered; caller pauses if needed

        # Weighted average  (invert so 0→1 means "line present")
        weights = [-2, -1, 0, 1, 2]
        active = [1 - v for v in sensors]       # 1 where line is detected
        total = sum(active)
        if total == 0:
            return None
        return sum(w * a for w, a in zip(weights, active)) / total

    def _direction_from_correction(self, correction: float):
        """Map a PID correction value to an API movement call."""
        abs_c = abs(correction)
        if abs_c < 0.3:
            return "forward", self.cfg.base_speed
        elif abs_c < 1.0:
            d = "left" if correction < 0 else "right"
            return d, self.cfg.turn_speed
        else:
            d = "left" if correction < 0 else "right"
            return d, self.cfg.sharp_turn_speed

    # ---- Main control loop ----

    async def _control_step(self):
        """Single iteration of the line-following loop."""
        sensors = await self.read_ir()
        error = self.compute_line_error(sensors)

        if error is None:
            # Line lost
            if self._lost_since is None:
                self._lost_since = time.monotonic()
                logger.warning(f"Line lost  IR={sensors}")
            elapsed = time.monotonic() - self._lost_since
            if elapsed > self.cfg.lost_line_timeout:
                logger.warning("Line lost too long – stopping")
                await self.api_stop()
                return
            # Keep creeping forward slowly while searching
            await self.api_forward(max(self.cfg.sharp_turn_speed - 10, 10))
            return

        # Line found – reset lost timer
        self._lost_since = None

        # Intersection (all sensors black)
        s1, s2, s3, s4, s5 = sensors
        if s1 == 0 and s2 == 0 and s3 == 0 and s4 == 0 and s5 == 0:
            logger.info("Intersection detected – pausing")
            await self.api_stop()
            await asyncio.sleep(self.cfg.intersection_pause)

        # PID correction
        correction = self.pid.update(error)
        direction, speed = self._direction_from_correction(correction)

        logger.debug(
            f"IR={sensors}  err={error:+.2f}  pid={correction:+.2f}  "
            f"→ {direction} @ {speed}%"
        )

        if direction == "forward":
            await self.api_forward(speed)
        elif direction == "left":
            await self.api_left(speed)
        elif direction == "right":
            await self.api_right(speed)

    async def run(self):
        """
        Main entry point.  Switches robot to autonomous mode and starts
        the control loop.  Stops cleanly on SIGINT / SIGTERM.
        """
        self.running = True
        logger.info(f"ZeroClaw starting – API={self.cfg.api_url}")

        # Ensure the robot API is reachable
        try:
            health = await self._get("/health")
            logger.info(f"Robot API health: {health}")
        except Exception as e:
            logger.error(f"Cannot reach Robot API: {e}")
            return

        # Switch to autonomous mode
        await self.set_mode("autonomous")
        logger.info("Mode set to AUTONOMOUS")

        try:
            while self.running:
                # Re-check mode – if someone switches to manual, pause
                mode = await self.get_mode()
                if mode != "autonomous":
                    logger.info(f"Mode is '{mode}' – ZeroClaw pausing")
                    await self.api_stop()
                    await asyncio.sleep(0.5)
                    continue

                await self._control_step()
                await asyncio.sleep(self.cfg.loop_interval)

        except asyncio.CancelledError:
            logger.info("ZeroClaw cancelled")
        except Exception as e:
            logger.error(f"ZeroClaw error: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Graceful shutdown – stop motors and switch back to manual."""
        logger.info("ZeroClaw shutting down …")
        self.running = False
        try:
            await self.api_stop()
            await self.set_mode("manual")
            logger.info("Mode restored to MANUAL")
        except Exception:
            pass
        await self.client.aclose()
        logger.info("ZeroClaw stopped")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="ZeroClaw – autonomous line-following agent")
    parser.add_argument("--url", default="http://localhost:8000", help="Robot Controller API URL")
    parser.add_argument("--speed", type=int, default=50, help="Base speed (0-100)")
    parser.add_argument("--kp", type=float, default=1.0, help="PID Kp")
    parser.add_argument("--ki", type=float, default=0.0, help="PID Ki")
    parser.add_argument("--kd", type=float, default=0.0, help="PID Kd")
    args = parser.parse_args()

    cfg = AgentConfig(
        api_url=args.url,
        base_speed=args.speed,
        kp=args.kp,
        ki=args.ki,
        kd=args.kd,
    )
    agent = ZeroClawAgent(cfg)

    loop = asyncio.new_event_loop()

    def _signal(sig, frame):
        logger.info(f"Signal {sig} received")
        agent.running = False

    signal.signal(signal.SIGINT, _signal)
    signal.signal(signal.SIGTERM, _signal)

    try:
        loop.run_until_complete(agent.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
