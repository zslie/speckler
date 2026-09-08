# Runtime

This is where the hardware level code lives.

In `hardware/` there is `camera.py`, `controller.py` (for the arduino), and `dmd.py` (for the digital micromirror device).

In `ui/` there is `monitor.py` which displays instrumentation reads coming live from the hardware while
the runtime is going.

Testing is back up a level in `../tests/hardware/`.
