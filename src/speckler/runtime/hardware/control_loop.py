from typing import Tuple

import torch

from .camera import BaseCamera, PhysicalCamera, VirtualCamera
from .dmd import BaseDMD, PhysicalDMD, VirtualDMD


class HardwareInTheLoop:
    """Unified Hardware-In-The-Loop interface for DMD projection and CMOS camera acquisition.

    Handles seamless execution across both virtual PyTorch simulations and physical
    bench setups (e.g. KODAK Luma 150 + CMOS camera).
    """

    def __init__(
        self,
        dmd: BaseDMD,
        camera: BaseCamera,
        is_simulation: bool = True,
    ) -> None:
        self.dmd = dmd
        self.camera = camera
        self.is_simulation = is_simulation

    def step(
        self,
        phases_or_pattern: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor | None]:
        """Executes one control cycle: Projects pattern on DMD and reads back camera counts.

        Args:
            phases_or_pattern: 1D or 2D PyTorch float tensor representing continuous
              phases [0, 2pi] or pre-encoded binary DMD mirrors [0, 1].

        Returns:
            Tuple containing:
                - cmos_frame: 2D torch.Tensor of camera digital counts [Height, Width].
                - active_pattern: The 1-bit binary pattern displayed on DMD (or None).
        """
        # 1. Project pattern onto DMD (Virtual or Physical)
        if isinstance(self.dmd, VirtualDMD):
            active_pattern = self.dmd.project(phases_or_pattern)
        else:
            self.dmd.project(phases_or_pattern)
            active_pattern = None

        # 2. Acquire camera frame (Virtual forward model or Physical CMOS SDK/OpenCV)
        if isinstance(self.camera, VirtualCamera):
            # Virtual camera requires the DMD phase/pattern tensor to compute forward TM physics
            cmos_frame = self.camera.capture_frame(phases_or_pattern)
        else:
            # Physical camera grabs live frame from hardware bus
            cmos_frame = self.camera.capture_frame()

        return cmos_frame, active_pattern

    def close(self) -> None:
        """Cleans up display windows, video devices, and hardware handles."""
        self.dmd.stop()
        if isinstance(self.camera, PhysicalCamera):
            self.camera.cap.release()


def build_hitl_pipeline(
    simulation_mode: bool = True,
    forward_model_fn=None,
    camera_sim_module=None,
    lee_encoder_fn=None,
    dmd_resolution: Tuple[int, int] = (854, 480),
    camera_index: int | None = None,
) -> HardwareInTheLoop:
    """Factory helper to construct HITL pipelines for testing or hardware execution."""
    if simulation_mode:
        if forward_model_fn is None or camera_sim_module is None:
            raise ValueError(
                "Simulation mode requires both `forward_model_fn` and `camera_sim_module`."
            )

        dmd = VirtualDMD(resolution=dmd_resolution, lee_encoder_fn=lee_encoder_fn)
        camera = VirtualCamera(
            forward_model_fn=forward_model_fn,
            camera_sim_module=camera_sim_module,
        )
    else:
        dmd = PhysicalDMD(resolution=dmd_resolution)
        print("Getting hardware devices... \nCamera Index: {}", camera_index)
        camera = PhysicalCamera(camera_index=camera_index)

    return HardwareInTheLoop(dmd=dmd, camera=camera, is_simulation=simulation_mode)