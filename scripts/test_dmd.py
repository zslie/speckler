#!/usr/bin/env python3
"""DMD Mirror State & Optical Verification Tool.

Controls the DMD projector display to toggle all micromirrors ON (full white)
and OFF (full black), with optional camera feedback to measure optical contrast.

Usage:
    # Interactive toggle window on the DMD display:
    uv run python scripts/test_dmd.py

    # Automated toggle test with live CMOS camera measurement:
    uv run python scripts/test_dmd.py --auto

    # Specify monitor index explicitly (default auto-detects secondary display):
    uv run python scripts/test_dmd.py --monitor 1

Interactive Keybindings:
    Spacebar : Toggle between ALL ON and ALL OFF
    1 / w    : Set ALL ON (white, 255)
    0 / b    : Set ALL OFF (black, 0)
    c        : Display checkerboard pattern (for optical focus & alignment)
    a        : Run automated ON/OFF verification cycle with camera readback
    q / ESC  : Quit and close window
"""

import argparse
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from screeninfo import get_monitors

logger = logging.getLogger("test_dmd")


def get_display_info(
    preferred_index: int | None = None,
    wait_for_connection: bool = True,
) -> tuple[int, int, int, int] | None:
    """Finds target display parameters (x_offset, y_offset, width, height)."""
    monitors = get_monitors()

    if preferred_index is not None and preferred_index < len(monitors):
        target = monitors[preferred_index]
        print(f"[✓] Selected specified monitor {preferred_index}: {target.width}x{target.height}")
        return target.x, target.y, target.width, target.height

    if len(monitors) > 1:
        target = monitors[1]
        print(f"[✓] Auto-detected external DMD display at index 1: {target.width}x{target.height}")
        return target.x, target.y, target.width, target.height

    if not wait_for_connection:
        print("[!] External HDMI display not detected.")
        return None

    print("\n[i] Waiting for DMD HDMI display to connect (bridge KEY to GND)...")
    print("    (Press Ctrl+C to cancel)\n")
    try:
        while True:
            time.sleep(0.5)
            monitors = get_monitors()
            if len(monitors) > 1:
                target = monitors[1]
                print(f"\n[✓] DMD DISPLAY DETECTED! Monitor 1: {target.width}x{target.height} at ({target.x}, {target.y})")
                print("    Launching video stream to DMD immediately...\n")
                return target.x, target.y, target.width, target.height
    except KeyboardInterrupt:
        print("\nDisplay detection cancelled by user.")
        return None


def create_patterns(width: int, height: int) -> dict[str, np.ndarray]:
    """Generates ALL_ON, ALL_OFF, and Checkerboard patterns."""
    all_on = np.full((height, width), 255, dtype=np.uint8)
    all_off = np.zeros((height, width), dtype=np.uint8)

    # 16x16 checkerboard
    cb_grid = np.indices((16, 16)).sum(axis=0) % 2 * 255
    checkerboard = cv2.resize(
        cb_grid.astype(np.uint8),
        (width, height),
        interpolation=cv2.INTER_NEAREST,
    )

    return {
        "ALL_ON": all_on,
        "ALL_OFF": all_off,
        "CHECKERBOARD": checkerboard,
    }


def grab_camera_stats(
    cap: cv2.VideoCapture | None,
) -> tuple[float, float, float] | None:
    """Reads a fresh frame from the camera and returns (mean, min, max) intensity."""
    if cap is None or not cap.isOpened():
        return None
    # Flush buffer
    frame = None
    for _ in range(4):
        ret, frame = cap.read()
        if not ret:
            return None
    if frame is None:
        return None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    return float(gray.mean()), float(gray.min()), float(gray.max())


def run_interactive(
    x_offset: int,
    y_offset: int,
    width: int,
    height: int,
    fullscreen: bool = True,
    use_camera: bool = True,
) -> None:
    """Runs interactive DMD toggle test."""
    patterns = create_patterns(width, height)
    current_state = "ALL_ON"

    window_name = "DMD_Controller_Test"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.moveWindow(window_name, x_offset, y_offset)

    if fullscreen:
        cv2.setWindowProperty(
            window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )
    else:
        cv2.resizeWindow(window_name, width, height)

    # Optional camera check
    cam = None
    if use_camera:
        try:
            cam = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
            if not cam.isOpened():
                cam = None
            else:
                cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1600)
                cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1200)
                print("[✓] CMOS camera (Arducam) linked for live reflection feedback.")
        except (ImportError, RuntimeError, OSError, cv2.error) as e:
            logger.debug("Failed opening camera: %s", e)
            cam = None

    print("\n" + "=" * 55)
    print(" DMD TOGGLE TEST CONTROLS")
    print("=" * 55)
    print("  SPACEBAR : Toggle between ALL ON and ALL OFF")
    print("  '1' / 'w': Set ALL ON  (full white, 255)")
    print("  '0' / 'b': Set ALL OFF (full black, 0)")
    print("  'c'      : Display Checkerboard (focus check)")
    print("  'a'      : Run automated ON/OFF verification")
    print("  'q' / ESC: Quit test")
    print("=" * 55)

    def display_state(state_name: str) -> None:
        cv2.imshow(window_name, patterns[state_name])
        cv2.waitKey(1)
        time.sleep(0.08)
        cam_info = ""
        if cam is not None:
            stats = grab_camera_stats(cam)
            if stats:
                cam_info = f" | CMOS Mean: {stats[0]:.1f} DN (Min={stats[1]:.0f}, Max={stats[2]:.0f})"
        print(f" -> DMD State: [{state_name}]{cam_info}")

    display_state(current_state)

    try:
        while True:
            key = cv2.waitKey(0) & 0xFF

            if key in (ord("q"), 27):  # 'q' or ESC
                break
            elif key in (ord(" "),):  # Toggle
                current_state = "ALL_OFF" if current_state == "ALL_ON" else "ALL_ON"
                display_state(current_state)
            elif key in (ord("1"), ord("w"), ord("W")):
                current_state = "ALL_ON"
                display_state(current_state)
            elif key in (ord("0"), ord("b"), ord("B")):
                current_state = "ALL_OFF"
                display_state(current_state)
            elif key in (ord("c"), ord("C")):
                current_state = "CHECKERBOARD"
                display_state(current_state)
            elif key in (ord("a"), ord("A")):
                print("\n[Auto Test] Running ON -> OFF -> ON sequence...")
                for s in ["ALL_ON", "ALL_OFF", "ALL_ON"]:
                    current_state = s
                    display_state(current_state)
                    time.sleep(1.2)
                print("[Auto Test] Completed.\n")
    finally:
        if cam is not None:
            cam.release()
        cv2.destroyAllWindows()
        print("[✓] DMD test window closed.")


def run_auto_test(
    x_offset: int,
    y_offset: int,
    width: int,
    height: int,
    fullscreen: bool = True,
) -> None:
    """Executes automated ON vs OFF toggle and measures camera optical response."""
    patterns = create_patterns(width, height)
    window_name = "DMD_Controller_Test"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.moveWindow(window_name, x_offset, y_offset)

    if fullscreen:
        cv2.setWindowProperty(
            window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )
    else:
        cv2.resizeWindow(window_name, width, height)

    captures_dir = Path("captures")
    captures_dir.mkdir(exist_ok=True)

    cam = None
    try:
        cam = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
        if not cam.isOpened():
            cam = None
        else:
            cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1600)
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1200)
            print("[✓] CMOS Camera connected.")
    except (ImportError, RuntimeError, OSError, cv2.error) as e:
        logger.debug("Failed opening camera: %s", e)
        cam = None

    print("\n" + "=" * 55)
    print(" RUNNING AUTOMATED DMD ON/OFF OPTICAL TEST")
    print("=" * 55)

    results = {}

    for state in ["ALL_OFF", "ALL_ON"]:
        print(f"\n[1] Projecting {state} on DMD...")
        cv2.imshow(window_name, patterns[state])
        cv2.waitKey(1)
        time.sleep(1.5)  # Let DMD mirrors settle and camera adjust

        if cam is not None:
            frame = None
            for _ in range(8):
                _ret, frame = cam.read()
                time.sleep(0.04)

            if frame is not None:
                gray = (
                    cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    if len(frame.shape) == 3
                    else frame
                )
                ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                save_file = captures_dir / f"dmd_{state.lower()}_{ts}.png"
                cv2.imwrite(str(save_file), frame)
                results[state] = {
                    "mean": float(gray.mean()),
                    "min": float(gray.min()),
                    "max": float(gray.max()),
                    "std": float(gray.std()),
                    "path": str(save_file),
                }
                print(f" -> Frame saved: {save_file}")
                print(
                    f" -> Intensity: Mean={results[state]['mean']:.2f} DN, Max={results[state]['max']:.0f} DN"
                )

    if cam is not None:
        cam.release()
    cv2.destroyAllWindows()

    print("\n" + "=" * 55)
    print(" DMD OPTICAL VERIFICATION SUMMARY")
    print("=" * 55)
    if "ALL_ON" in results and "ALL_OFF" in results:
        on_mean = results["ALL_ON"]["mean"]
        off_mean = results["ALL_OFF"]["mean"]
        diff = on_mean - off_mean
        ratio = (on_mean / off_mean) if off_mean > 0 else float("inf")
        print(f" ALL OFF Mean Intensity : {off_mean:.2f} DN")
        print(f" ALL ON  Mean Intensity : {on_mean:.2f} DN")
        print(
            f" Net Optical Shift      : +{diff:.2f} DN ({diff / max(off_mean, 1) * 100:.1f}%)"
        )
        print(f" On/Off Contrast Ratio  : {ratio:.2f}:1")
        print("=" * 55)
    else:
        print("[!] Camera was not available for optical measurement.")


def main() -> None:
    parser = argparse.ArgumentParser(description="DMD All-On / All-Off Toggle Test")
    parser.add_argument(
        "--monitor",
        type=int,
        default=None,
        help="Monitor index to project onto (default: auto-detects external monitor).",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run automated ON/OFF cycle with CMOS camera optical feedback.",
    )
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="Run in windowed mode rather than fullscreen.",
    )

    args = parser.parse_args()
    display_info = get_display_info(args.monitor)
    if display_info is None:
        return
    x, y, w, h = display_info

    if args.auto:
        run_auto_test(x, y, w, h, fullscreen=not args.windowed)
    else:
        run_interactive(x, y, w, h, fullscreen=not args.windowed)


if __name__ == "__main__":
    main()
