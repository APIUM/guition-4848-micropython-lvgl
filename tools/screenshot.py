#!/usr/bin/env python3
"""Capture a screenshot from the Guition 4848 display via serial.

Connects to the ESP32 over serial using the raw REPL protocol (no
soft-reset), reads the DMA framebuffer (RGB565), and saves as PNG.

Usage:
    python3 tools/screenshot.py [output.png]
    PORT=/dev/ttyUSB0 python3 tools/screenshot.py

Requirements:
    pip install pyserial Pillow
"""

import os
import struct
import sys
import time

import serial

W, H = 480, 480
EXPECTED_SIZE = W * H * 2  # RGB565 = 460800 bytes
OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "screenshot.png"
PORT = os.environ.get("PORT", "/dev/ttyUSB0")
BAUD = 115200

# MicroPython snippet executed via raw REPL.
# Reads the live DMA framebuffer and writes it as binary with a magic header.
MP_SCRIPT = """\
import sys, board_guition_4848 as _b
fb = _b.display_dev.framebuffer(0)
sys.stdout.buffer.write(b'\\x89SCR\\r\\n')
mv = memoryview(fb)
i = 0
while i < len(mv):
    sys.stdout.buffer.write(mv[i:i+4096])
    i += 4096
sys.stdout.buffer.write(b'\\x89END\\r\\n')
"""

MAGIC_START = b"\x89SCR\r\n"
MAGIC_END = b"\x89END\r\n"


def enter_raw_repl(ser):
    """Enter MicroPython raw REPL mode (Ctrl-A). No soft-reset."""
    # Interrupt any running program
    ser.write(b"\r\x03\x03")
    time.sleep(0.2)
    ser.read(ser.in_waiting)  # drain

    # Enter raw REPL
    ser.write(b"\x01")  # Ctrl-A
    time.sleep(0.2)
    data = ser.read(ser.in_waiting)
    if b"raw REPL" not in data:
        # Try once more
        ser.write(b"\r\x03\x03")
        time.sleep(0.3)
        ser.read(ser.in_waiting)
        ser.write(b"\x01")
        time.sleep(0.2)
        data = ser.read(ser.in_waiting)
        if b"raw REPL" not in data:
            print(f"Warning: could not confirm raw REPL entry. Got: {data!r}")


def exec_raw(ser, code, timeout=120):
    """Execute code in raw REPL and return stdout bytes."""
    # Send code
    ser.write(code.encode())
    # Ctrl-D to execute
    ser.write(b"\x04")

    # Raw REPL response: "OK" then stdout until \x04, then stderr until \x04
    # Wait for "OK"
    buf = b""
    deadline = time.time() + 5
    while time.time() < deadline:
        buf += ser.read(max(1, ser.in_waiting))
        if b"OK" in buf:
            break
    else:
        print(f"Timed out waiting for OK. Got: {buf!r}")
        sys.exit(1)

    # Read stdout until first \x04
    stdout = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        chunk = ser.read(max(1, ser.in_waiting))
        if not chunk:
            continue
        stdout += chunk
        if b"\x04" in stdout:
            stdout, rest = stdout.split(b"\x04", 1)
            break
    else:
        print(f"Timed out reading stdout ({len(stdout)} bytes so far)")
        sys.exit(1)

    # Read stderr until second \x04
    stderr = rest
    deadline = time.time() + 2
    while time.time() < deadline:
        chunk = ser.read(max(1, ser.in_waiting))
        if not chunk:
            continue
        stderr += chunk
        if b"\x04" in stderr:
            stderr = stderr.split(b"\x04", 1)[0]
            break

    if stderr:
        print(f"Device stderr: {stderr.decode(errors='replace')}")

    return stdout


def exit_raw_repl(ser):
    """Exit raw REPL back to normal REPL (Ctrl-B)."""
    ser.write(b"\x02")  # Ctrl-B
    time.sleep(0.1)


def rgb565_to_png(fb_data, path):
    """Convert RGB565 framebuffer to PNG."""
    if len(fb_data) < EXPECTED_SIZE:
        print(f"WARNING: short read ({len(fb_data)}/{EXPECTED_SIZE}), padding")
        fb_data = fb_data.ljust(EXPECTED_SIZE, b"\x00")
    elif len(fb_data) > EXPECTED_SIZE:
        fb_data = fb_data[:EXPECTED_SIZE]

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
    img.save(path)


def main():
    print(f"Connecting to {PORT} at {BAUD} baud...")
    ser = serial.Serial(PORT, BAUD, timeout=1)
    try:
        enter_raw_repl(ser)
        print("Capturing framebuffer...")
        raw = exec_raw(ser, MP_SCRIPT)
        exit_raw_repl(ser)
    finally:
        ser.close()

    idx = raw.find(MAGIC_START)
    if idx < 0:
        text = raw.decode(errors="replace")
        print(f"No screenshot data received. Output:\n{text[:1000]}")
        sys.exit(1)

    fb_data = raw[idx + len(MAGIC_START) :]
    end_idx = fb_data.find(MAGIC_END)
    if end_idx >= 0:
        fb_data = fb_data[:end_idx]

    print(f"Received {len(fb_data)} bytes (expected {EXPECTED_SIZE})")
    rgb565_to_png(fb_data, OUTPUT)
    print(f"Saved to {OUTPUT}")


if __name__ == "__main__":
    main()
