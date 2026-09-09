from abc import ABC, Callable, abstractmethod

import numpy as np
import torch


class BaseCamera(ABC):
    @abstractmethod
    def capture_frame(self) -> torch.Tensor:
        """Returns 2D float tensor of sensor counts [height, width]."""
        pass

class VirtualCamera(BaseCamera):
    """Digital camera, simulates hardware for offline PyTorch ML testing."""
    def __init__(
            self, 
            forward_model_fn: Callable[[torch.Tensor], torch.Tensor], 
            camera_sim_module: Callable[[torch.Tensor], torch.Tensor] | np.nn.Module
        ):
        self.forward_model = forward_model_fn
        self.cam_sim = camera_sim_module

    def capture_frame(self, dmd_phases: torch.Tensor) -> torch.Tensor:
        # Simulate light propagation through tissue onto CMOS
        E_out = self.forward_model(dmd_phases)
        digital_counts = self.cam_sim(E_out)
        return digital_counts

class PhysicalCamera(BaseCamera):
    """Physical hardware interface using OpenCV"""
    def __init__(self, camera_index: int | None = None):
        import cv2
        from cv2_enumerate_cameras import enumerate_cameras
        
        for camera_info in enumerate_cameras():
            print(f"Device Index: {camera_info.index}")
            print(f"Camera Name:  {camera_info.name}")
            print(f"Backend Used: {camera_info.backend}\n")
            if camera_info.name.index('cmos'):
                camera_index = camera_info.index
                break

        if camera_index is None:
            raise Exception("Could not find camera index")

        self.cap = cv2.VideoCapture(camera_index)

    def capture_frame(self) -> torch.Tensor:
        import cv2
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to capture frame from physical CMOS camera.")
        
        # Convert grayscale frame to PyTorch tensor
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return torch.from_numpy(gray).float()