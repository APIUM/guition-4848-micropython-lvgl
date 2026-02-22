#!/usr/bin/env bash
#
# Flash MicroPython + LVGL demo firmware to Guition ESP32-S3-4848S040.
#
# Prerequisites (install once):
#   pip install esptool mpremote
#
# Usage:
#   ./flash.sh                  # full flash (erase + flash + upload app)
#   ./flash.sh --app-only       # re-upload .py files only (fast iteration)
#
# The script auto-detects the serial port. Override with:
#   PORT=/dev/ttyUSB0 ./flash.sh
#
set -euo pipefail
cd "$(dirname "$0")"

# ─── Config ───────────────────────────────────────────────────────────────────

CHIP="esp32s3"
FIRMWARE_FILE="firmware_guition_4848.bin"
BAUD=460800

# ─── Helpers ──────────────────────────────────────────────────────────────────

red()   { printf '\033[0;31m%s\033[0m\n' "$*"; }
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
blue()  { printf '\033[0;34m%s\033[0m\n' "$*"; }

die() { red "Error: $*" >&2; exit 1; }

check_tool() {
  command -v "$1" >/dev/null 2>&1 || die "$1 not found. Install with: pip install $1"
}

# ─── Port detection ──────────────────────────────────────────────────────────

detect_port() {
  if [[ -n "${PORT:-}" ]]; then
    echo "$PORT"
    return
  fi

  local candidates=()

  # Linux
  for p in /dev/ttyUSB* /dev/ttyACM*; do
    [[ -e "$p" ]] && candidates+=("$p")
  done

  # macOS
  for p in /dev/cu.usbserial-* /dev/cu.SLAB_USBtoUART* /dev/cu.wchusbserial*; do
    [[ -e "$p" ]] && candidates+=("$p")
  done

  if [[ ${#candidates[@]} -eq 0 ]]; then
    die "No serial port found. Is the board plugged in? Set PORT= manually."
  fi

  if [[ ${#candidates[@]} -gt 1 ]]; then
    blue "Multiple serial ports found:" >&2
    for p in "${candidates[@]}"; do echo "  $p" >&2; done
    blue "Using first: ${candidates[0]}  (override with PORT=...)" >&2
  fi

  echo "${candidates[0]}"
}

# ─── Steps ───────────────────────────────────────────────────────────────────

erase_and_flash() {
  local port="$1"

  if [[ ! -f "$FIRMWARE_FILE" ]]; then
    die "Firmware not found: ${FIRMWARE_FILE}\nBuild it first: cd ../drivers && ./build.sh"
  fi

  blue "Erasing flash..."
  esptool.py --chip "$CHIP" --port "$port" erase_flash

  blue "Flashing firmware (${CHIP})..."
  esptool.py --chip "$CHIP" --port "$port" --baud "$BAUD" write_flash -z 0x0 "$FIRMWARE_FILE"
  green "Firmware flashed successfully"

  blue "Waiting for device to reboot..."
  sleep 3
}

upload_app() {
  local port="$1"

  blue "Uploading application files..."
  mpremote connect "$port" cp boot.py :boot.py
  mpremote connect "$port" cp board.py :board.py
  mpremote connect "$port" cp board_guition_4848.py :board_guition_4848.py
  mpremote connect "$port" cp main.py :main.py
  green "Application uploaded"
}

reset_device() {
  local port="$1"
  blue "Resetting device..."
  mpremote connect "$port" reset
  green "Done! The LVGL widget demo should now be running on the display."
}

# ─── Main ─────────────────────────────────────────────────────────────────────

main() {
  local mode="${1:-full}"

  check_tool esptool.py
  check_tool mpremote

  local port
  port=$(detect_port)
  blue "Using port: $port"

  case "$mode" in
    --app-only)
      upload_app "$port"
      reset_device "$port"
      ;;
    full|*)
      erase_and_flash "$port"
      upload_app "$port"
      reset_device "$port"
      ;;
  esac

  echo ""
  green "═══════════════════════════════════════════════════"
  green "  Guition 4848 LVGL demo flashed successfully!"
  green "═══════════════════════════════════════════════════"
  echo ""
  echo "  Monitor serial output:  mpremote connect $port repl"
  echo ""
}

main "$@"
