
# Ouster OS1-32 Real-Time Object Detection
# Sensor: os-122208000733.local
# IP: 169.254.231.104

import json
import re
import time
import numpy as np
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from ouster.sdk import sensor, core


SENSOR_IP = "169.254.231.104"

# Detection settings (millimeters)
MIN_DISTANCE = 500
MAX_DISTANCE = 1000
MIN_POINTS = 5

print("Connecting to Ouster LiDAR...")

# Check sensor firmware
firmware_url = f"http://{SENSOR_IP}/api/v1/system/firmware"

try:
    with build_opener(ProxyHandler({})).open(
        firmware_url, timeout=5
    ) as response:
        firmware = json.load(response)

except (URLError, TimeoutError, OSError, ValueError) as exc:
    raise SystemExit(
        f"Cannot read sensor firmware: {exc}"
    ) from exc

version = re.search(
    r"(?:^|-)v?(\d+)\.(\d+)\.(\d+)",
    firmware.get("semver") or firmware.get("fw", "")
)

if version and tuple(map(int, version.groups())) < (2, 4, 0):
    raise SystemExit(
        "Sensor firmware is unsupported. "
        "Firmware 2.4 or newer is required."
    )

# Connect to sensor
source = sensor.SensorFrameSetSource(SENSOR_IP)

print("Connected!")
print("Real-Time Object Detection Started")
print("Move your hand in front of the LiDAR.")
print("Press Ctrl+C to stop.\n")

frame_count = 0
start_time = time.monotonic()

try:
    for frames in source:
        frame = frames[0]

        if frame is None:
            continue

        frame_count += 1

        # Read LiDAR distance measurements
        distances = frame.field(core.ChanField.RANGE)

        # Vectorized NumPy filtering (much faster)
        nearby = (
            (distances >= MIN_DISTANCE) &
            (distances <= MAX_DISTANCE)
        )

        nearby_count = np.count_nonzero(nearby)

        # Calculate average processing FPS
        elapsed = time.monotonic() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0

        if nearby_count >= MIN_POINTS:
            closest = np.min(distances[nearby])
            distance_cm = closest / 10.0

            status = (
                f"OBJECT DETECTED! | "
                f"Distance: {distance_cm:.1f} cm | "
                f"Points: {nearby_count} | "
                f"FPS: {fps:.1f}"
            )

        else:
            status = (
                f"CLEAR            | "
                f"Points: {nearby_count} | "
                f"FPS: {fps:.1f}"
            )

        # Continuously overwrite the terminal line
        print(f"\r{status:<100}", end="", flush=True)

except KeyboardInterrupt:
    print("\n\nDetection stopped.")

finally:
    source.close()
