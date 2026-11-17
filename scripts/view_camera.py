#!/usr/bin/env python3
"""Arducam CMOS Camera Viewer & Diagnostic Tool.

Directly connects to the Arducam OV2311 CMOS camera without polling
or activating other connected cameras (e.g. FaceTime HD or Continuity cameras).

Usage:
    # Live preview GUI with HUD, crosshairs, colormaps, snapshot saving:
    uv run python scripts/view_camera.py

    # Single snapshot mode (headless/no GUI window):
    uv run python scripts/view_camera.py --snapshot

    # Specify output snapshot filename:
    uv run python scripts/view_camera.py --snapshot --output bench_view.png

    # Override camera index:
    uv run python scripts/view_camera.py --index 0

Keybindings in Live GUI:
    q, ESC : Quit preview
    s      : Save snapshot to disk
    c      : Toggle crosshair / alignment grid
    m      : Cycle colormap (Grayscale, Inferno, Viridis, Jet)
    h      : Toggle HUD telemetry overlay
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger("arducam_view")


def find_arducam_index() -> int:
    """Finds the device index for Arducam OV2311 without polling other cameras."""
    # OpenCV AVFoundation backend indexes external USB cameras (like Arducam) at index 0
    # Arducam OV2311 is distinctively 1600x1200 native resolution
    try:
        test_cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
        if test_cap.isOpened():
            w = int(test_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(test_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            test_cap.release()
            if (w, h) == (1600, 1200):
                print(f"[✓] Located Arducam OV2311 ({w}x{h}) at index 0")
                return 0
    except (ImportError, RuntimeError, OSError, cv2.error) as e:
        logger.debug("Check on index 0 failed: %s", e)

    try:
        import AVFoundation

        devices = AVFoundation.AVCaptureDevice.devicesWithMediaType_(
            AVFoundation.AVMediaTypeVideo
        )
        for idx, dev in enumerate(devices):
            name = dev.localizedName().lower()
            if "arducam" in name or "ov2311" in name:
                print(
                    f"[✓] Located Arducam device: '{dev.localizedName()}' at index {idx}"
                )
                return idx
    except (ImportError, RuntimeError, OSError) as e:
        logger.debug("Failed querying AVFoundation metadata: %s", e)

    # Default fallback index
    print("[i] Using default camera index 0")
    return 0


def capture_single_frame(
    camera_index: int,
    output_path: str | None = None,
    width: int = 1600,
    height: int = 1200,
) -> None:
    """Captures a single frame, prints intensity stats, and saves to disk."""
    cap = cv2.VideoCapture(camera_index, cv2.CAP_AVFOUNDATION)
    if not cap.isOpened():
        print(f"Error: Unable to open camera at index {camera_index}", file=sys.stderr)
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    # Warm-up sensor so auto-exposure settles
    frame = None
    for _ in range(8):
        ret, current_frame = cap.read()
        if ret:
            frame = current_frame
        time.sleep(0.04)

    cap.release()

    if frame is None:
        print("Error: Failed to grab frame from Arducam.", file=sys.stderr)
        sys.exit(1)

    # Analyze intensity
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    h, w = gray.shape

    if output_path is None:
        out_dir = Path("captures")
        out_dir.mkdir(exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = str(out_dir / f"arducam_{timestamp}.png")

    cv2.imwrite(output_path, frame)

    saturated_pct = (np.count_nonzero(gray >= 254) / gray.size) * 100.0
    print("=" * 50)
    print(" ARDUCAM OV2311 SNAPSHOT SUMMARY")
    print("=" * 50)
    print(f" Saved To            : {output_path}")
    print(f" Resolution          : {w} x {h} px")
    print(f" Min Intensity (DN)  : {gray.min()}")
    print(f" Max Intensity (DN)  : {gray.max()}")
    print(f" Mean Intensity (DN) : {gray.mean():.2f}")
    print(f" Std Dev (DN)        : {gray.std():.2f}")
    print(f" Saturation (>=254)  : {saturated_pct:.2f}%")
    print("=" * 50)


def run_live_preview(
    camera_index: int,
    width: int = 1600,
    height: int = 1200,
) -> None:
    """Runs interactive live preview window with real-time stats and controls."""
    cap = cv2.VideoCapture(camera_index, cv2.CAP_AVFOUNDATION)
    if not cap.isOpened():
        print(f"Error: Unable to open camera at index {camera_index}", file=sys.stderr)
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    window_name = "Arducam OV2311 - Live Preview (Speckler)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, min(actual_w, 1280), min(actual_h, 960))

    print("\n" + "=" * 55)
    print(" ARDUCAM LIVE PREVIEW CONTROLS")
    print("=" * 55)
    print("  'q' / ESC : Exit preview")
    print("  's'       : Save snapshot to captures/")
    print("  'c'       : Toggle center crosshairs / alignment grid")
    print("  'm'       : Cycle colormap (Gray -> Inferno -> Viridis -> Jet)")
    print("  'h'       : Toggle HUD overlay")
    print("=" * 55 + "\n")

    # State variables
    show_hud = True
    show_crosshairs = False
    colormap_idx = 0  # 0: Grayscale, 1: Inferno, 2: Viridis, 3: Jet
    colormaps = [
        ("GRAYSCALE", None),
        ("INFERNO", cv2.COLORMAP_INFERNO),
        ("VIRIDIS", cv2.COLORMAP_VIRIDIS),
        ("JET", cv2.COLORMAP_JET),
    ]

    last_saved_msg = ""
    last_saved_time = 0.0

    fps = 0.0
    frame_count = 0
    t_start = time.time()

    captures_dir = Path("captures")
    captures_dir.mkdir(exist_ok=True)

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("[!] Frame read failed. Retrying...", file=sys.stderr)
                time.sleep(0.01)
                continue

            frame_count += 1
            now = time.time()
            elapsed = now - t_start
            if elapsed >= 0.5:
                fps = frame_count / elapsed
                frame_count = 0
                t_start = now

            # Ensure single-channel grayscale base
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame

            h, w = gray.shape

            # Apply colormap mode if selected
            cm_name, cm_code = colormaps[colormap_idx]
            if cm_code is not None:
                display_img = cv2.applyColorMap(gray, cm_code)
            else:
                display_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

            # Draw crosshairs
            if show_crosshairs:
                cx, cy = w // 2, h // 2
                color = (0, 255, 0)
                # Center cross
                cv2.line(display_img, (cx - 40, cy), (cx + 40, cy), color, 1)
                cv2.line(display_img, (cx, cy - 40), (cx, cy + 40), color, 1)
                cv2.circle(display_img, (cx, cy), 15, color, 1)
                cv2.circle(display_img, (cx, cy), 60, (0, 200, 200), 1)
                # Frame grid lines
                cv2.line(display_img, (0, cy), (w, cy), (0, 100, 0), 1, cv2.LINE_AA)
                cv2.line(display_img, (cx, 0), (cx, h), (0, 100, 0), 1, cv2.LINE_AA)

            # Draw HUD
            if show_hud:
                # Calculate quick stats
                min_val = int(gray.min())
                max_val = int(gray.max())
                mean_val = float(gray.mean())
                sat_pct = (np.count_nonzero(gray >= 254) / gray.size) * 100.0

                # Semi-transparent HUD box
                overlay = display_img.copy()
                box_h = 135
                box_w = 340
                cv2.rectangle(
                    overlay,
                    (10, 10),
                    (10 + box_w, 10 + box_h),
                    (20, 20, 20),
                    -1,
                )
                cv2.addWeighted(overlay, 0.75, display_img, 0.25, 0, display_img)

                # Text annotations
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.48
                color_white = (255, 255, 255)

                lines = [
                    f"Arducam OV2311 ({w}x{h}) | {fps:.1f} FPS",
                    f"Mean: {mean_val:5.1f} | Min: {min_val:3d} | Max: {max_val:3d}",
                    f"Colormap: {cm_name} (press 'm')",
                    f"Crosshair: {'ON' if show_crosshairs else 'OFF'} (press 'c')",
                ]
                if sat_pct > 0.5:
                    lines.append(f"SATURATION: {sat_pct:.1f}% OVEREXPOSED!")
                else:
                    lines.append(f"Saturation: {sat_pct:.2f}% (normal)")

                for i, text in enumerate(lines):
                    y_pos = 32 + i * 22
                    col = (0, 0, 255) if "SATURATION:" in text else color_white
                    cv2.putText(
                        display_img,
                        text,
                        (20, y_pos),
                        font,
                        font_scale,
                        col,
                        1,
                        cv2.LINE_AA,
                    )

            # Show snapshot flash message
            if last_saved_msg and (time.time() - last_saved_time < 2.5):
                cv2.putText(
                    display_img,
                    last_saved_msg,
                    (20, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )

            cv2.imshow(window_name, display_img)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):  # 'q' or ESC
                break
            elif key == ord("s"):  # Save snapshot
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                save_path = captures_dir / f"arducam_{timestamp}.png"
                cv2.imwrite(str(save_path), frame)
                last_saved_msg = f"[SAVED] {save_path.name}"
                last_saved_time = time.time()
                print(f"[✓] Snapshot saved to: {save_path}")
            elif key == ord("c"):  # Toggle crosshairs
                show_crosshairs = not show_crosshairs
            elif key == ord("m"):  # Cycle colormaps
                colormap_idx = (colormap_idx + 1) % len(colormaps)
            elif key == ord("h"):  # Toggle HUD
                show_hud = not show_hud

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\n[✓] Camera feed released cleanly.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Arducam OV2311 CMOS Camera View & Diagnostics"
    )
    parser.add_argument(
        "--index",
        type=int,
        default=None,
        help="Camera device index (auto-detects Arducam by default).",
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Capture a single frame to disk without launching GUI preview.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output image path for --snapshot mode (e.g. captures/view.png).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1600,
        help="Target frame width in pixels (default: 1600).",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=1200,
        help="Target frame height in pixels (default: 1200).",
    )

    args = parser.parse_args()

    # Determine Arducam device index
    cam_index = args.index if args.index is not None else find_arducam_index()

    if args.snapshot:
        capture_single_frame(
            camera_index=cam_index,
            output_path=args.output,
            width=args.width,
            height=args.height,
        )
    else:
        run_live_preview(
            camera_index=cam_index,
            width=args.width,
            height=args.height,
        )


if __name__ == "__main__":
    main()
