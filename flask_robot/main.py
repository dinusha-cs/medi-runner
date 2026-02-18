#!/usr/bin/env python3
"""
Main entry point for the Line-Following Robot Flask Server.

Run::

    python main.py              # defaults: simulation mode, port 5000
    SIMULATION=0 python main.py # real hardware
    FLASK_PORT=8080 python main.py

Or directly::

    python app.py
"""

import sys
import os

# Ensure the package root is on sys.path so that relative imports work
# regardless of the working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, _cleanup, FLASK_HOST, FLASK_PORT, DEBUG, SIMULATION_MODE


def main():
    print("=" * 60)
    print("  Line-Following Robot Flask Server")
    print(f"  URL:  http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"  Mode: {'SIMULATION' if SIMULATION_MODE else 'HARDWARE'}")
    print(f"  Debug: {DEBUG}")
    print("=" * 60)
    print()
    print("Endpoints:")
    print("  GET  /api/status             – full robot status")
    print("  POST /api/mode               – switch manual/autonomous")
    print("  POST /api/move               – manual movement")
    print("  POST /api/emergency-stop     – emergency stop")
    print("  POST /api/line-follow/start  – start line following")
    print("  GET  /api/camera/stream      – MJPEG video")
    print("  GET  /api/zones/detect       – colour zone detection")
    print("  GET  /api/logs               – activity logs")
    print("  GET  /api/errors             – error records")
    print()

    try:
        app.run(
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug=DEBUG,
            threaded=True,
            use_reloader=False,
        )
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        _cleanup()
        print("Goodbye.")


if __name__ == "__main__":
    main()
