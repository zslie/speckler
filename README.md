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

##### Bench
![Bench](images/bench/bench.jpg)
##### DMD Board
![DMD](images/bench/dmd-board.jpg)
##### Speckle
![Speckle](images/bench/speckle.jpg)

### Results


---


## V2
See [EQUIPMENT_V2.md](./EQUIPMENT_V2.md) for a parts list.
V2 will use a RF wideband amplifier paired with a low noise amp
and an oscilloscope. The low noise amp will be placed directly on 
the synthetic dermal tissue on the same side that the laser enters.
The laser causes tiny sound waves that the low noise amp picks up,
sends to the oscilloscope, and then is used as the training signal.

```mermaid
graph TD
    %% Main Nodes
    MAC["Mac M1 Max (Python PyVISA/SCPI Loop)"]
    DLPC["TI DLPC900 Controller Board"]
    DMD["TI DLP6500 DMD (0.65' Mirror Array)"]
    LASER["808nm 500mW Laser Diode Module"]
    RP["QT Py RP2040 (Laser Gate / Safety Interlock)"]
    
    %% Optical Path Components
    L1["Lens 1: Bi-Concave (DCV, f = -50mm)"]
    L2["Lens 2: Plano-Convex (PCX, f = +100mm)"]
    L3["Lens 3: Achromatic Doublet 1 (f = 100mm)"]
    IRIS["Spatial Filter / Iris (Fourier Plane)"]
    L4["Lens 4: Achromatic Doublet 2 (f = 100mm or 75mm)"]
    TISSUE["Tissue Phantom / Target (5mm Depth)"]

    %% Acoustic & Feedback Path
    XDUCER["Panametrics V312 Transducer (10MHz, F=0.75' PTF)"]
    LNA["HiLetgo LNA (+30dB, 12V Powered)"]
    SCOPE["Rigol DHO804 Oscilloscope (12-bit ADC)"]

    %% Data & USB Control Links
    MAC -- "1. USB Command / Pattern Stream" --> DLPC
    MAC -- "2. SCPI Waveform Fetch (PyVISA over USB/Ethernet)" --> SCOPE
    MAC -. "3. Optional Safety/Gate Config (USB Serial)" .-> RP

    %% Real-Time Hardware Triggers
    DLPC -- "A. Hardware TRIG_OUT_1 (BNC)" --> SCOPE
    DLPC -- "B. Hardware TRIG_OUT_2 (TTL)" --> RP
    RP -- "C. Gated TTL Control Signal (3.3V to 5V Shifter)" --> LASER

    %% Beam Conditioning Optics Path
    LASER -- "Raw Elliptical 808nm Beam" --> L1
    L1 -- "Diverging Light Cone" --> L2
    L2 -- "Collimated 2x Beam (6x10mm)" --> DMD

    %% 4f Projection Optics Path
    DMD -- "Diffracted Binary Hologram" --> L3
    L3 -- "Focused Spatial Frequencies" --> IRIS
    IRIS -- "Isolated Central Order (0th/+1st)" --> L4
    L4 -- "Focused Wavefront Image" --> TISSUE

    %% Acoustic Feedback Signal Chain
    TISSUE -- "Photoacoustic Pressure Wave" --> XDUCER
    XDUCER -- "Low-mV Signal (BNC to SMA Cable)" --> LNA
    LNA -- "Amplified Signal (+30dB, SMA to BNC Cable)" --> SCOPE

    %% Subgraphs for Organization
    subgraph Host ["Host Layer"]
        MAC
    end

    subgraph SpeedEngine ["Fast Switching & Timing Engine"]
        DLPC
        RP
    end

    subgraph Optics ["Beam Conditioning & 4f System"]
        LASER
        L1
        L2
        DMD
        L3
        IRIS
        L4
    end

    subgraph Target ["Sample & Detection Zone"]
        TISSUE
        XDUCER
    end

    subgraph Feedback ["Acoustic Processing & Digitization"]
        LNA
        SCOPE
    end

    %% Class Styling
    classDef hw fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef optics fill:#0f766e,stroke:#2dd4bf,stroke-width:2px,color:#fff;
    classDef signal fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#fff;

    class MAC,DLPC,RP,SCOPE hw;
    class LASER,L1,L2,DMD,L3,IRIS,L4 optics;
    class TISSUE,XDUCER,LNA signal;
```

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