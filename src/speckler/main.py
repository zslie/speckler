import argparse
import sys

import torch

from speckler.calculations.lee_hologram import (
    CMOSCameraModel,
    compute_pbr_loss,
    encode_lee_hologram,
    forward_pass,
)
from speckler.runtime.hardware.control_loop import build_hitl_pipeline

from .config import DMD_HEIGHT, DMD_WIDTH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Speckler Wavefront Shaping Pipeline (PyTorch + HITL)"
    )

    # Mode selection flags
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--hardware",
        action="store_true",
        help="Run in Physical Hardware mode (Kodak DMD + CMOS Camera).",
    )
    mode_group.add_argument(
        "--virtual",
        action="store_true",
        default=True,
        help="Run in Virtual Simulation mode (Default).",
    )

    # Optimization parameters
    parser.add_argument(
        "--steps",
        type=int,
        default=100,
        help="Number of optimization steps (default: 100).",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=0.1,
        help="Learning rate for Adam optimizer (default: 0.1).",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=600,
        help="Target focal pixel index on CMOS array (default: 600).",
    )
    parser.add_argument(
        "--elements",
        type=int,
        default=256,
        help="Number of DMD control segments (default: 256).",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Determine execution mode (--hardware overrides default --virtual)
    simulation_mode = not args.hardware
    mode_str = "VIRTUAL SIMULATION" if simulation_mode else "PHYSICAL HARDWARE"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[{mode_str}] Initializing pipeline on device: {device}")

    # Setup trainable parameters
    phi = torch.nn.Parameter(
        torch.rand(args.elements, device=device) * 2 * torch.pi
    )
    optimizer = torch.optim.Adam([phi], lr=args.lr)
    cmos_sim = CMOSCameraModel().to(device)
    # Simple dummy camera model: Converts complex E-field to raw intensity |E|^2
    # cmos_sim = lambda E_field: torch.abs(E_field) ** 2

    # Initialize Hardware-In-The-Loop interface
    hitl = build_hitl_pipeline(
        simulation_mode=simulation_mode,
        forward_model_fn=forward_pass,
        camera_sim_module=cmos_sim,
        lee_encoder_fn=encode_lee_hologram,
        dmd_resolution=(DMD_WIDTH, DMD_HEIGHT),
    )

    print(f"Starting optimization for {args.steps} steps...")
    print(f"Target Pixel: {args.target} | Control Elements: {args.elements} | LR: {args.lr}")

    try:
        for step in range(1, args.steps + 1):
            optimizer.zero_grad()

            # Execute HITL step: Project on DMD and grab frame
            cmos_counts, _ = hitl.step(phi)

            # Calculate Loss & Backpropagate
            loss, pbr = compute_pbr_loss(cmos_counts, args.target)

            if simulation_mode:
                loss.backward()
                optimizer.step()

            # Telemetry readout
            if step % 10 == 0 or step == args.steps:
                print(
                    f"Step {step:03d}/{args.steps} | Loss: {loss.item():.4f} | PBR: {pbr.item():.2f}"
                )

    except KeyboardInterrupt:
        print("\nOptimization interrupted by user.")
    finally:
        hitl.close()
        print("Pipeline shut down safely.")


if __name__ == "__main__":
    main()