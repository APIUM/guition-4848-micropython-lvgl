#!/usr/bin/env python3
"""Capture a screenshot from the Guition 4848 display via serial.

Connects to the ESP32 over serial using mpremote, reads the DMA
framebuffer (RGB565), and saves it as a PNG.

Usage:
    python3 tools/screenshot.py [output.png]
    PORT=/dev/ttyACM0 python3 tools/screenshot.py

Requirements:
    pip install mpremote Pillow
"""

import os
import struct
import subprocess
import sys
import tempfile

W, H = 480, 480
EXPECTED_SIZE = W * H * 2  # RGB565, 460800 bytes
OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/screenshot.png"
PORT = os.environ.get("PORT", "auto")

# MicroPython script to dump the framebuffer as raw bytes to stdout.
# Uses sys.stdout.buffer.write() to avoid any text encoding.
# Sends a magic header so we can find the start of binary data.
MP_SCRIPT = r"""
import sys
import board

if board.display_dev is None:
    print("ERROR: display not initialised")
    sys.exit(1)

fb = board.display_dev.framebuffer(0)
MAGIC = b'\x89SCR\r\n'
sys.stdout.buffer.write(MAGIC)

# Write in chunks to avoid memory issues
mv = memoryview(fb)
CHUNK = 4096
i = 0
while i < len(mv):
    end = min(i + CHUNK, len(mv))
    sys.stdout.buffer.write(mv[i:end])
    i = end
"""


def main():
    # Write the MP script to a temp file for mpremote exec
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(MP_SCRIPT)
        script_path = f.name

    try:
        port_args = ["connect", PORT] if PORT != "auto" else []
        cmd = ["mpremote", *port_args, "run", script_path]
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, timeout=30)
    finally:
        os.unlink(script_path)

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        print(f"mpremote failed (exit {result.returncode}):\n{stderr}")
        sys.exit(1)

    raw = result.stdout
    MAGIC = b"\x89SCR\r\n"
    idx = raw.find(MAGIC)
    if idx < 0:
        # Check for error message in output
        text = raw.decode(errors="replace")
        print(f"No screenshot data received. Output:\n{text[:500]}")
        sys.exit(1)

    fb_data = raw[idx + len(MAGIC):]
    print(f"Received {len(fb_data)} bytes (expected {EXPECTED_SIZE})")

    if len(fb_data) < EXPECTED_SIZE:
        print(f"WARNING: Short read ({len(fb_data)}/{EXPECTED_SIZE}), image may be truncated")
        fb_data = fb_data.ljust(EXPECTED_SIZE, b"\x00")
    elif len(fb_data) > EXPECTED_SIZE:
        fb_data = fb_data[:EXPECTED_SIZE]

    # Convert RGB565 to RGB888
    pixels = bytearray(W * H * 3)
    for i in range(0, EXPECTED_SIZE, 2):
        v = struct.unpack("<H", fb_data[i : i + 2])[0]
        r = ((v >> 11) & 0x1F) << 3
        g = ((v >> 5) & 0x3F) << 2
        b = (v & 0x1F) << 3
        j = (i // 2) * 3
        pixels[j] = r
        pixels[j + 1] = g
        pixels[j + 2] = b

    from PIL import Image

    img = Image.frombytes("RGB", (W, H), bytes(pixels))
    img.save(OUTPUT)
    print(f"Saved to {OUTPUT}")


if __name__ == "__main__":
    main()
