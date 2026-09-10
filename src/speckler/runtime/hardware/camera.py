from abc import ABC, abstractmethod
from typing import Callable

import torch
from torch import nn


class BaseCamera(ABC):
    @abstractmethod
    def capture_frame(
        self, dmd_phases: torch.Tensor | None = None
    ) -> torch.Tensor:
        """Returns 2D float tensor of sensor counts [height, width]."""


class VirtualCamera(BaseCamera):
    """Digital camera, simulates hardware for offline PyTorch ML testing."""
    def __init__(
        self,
        forward_model_fn: Callable[[torch.Tensor], torch.Tensor],
        camera_sim_module: Callable[[torch.Tensor], torch.Tensor] | nn.Module,
    ):
        self.forward_model = forward_model_fn
        self.cam_sim = camera_sim_module

    def capture_frame(
        self, dmd_phases: torch.Tensor | None = None
    ) -> torch.Tensor:
        if dmd_phases is None:
            raise ValueError(
                "VirtualCamera requires `dmd_phases` to execute forward simulation."
            )

        # Simulate light propagation through tissue onto CMOS
        E_out = self.forward_model(dmd_phases)
        digital_counts = self.cam_sim(E_out)
        return digital_counts


class PhysicalCamera(BaseCamera):
    """Physical hardware interface using OpenCV."""
    def __init__(self, camera_index: int | None = None):
        import cv2
        from cv2_enumerate_cameras import enumerate_cameras

        # Auto-detect camera if index is not explicitly provided
        if camera_index is None:
            for camera_info in enumerate_cameras():
                print(f"Device Index: {camera_info.index}")
                print(f"Camera Name:  {camera_info.name}")
                print(f"Backend Used: {camera_info.backend}\n")

                # Case-insensitive substring search without throwing ValueError
                if "ov2311" in camera_info.name.lower():
                    camera_index = camera_info.index
                    break

        if camera_index is None:
            raise RuntimeError(
                "Could not find CMOS camera index. Pass `camera_index` explicitly."
            )

        self.cap = cv2.VideoCapture(camera_index)

    def capture_frame(
        self, dmd_phases: torch.Tensor | None = None
    ) -> torch.Tensor:
        import cv2

        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError(
                "Failed to capture frame from physical CMOS camera."
            )

        # Convert grayscale frame to PyTorch tensor
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return torch.from_numpy(gray).float()