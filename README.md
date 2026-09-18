# Speckler

This project takes a laser and shines it into an occluded substrate attempting to focus a laser deeper 
via machine learning and digital micromirror devices.


## Speckler Version 1 

### Introduction
This project is a sub $1000 example for building a Biophotonics device that penetrates
a tissue phantom (such as a gelatin slide) via Lee Holography using a Digital Micromirror
Device and 650nm laser. 

### Setup
```mermaid
graph TD
    %% Main Nodes
    MAC["Mac M1 Max (Host Runtime)"]
    RP["QT Py RP2040 (Trigger Micro)"]
    DMD["Kodak Luma 150 (WVGA DMD)"]
    LASER["650nm Laser Diode"]
    CAM["Arducam OV2311 (Global Shutter)"]
    TISSUE["Tissue Phantom / Target"]

    %% USB & Control Streams
    MAC -- "1. USB Serial (/dev/tty.usbmodem)" --> RP
    MAC -- "2. HDMI (1080p @ 60Hz)" --> DMD
    CAM -- "3. USB 3.0 Frame Capture Stream" --> MAC

    %% Hardware Real-Time Triggers
    RP -- "A. GPIO26 (A0) / TTL Power Control" --> LASER
    RP -- "B. GPIO27 (A1) / Hardware Strobe Pulse" --> CAM

    %% Optical Path
    LASER -- "Coherent Red Light (45° Angle)" --> DMD
    DMD -- "Phase Mask Reflection (Binary Hologram)" --> TISSUE
    TISSUE -- "Backscattered Speckle Pattern" --> CAM

    %% Subgraphs for Organization
    subgraph Host ["Host Layer (uv / just)"]
        MAC
    end

    subgraph Micro ["Real-Time Timing Master"]
        RP
    end

    subgraph Hardware ["Optics & Sensors"]
        DMD
        LASER
        CAM
        TISSUE
    end

    %% Class Styles
    classDef hw fill:#2F4858,stroke:#ff9800,stroke-width:2px,color:#fff;
    
    class DMD,LASER,CAM,TISSUE,MAC,RP hw;
```

See full parts list in [EQUIPMENT_V1](./EQUIPMENT_V1.md). 

TODO: add photo

### Results


---


## V2
See [EQUIPMENT_V2.md](./EQUIPMENT_V2.md) for a parts list.
V2 will use a RF wideband amplifier paired with a low noise amp
and an oscilloscope. The low noise amp will be placed directly on 
the synthetic dermal tissue on the same side that the laser enters.
The laser causes tiny sound waves that the low noise amp picks up,
sends to the oscilloscope, and then is used as the training signal.

### TODO

Images & Write Up of Lab Setup

Code:
```
hardware/
- camera
- controller
- dmd

calculations/
- lee_hologram
- phase_retrieval
- signal_to_enhancement
- speckle

tests/

training/
```