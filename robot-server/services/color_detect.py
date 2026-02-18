"""
Zone Color Detection Service
Detects dominant floor-zone colors from camera frames for the Medi-Runner
competition.  Zones are marked in four colours:

    Blue   → 1 beep
    Red    → 2 quick beeps
    Green  → 3 quick beeps
    Yellow → 4 quick beeps

Usage
-----
    from services.color_detect import detect_zone_color

    color, confidence, counts = detect_zone_color(bgr_frame)
    # color: "blue" | "red" | "green" | "yellow" | "unknown"
    # confidence: 0.0-1.0  (fraction of ROI pixels matching the dominant colour)
    # counts: dict of pixel counts per colour

The function analyses the bottom-centre region of the image (the floor
directly ahead) and compares HSV ranges for the four target colours.
"""

from __future__ import annotations

from typing import Tuple, Dict

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None  # type: ignore
    np = None   # type: ignore

# ---------------------------------------------------------------------------
# HSV colour ranges – calibrated for typical printed coloured tape / paper
# under indoor lighting.  Adjust as needed after real-world testing.
# ---------------------------------------------------------------------------
# Each entry: (lower_hsv, upper_hsv)
# OpenCV HSV ranges: H 0-179, S 0-255, V 0-255
COLOR_RANGES: Dict[str, list[Tuple]] = {
    "blue": [
        ((90, 80, 50), (130, 255, 255)),
    ],
    "red": [
        ((0, 80, 50), (10, 255, 255)),      # low-hue red
        ((160, 80, 50), (179, 255, 255)),    # high-hue red (wraps around)
    ],
    "green": [
        ((35, 60, 50), (85, 255, 255)),
    ],
    "yellow": [
        ((18, 80, 80), (35, 255, 255)),
    ],
}

# Fraction of the image height/width used as the detection ROI.
# Bottom-centre strip = floor right in front of the robot.
ROI_TOP_FRAC = 0.55      # start at 55 % down
ROI_BOTTOM_FRAC = 0.90   # end at 90 % down
ROI_LEFT_FRAC = 0.20     # 20 % from left
ROI_RIGHT_FRAC = 0.80    # 80 % from right

# Minimum fraction of ROI pixels that must match for a valid detection
MIN_CONFIDENCE = 0.08     # 8 % of ROI pixels


def detect_zone_color(
    bgr_frame,
    *,
    roi: Tuple[float, float, float, float] | None = None,
    min_confidence: float = MIN_CONFIDENCE,
) -> Tuple[str, float, Dict[str, int]]:
    """
    Detect the dominant zone colour in a BGR camera frame.

    Parameters
    ----------
    bgr_frame : numpy.ndarray
        BGR image (from OpenCV or picamera).
    roi : tuple, optional
        (top_frac, bottom_frac, left_frac, right_frac) override.
    min_confidence : float
        Minimum pixel fraction to accept a colour.

    Returns
    -------
    colour : str
        "blue", "red", "green", "yellow", or "unknown".
    confidence : float
        Fraction of ROI pixels matching the dominant colour (0–1).
    counts : dict
        Pixel counts for each colour in the ROI.
    """
    if cv2 is None or np is None:
        return "unknown", 0.0, {}

    h, w = bgr_frame.shape[:2]

    # Extract ROI
    t_frac, b_frac, l_frac, r_frac = roi or (
        ROI_TOP_FRAC, ROI_BOTTOM_FRAC, ROI_LEFT_FRAC, ROI_RIGHT_FRAC
    )
    y1, y2 = int(h * t_frac), int(h * b_frac)
    x1, x2 = int(w * l_frac), int(w * r_frac)
    roi_img = bgr_frame[y1:y2, x1:x2]

    # Convert to HSV
    hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
    roi_pixels = hsv.shape[0] * hsv.shape[1]

    counts: Dict[str, int] = {}
    for colour_name, ranges in COLOR_RANGES.items():
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for lower, upper in ranges:
            lower_np = np.array(lower, dtype=np.uint8)
            upper_np = np.array(upper, dtype=np.uint8)
            mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower_np, upper_np))
        counts[colour_name] = int(cv2.countNonZero(mask))

    if roi_pixels == 0:
        return "unknown", 0.0, counts

    # Determine dominant colour
    best_colour = max(counts, key=counts.get)  # type: ignore[arg-type]
    best_count = counts[best_colour]
    confidence = best_count / roi_pixels

    if confidence < min_confidence:
        return "unknown", confidence, counts

    return best_colour, confidence, counts


# ---------------------------------------------------------------------------
# Convenience wrapper matching the old ``detect_dominant_color`` signature
# that ``color-detect.py`` expects.
# ---------------------------------------------------------------------------
def detect_dominant_color(bgr_frame) -> Tuple[str, float, Dict[str, int]]:
    """Alias kept for backward-compat with ``color-detect.py`` test script."""
    return detect_zone_color(bgr_frame)


# ---------------------------------------------------------------------------
# Beep pattern mapping (used by ZeroClaw agent)
# ---------------------------------------------------------------------------
ZONE_BEEP_MAP: Dict[str, int] = {
    "blue": 1,
    "red": 2,
    "green": 3,
    "yellow": 4,
}


# ---------------------------------------------------------------------------
# Quick self-test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m services.color_detect <image_path> [image_path ...]")
        sys.exit(1)

    for path in sys.argv[1:]:
        img = cv2.imread(path)
        if img is None:
            print(f"[{path}] FILE NOT FOUND – skipping")
            continue
        colour, conf, cnts = detect_zone_color(img)
        print(f"[{path}] colour={colour}  confidence={conf:.2%}  counts={cnts}")
