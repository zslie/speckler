from abc import ABC, abstractmethod
from typing import Callable, Tuple

import numpy as np
import torch

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

    def __init__(
        self,
        display_offset_x: int = 1920,  # X coordinate where extended display begins
        display_offset_y: int = 0,     # Y coordinate offset
        resolution: Tuple[int, int] = (1920, 1080), # (Width, Height)
        window_name: str = "DMD_Projection",
    ) -> None:
        self.width, self.height = resolution
        self.window_name = window_name
        self.offset_x = display_offset_x
        self.offset_y = display_offset_y

        # Initialize OpenCV full-screen borderless window on secondary screen
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