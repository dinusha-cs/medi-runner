 import cv2
from src.color_detect import detect_dominant_color

# Test all camera images
TEST_IMAGES = [
    "src/1.jpeg",
    "src/2.jpeg",
    "src/3.jpeg",
    "src/4.jpeg",
]

for path in TEST_IMAGES:
    img = cv2.imread(path)
    if img is None:
        print(f"[{path}] -- FILE NOT FOUND, skipping")
        continue

    color, conf, counts = detect_dominant_color(img)
    print(color)