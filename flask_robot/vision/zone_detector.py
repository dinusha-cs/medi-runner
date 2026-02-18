"""
Zone Detector – colour-based region classification using OpenCV.

Given a camera frame, this module detects coloured zones
(red, green, blue, yellow by default) via HSV thresholding,
contour analysis, and area filtering.

The detected zones (with bounding boxes and confidence) are
returned as a list of dicts suitable for JSON serialisation.

This acts as a lightweight "AI" vision pipeline that can be
extended with ML models later.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    logger.warning("OpenCV not available – zone detection disabled")


class ZoneDetector:
    """
    Detects predefined colour zones in camera frames.

    Usage::

        detector = ZoneDetector(zone_colours, min_area=3000)
        detections = detector.detect(bgr_frame)
        # [{"zone": "red", "area": 12345, "bbox": [x,y,w,h], "center": [cx,cy], "confidence": 0.87}, ...]
    """

    def __init__(
        self,
        zone_colours: Dict[str, dict],
        min_area: int = 3000,
    ):
        """
        Parameters
        ----------
        zone_colours : dict
            Mapping zone_name → HSV range dict.  Supports single
            ``lower``/``upper`` or dual ranges (``lower1``/``upper1``,
            ``lower2``/``upper2``) for colours that wrap in HSV (red).
        min_area : int
            Minimum contour area in pixels² to be considered valid.
        """
        self._colours = zone_colours
        self._min_area = min_area
        self._last_detections: List[dict] = []
        self._detection_count: int = 0
        logger.info(
            "ZoneDetector created (zones=%s, min_area=%d)",
            list(zone_colours.keys()),
            min_area,
        )

    def detect(self, frame: np.ndarray) -> List[dict]:
        """
        Analyse *frame* (BGR numpy array) and return detected zones.

        Returns
        -------
        list of dict
            Each dict: ``zone``, ``area``, ``bbox`` [x,y,w,h],
            ``center`` [cx,cy], ``confidence``.
        """
        if not HAS_CV2 or frame is None:
            return []

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Light Gaussian blur to reduce noise
        hsv = cv2.GaussianBlur(hsv, (5, 5), 0)

        detections: List[dict] = []

        for zone_name, ranges in self._colours.items():
            mask = self._build_mask(hsv, ranges)
            zone_dets = self._find_zones(mask, zone_name, frame.shape)
            detections.extend(zone_dets)

        self._last_detections = detections
        self._detection_count += 1

        if detections:
            logger.debug(
                "Detected %d zone(s): %s",
                len(detections),
                [d["zone"] for d in detections],
            )

        return detections

    # ── mask building ────────────────────────────────────────────────────

    @staticmethod
    def _build_mask(hsv: np.ndarray, ranges: dict) -> np.ndarray:
        """
        Create a binary mask for a colour range.

        Supports single-range colours (green, blue, yellow) and
        dual-range colours (red wraps around 0/180 in HSV).
        """
        if "lower1" in ranges:
            # Dual-range (e.g. red)
            mask1 = cv2.inRange(
                hsv,
                np.array(ranges["lower1"], dtype=np.uint8),
                np.array(ranges["upper1"], dtype=np.uint8),
            )
            mask2 = cv2.inRange(
                hsv,
                np.array(ranges["lower2"], dtype=np.uint8),
                np.array(ranges["upper2"], dtype=np.uint8),
            )
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            # Single range
            mask = cv2.inRange(
                hsv,
                np.array(ranges["lower"], dtype=np.uint8),
                np.array(ranges["upper"], dtype=np.uint8),
            )

        # Morphological cleanup – remove small noise, fill small holes
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        return mask

    # ── contour analysis ─────────────────────────────────────────────────

    def _find_zones(
        self,
        mask: np.ndarray,
        zone_name: str,
        frame_shape: Tuple[int, ...],
    ) -> List[dict]:
        """Extract valid contours from *mask* and return detection dicts."""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        results: List[dict] = []
        frame_area = frame_shape[0] * frame_shape[1]

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self._min_area:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            cx, cy = x + w // 2, y + h // 2

            # Confidence heuristic: larger area relative to frame = higher
            # confidence; also penalise very elongated shapes.
            aspect = max(w, h) / (min(w, h) + 1e-6)
            size_score = min(area / frame_area * 10, 1.0)
            shape_score = max(0.0, 1.0 - (aspect - 1.0) * 0.15)
            confidence = round(min(size_score * shape_score, 1.0), 2)

            results.append({
                "zone": zone_name,
                "area": int(area),
                "bbox": [int(x), int(y), int(w), int(h)],
                "center": [int(cx), int(cy)],
                "confidence": confidence,
            })

        return results

    # ── annotated frame (for debug overlay) ──────────────────────────────

    def annotate_frame(self, frame: np.ndarray, detections: List[dict] = None) -> np.ndarray:
        """
        Draw bounding boxes and labels on *frame*.

        If *detections* is None the last cached detections are used.
        """
        if not HAS_CV2:
            return frame

        dets = detections if detections is not None else self._last_detections
        annotated = frame.copy()

        colour_map = {
            "red": (0, 0, 255),
            "green": (0, 255, 0),
            "blue": (255, 0, 0),
            "yellow": (0, 255, 255),
        }

        for d in dets:
            x, y, w, h = d["bbox"]
            colour = colour_map.get(d["zone"], (255, 255, 255))
            cv2.rectangle(annotated, (x, y), (x + w, y + h), colour, 2)

            label = f"{d['zone']} {d['confidence']:.0%}"
            cv2.putText(
                annotated, label, (x, y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2, cv2.LINE_AA,
            )

        return annotated

    # ── status ───────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "zones_configured": list(self._colours.keys()),
            "min_area": self._min_area,
            "detection_count": self._detection_count,
            "last_detections": self._last_detections,
            "opencv_available": HAS_CV2,
        }
