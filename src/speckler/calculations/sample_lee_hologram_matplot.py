import matplotlib.pyplot as plt
import numpy as np

from speckler.config import DMD_HEIGHT, DMD_WIDTH

# 1. Spatial Grid tailored to DMD resolution
y = np.linspace(-1, 1, DMD_HEIGHT)
x = np.linspace(-1, 1, DMD_WIDTH)
X, Y = np.meshgrid(x, y)

# 2. Target Field: Focused Spot Off-Axis (Target Beam Steering)
# Shifting in frequency space simulates targeting a specific spot on/in a substrate
target_x, target_y = 0.3, -0.2
carrier_freq = 20.0  # Spatial carrier frequency along X
phase_target = 2 * np.pi * (carrier_freq * X) + 15.0 * ((X - target_x)**2 + (Y - target_y)**2)
amplitude_target = np.exp(-((X - target_x)**2 + (Y - target_y)**2) / 0.1)

U = amplitude_target * np.exp(1j * phase_target)

# 3. Continuous Lee Decomposition (4-subpixel)
Ur = np.real(U)
Ui = np.imag(U)

F1 = np.maximum(Ur, 0)   # Phase 0
F2 = np.maximum(-Ur, 0)  # Phase \pi
F3 = np.maximum(Ui, 0)   # Phase \pi/2
F4 = np.maximum(-Ui, 0)  # Phase 3\pi/2

# Assemble sub-pixels (Width expands 4x internally, or scaled down)
lee_continuous = np.zeros((DMD_HEIGHT, DMD_WIDTH), dtype=float)
# Assign sub-columns across the native DMD width
lee_continuous[:, 0::4] = F1[:, 0::4]
lee_continuous[:, 1::4] = F3[:, 1::4]
lee_continuous[:, 2::4] = F2[:, 2::4]
lee_continuous[:, 3::4] = F4[:, 3::4]

if lee_continuous.max() > 0:
    lee_continuous /= lee_continuous.max()

# 4. Binary Thresholding for DMD display
threshold = 0.5
lee_binary = (lee_continuous > threshold).astype(float)

# 5. Far-Field Optical Reconstructions (2D FFT)
rec_continuous = np.abs(np.fft.fftshift(np.fft.fft2(lee_continuous)))**2
rec_binary = np.abs(np.fft.fftshift(np.fft.fft2(lee_binary)))**2

# 6. Plotting
fig, axes = plt.subplots(2, 2, figsize=(12, 8))

# Continuous Pattern & Reconstruction
axes[0, 0].imshow(lee_continuous[:64, :128], cmap='gray', aspect='auto')
axes[0, 0].set_title("Continuous Lee Pattern (Zoomed 64x128)")

axes[0, 1].imshow(np.sqrt(rec_continuous), cmap='magma')
axes[0, 1].set_title("Continuous Optical Reconstruction")

# Binary DMD Pattern & Reconstruction
axes[1, 0].imshow(lee_binary[:64, :128], cmap='binary', aspect='auto')
axes[1, 0].set_title("Binary DMD Pattern (Zoomed 64x128)")

axes[1, 1].imshow(np.sqrt(rec_binary), cmap='magma')
axes[1, 1].set_title("Binary DMD Optical Reconstruction")

for ax in axes.flat:
    ax.axis('off')

plt.tight_layout()
plt.show()