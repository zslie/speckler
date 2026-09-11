# Speckler

This project takes a laser and shines it into an occluded substrate attempting to focus a laser deeper via machine learning and digital micromirror devices.



### Speckle Detection
#### V1
See [EQUIPMENT_V1.md](./EQUIPMENT_V1.md) for a parts list.
V1 uses a Arducam 2MP CMOS camera for speckle detection based
on brightness from F1 of the Lee Hologram. The camera is positioned
behind the sample (such a milk with water or another opaque liquid)
and attempts to measure the scattered photon count.


#### V2
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