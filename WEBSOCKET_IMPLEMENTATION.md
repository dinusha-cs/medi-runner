# WebSocket Implementation — Status

## Current Architecture

The Medi Runner system uses a **REST-only** architecture. All communication with the robot goes through the **Robot Controller API** (FastAPI on port 8000).

The previous Node.js WebSocket backend (`controller-backend/`) has been **removed**. All functionality is now handled by the Python FastAPI server.

## Communication Flow

```
Any HTTP Client  ──── HTTP REST ────►  Robot Controller API (FastAPI :8000)
ZeroClaw Agent   ──── HTTP REST ────►  Robot Controller API (FastAPI :8000)
```

## Available Endpoints

See [docs/api-reference.md](docs/api-reference.md) for the full REST API reference.

## Camera Streaming

Live video is served as MJPEG over HTTP — no WebSocket required:

```
GET /api/robot/camera/stream    → multipart/x-mixed-replace (MJPEG)
GET /api/robot/camera/snapshot  → image/jpeg (single frame)
```

## Future WebSocket Support

If real-time push notifications are needed (e.g. sensor telemetry streaming), FastAPI natively supports WebSocket endpoints. This can be added to `api_server.py` without any additional framework.
