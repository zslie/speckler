from abc import ABC, abstractmethod
from typing import Callable, Tuple

import numpy as np
import torch
from screeninfo import get_monitors

# Type aliases
DMDPattern = torch.Tensor | np.ndarray  # Shape: [Height, Width], binary 0 or 1
BinaryLeeEncoderFn = Callable[[torch.Tensor], torch.Tensor]


class BaseDMD(ABC):
    """Abstract Base Class for DMD controllers (Virtual or Physical)."""

    @abstractmethod
    def project(self, pattern: DMDPattern) -> None:
        """Projects a binary pattern onto the light path or virtual simulation."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Cleans up resources or closes display windows."""
        pass

class VirtualDMD(BaseDMD):
    """Digital twin DMD interface for PyTorch simulation."""

    def __init__(
        self,
        resolution: Tuple[int, int] = (480, 854),
        lee_encoder_fn: BinaryLeeEncoderFn | None = None,
    ) -> None:
        self.height, self.width = resolution
        self.lee_encoder = lee_encoder_fn
        self.current_pattern: torch.Tensor | None = None

    def project(self, pattern: DMDPattern) -> torch.Tensor:
        """
        Stores and returns the active binary Lee hologram pattern.
        If continuous phases are passed, encodes them to binary 0/1 states first.
        """
        if self.lee_encoder is not None and pattern.dtype == torch.float32:
            binary_pattern = self.lee_encoder(pattern)
        else:
            binary_pattern = pattern

        self.current_pattern = binary_pattern
        return self.current_pattern

    def stop(self) -> None:
        self.current_pattern = None

import cv2


class PhysicalDMD(BaseDMD):
    """Hardware interface for HDMI DLP projectors"""

    def __init__(self, resolution: None, monitor_index: int = 1) -> None:
        monitors = get_monitors()

        print("\n--- Display Enumeration ---")
        for i, m in enumerate(monitors):
            print(
                f" Monitor {i}: {m.name} | Resolution: {m.width}x{m.height} | Offset: (x={m.x}, y={m.y})"
            )

        # Target the extended monitor (index 1) if present
        if len(monitors) > monitor_index:
            target_monitor = monitors[monitor_index]
            self.offset_x = target_monitor.x
            self.offset_y = target_monitor.y
            self.width = target_monitor.width
            self.height = target_monitor.height
            print(
                f" -> Directing projection to Monitor {monitor_index} at offset ({self.offset_x}, {self.offset_y})"
            )
        else:
            print(
                " [!] Secondary monitor not detected! Falling back to primary screen offset (0, 0)."
            )
            self.offset_x, self.offset_y = 0, 0
            self.width, self.height = 854, 480

        # Create named window, slide it to the projector's X/Y offset, then set fullscreen
        self.window_name = "DMD_Projection"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.moveWindow(self.window_name, self.offset_x, self.offset_y)
        cv2.setWindowProperty(
            self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )

    def project(self, pattern: DMDPattern) -> None:
        """
        Converts 1-bit binary pattern tensor to 8-bit image and renders
        full-screen on the KODAK Luma 150 display.
        """
        # Convert PyTorch Tensor to NumPy
        if isinstance(pattern, torch.Tensor):
            img_np = pattern.detach().cpu().numpy()
        else:
            img_np = pattern

        # Scale binary (0 or 1) to 8-bit grayscale (0 or 255)
        img_uint8 = (img_np * 255).astype(np.uint8)

        # Ensure image dimensions match projector resolution exactly
        if img_uint8.shape[:2] != (self.height, self.width):
            img_uint8 = cv2.resize(
                img_uint8,
                (self.width, self.height),
                interpolation=cv2.INTER_NEAREST,
            )

        # Render pattern onto projector
        cv2.imshow(self.window_name, img_uint8)
        cv2.waitKey(1)  # Refresh display buffer

    def stop(self) -> None:
        """Closes projector display window."""
        cv2.destroyWindow(self.window_name)