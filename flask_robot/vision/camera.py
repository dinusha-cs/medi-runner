"""
Camera – capture frames and stream MJPEG over HTTP.

Supports:
* Real Pi Camera via ``picamera2`` (Raspberry Pi OS Bookworm+).
* OpenCV ``cv2.VideoCapture`` fallback for USB cameras.
* A synthetic test-pattern generator for **simulation mode**.

The :meth:`get_frame` method always returns a JPEG-encoded ``bytes``
object ready to be yielded in an MJPEG response.
"""

import logging
import threading
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Try importing camera back-ends; will be None if unavailable.
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    logger.warning("OpenCV (cv2) not installed – camera features limited")

try:
    from picamera2 import Picamera2
    HAS_PICAMERA = True
except ImportError:
    HAS_PICAMERA = False


class Camera:
    """
    Unified camera interface.

    Priority order:
        1. picamera2  (Pi Camera)
        2. cv2.VideoCapture(0)  (USB webcam)
        3. Simulation  (synthetic frames)
    """

    def __init__(self, config: dict, simulation: bool = False):
        """
        Parameters
        ----------
        config : dict
            Camera configuration from ``config.CAMERA``.
        simulation : bool
            Force simulation mode even if hardware is available.
        """
        self._cfg = config
        self._simulation = simulation
        self._width = config["WIDTH"]
        self._height = config["HEIGHT"]
        self._fps = config["FPS"]
        self._jpeg_quality = config["JPEG_QUALITY"]

        self._cap = None          # cv2.VideoCapture or Picamera2 handle
        self._lock = threading.Lock()
        self._frame: Optional[bytes] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_count: int = 0

        logger.info(
            "Camera created (%dx%d @%d fps, sim=%s)",
            self._width, self._height, self._fps, simulation,
        )

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Open the camera and begin capturing in a background thread."""
        if self._running:
            return

        if not self._simulation and HAS_PICAMERA:
            self._start_picamera()
        elif not self._simulation and HAS_CV2:
            self._start_opencv()
        else:
            logger.info("Camera running in SIMULATION mode")

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="camera")
        self._thread.start()
        logger.info("Camera capture thread started")

    def stop(self) -> None:
        """Release camera resources."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        if self._cap is not None:
            try:
                if HAS_PICAMERA and isinstance(self._cap, Picamera2):
                    self._cap.stop()
                elif HAS_CV2:
                    self._cap.release()
            except Exception:
                pass
            self._cap = None

        logger.info("Camera stopped (frames captured: %d)", self._frame_count)

    # ── frame access ─────────────────────────────────────────────────────

    def get_frame(self) -> Optional[bytes]:
        """Return the latest JPEG-encoded frame, or None."""
        with self._lock:
            return self._frame

    def generate_mjpeg(self):
        """
        Generator that yields MJPEG multipart chunks.

        Usage in Flask::

            return Response(camera.generate_mjpeg(),
                            mimetype='multipart/x-mixed-replace; boundary=frame')
        """
        while self._running:
            frame = self.get_frame()
            if frame is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            time.sleep(1.0 / self._fps)

    # ── raw numpy frame (for zone detector) ──────────────────────────────

    def get_raw_frame(self) -> Optional[np.ndarray]:
        """Return the latest frame as a BGR numpy array (or None)."""
        jpeg = self.get_frame()
        if jpeg is None or not HAS_CV2:
            return None
        arr = np.frombuffer(jpeg, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)

    # ── back-end initialisers ────────────────────────────────────────────

    def _start_picamera(self) -> None:
        logger.info("Opening Pi Camera via picamera2")
        cam = Picamera2()
        cam_config = cam.create_preview_configuration(
            main={"size": (self._width, self._height), "format": "RGB888"}
        )
        cam.configure(cam_config)
        cam.start()
        time.sleep(self._cfg.get("WARMUP_TIME", 1.0))
        self._cap = cam

    def _start_opencv(self) -> None:
        logger.info("Opening camera via OpenCV VideoCapture(0)")
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        cap.set(cv2.CAP_PROP_FPS, self._fps)
        if not cap.isOpened():
            raise RuntimeError("Failed to open camera with OpenCV")
        self._cap = cap

    # ── capture loop ─────────────────────────────────────────────────────

    def _capture_loop(self) -> None:
        """Continuously grab frames and JPEG-encode them."""
        interval = 1.0 / self._fps
        while self._running:
            try:
                if self._simulation:
                    raw = self._generate_test_frame()
                elif HAS_PICAMERA and isinstance(self._cap, Picamera2):
                    raw = self._cap.capture_array()
                elif HAS_CV2 and self._cap is not None:
                    ret, raw = self._cap.read()
                    if not ret:
                        time.sleep(interval)
                        continue
                else:
                    raw = self._generate_test_frame()

                # JPEG encode
                if HAS_CV2:
                    _, buf = cv2.imencode(
                        ".jpg", raw, [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality]
                    )
                    jpeg = buf.tobytes()
                else:
                    # Minimal fallback: create a tiny JPEG-like placeholder
                    jpeg = self._minimal_jpeg_placeholder()

                with self._lock:
                    self._frame = jpeg
                self._frame_count += 1

            except Exception as exc:
                logger.error("Camera capture error: %s", exc)

            time.sleep(interval)

    # ── simulation helpers ───────────────────────────────────────────────

    def _generate_test_frame(self) -> np.ndarray:
        """Create a synthetic BGR frame with a moving coloured bar."""
        frame = np.zeros((self._height, self._width, 3), dtype=np.uint8)
        # Dark grey background
        frame[:] = (40, 40, 40)

        # Animated vertical bar
        offset = (self._frame_count * 3) % self._width
        bar_w = 60
        x1 = offset
        x2 = min(offset + bar_w, self._width)
        frame[:, x1:x2] = (0, 200, 0)  # green bar

        # Timestamp overlay (if cv2 available)
        if HAS_CV2:
            text = f"SIM {time.strftime('%H:%M:%S')}  frame={self._frame_count}"
            cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (255, 255, 255), 1, cv2.LINE_AA)

        return frame

    @staticmethod
    def _minimal_jpeg_placeholder() -> bytes:
        """Return a 1x1-pixel valid JPEG (used when cv2 is missing)."""
        # Smallest valid JPEG: a 1x1 white pixel
        return (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01"
            b"\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06"
            b"\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b"
            b"\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c"
            b"\x1c $.\' ',#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0"
            b"\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4"
            b"\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06"
            b"\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03"
            b"\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02"
            b"\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81"
            b"\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16"
            b"\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghij"
            b"stuvwxyz\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd2"
            b"\x8a(\x03\xff\xd9"
        )

    # ── status ───────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "simulation": self._simulation,
            "resolution": f"{self._width}x{self._height}",
            "fps": self._fps,
            "frames_captured": self._frame_count,
        }
