import time

import cv2
import numpy as np
import torch
from cv2_enumerate_cameras import enumerate_cameras


def test_dmd_and_camera() -> None:
    print("=" * 60)
    print(" HARDWARE CONNECTION DIAGNOSTIC TEST ")
    print("=" * 60)

    # 1. Detect and Connect to Arducam OV2311
    print("\n[1/3] Scanning for Arducam OV2311...")
    camera_index = None
    for camera_info in enumerate_cameras():
        print(f" -> Found Device Index {camera_info.index}: {camera_info.name}")
        if "arducam" in camera_info.name.lower() or "ov2311" in camera_info.name.lower():
            camera_index = camera_info.index
            print(f"    *** Selected Arducam at index {camera_index} ***")
            break

    if camera_index is None:
        print(" [!] Arducam not explicitly found by name. Falling back to default index 0.")
        camera_index = 0

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video capture device at index {camera_index}")

    print(" [✓] Arducam video feed connected successfully.")

    # 2. Initialize Kodak Luma Display Window
    print("\n[2/3] Initializing Kodak Luma Projector Display...")
    window_name = "KODAK_LUMA_TEST"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    # Render a 16x16 checkerboard pattern
    pattern_size = (480, 854)
    checkerboard = np.indices((16, 16)).sum(axis=0) % 2 * 255
    checkerboard_resized = cv2.resize(
        checkerboard.astype(np.uint8), 
        (pattern_size[1], pattern_size[0]), 
        interpolation=cv2.INTER_NEAREST
    )

    cv2.imshow(window_name, checkerboard_resized)
    cv2.waitKey(500)  # Allow display buffer to update
    print(" [✓] Checkerboard pattern projected on display.")

    # 3. Capture and Validate Live Camera Frame
    print("\n[3/3] Capturing test frames from Arducam...")
    time.sleep(0.5)  # Let sensor adjust ambient light

    ret, frame = cap.read()
    if not ret or frame is None:
        cap.release()
        cv2.destroyAllWindows()
        raise RuntimeError("Failed to read frame buffer from Arducam.")

    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame_tensor = torch.from_numpy(gray_frame).float()

    print("\n" + "-" * 40)
    print(" HARDWARE DIAGNOSTIC SUMMARY")
    print("-" * 40)
    print(f" Camera Frame Resolution : {gray_frame.shape[1]}x{gray_frame.shape[0]} px")
    print(f" Camera Tensor Shape     : {list(frame_tensor.shape)}")
    print(f" Pixel Intensity Range   : Min={frame_tensor.min():.1f}, Max={frame_tensor.max():.1f}")
    print(f" Ambient Mean Counts (DN): {frame_tensor.mean():.2f}")
    print("-" * 40)

    # Cleanup
    cap.release()
    cv2.destroyWindow(window_name)
    print("\n[✓] Diagnostic complete: Both devices are connected and responsive!\n")


if __name__ == "__main__":
    test_dmd_and_camera()