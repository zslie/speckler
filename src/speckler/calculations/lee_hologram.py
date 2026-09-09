import torch
from torch import nn

torch.manual_seed(42)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# -----------------------------------------------------------------------------
# 1. Setup Parameters
# -----------------------------------------------------------------------------
N_elements = 256  # Control segments
N_pixels = 64 * 64  # CMOS sensor grid (64x64)
target_pixel = 2048  # Target focal coordinate

# Carrier spatial frequency for off-axis Lee encoding
carrier_freq = 4.0

# Transmission Matrix representing tissue scattering
real_part = torch.randn(N_pixels, N_elements, device=device)
imag_part = torch.randn(N_pixels, N_elements, device=device)
TM = torch.complex(real_part, imag_part) / (N_elements**0.5)


# -----------------------------------------------------------------------------
# 2. Straight-Through Binarization Custom Autograd Function
# -----------------------------------------------------------------------------
class StraightThroughBinarize(torch.autograd.Function):

    @staticmethod
    def forward(ctx, input_pattern):
        # Hard thresholding for forward pass: 1 if >= 0.5, else 0
        return (input_pattern >= 0.5).float()

    @staticmethod
    def backward(ctx, grad_output):
        # Pass gradient straight through unchanged during backward pass
        return grad_output


binarize = StraightThroughBinarize.apply


# -----------------------------------------------------------------------------
# 3. Differentiable Lee Encoding & Forward Propagation
# -----------------------------------------------------------------------------
def encode_lee_hologram(phases: torch.Tensor) -> torch.Tensor:
    """Encodes continuous phase shifts into binary Lee hologram subpixel values."""
    # Create 4-phase subpixel spatial carrier
    x = torch.linspace(0, 1, phases.shape[0], device=device)
    carrier = 2 * torch.pi * carrier_freq * x

    # Interference pattern: I = 0.5 * (1 + cos(carrier - phi))
    continuous_lee = 0.5 * (1.0 + torch.cos(carrier - phases))

    # Apply Straight-Through Binarization for 1-bit DMD mirrors (0 or 1)
    binary_dmd = binarize(continuous_lee)
    return binary_dmd


def forward_pass(phases: torch.Tensor):
    """Encodes DMD binary pattern and propagates through scattering matrix.

    Returns complex E_out field for VirtualCamera processing.
    """
    # 1. Generate Binary DMD Pattern (1-bit)
    dmd_pattern = encode_lee_hologram(phases)

    # 2. 1st-Order Carrier Demodulation (Simulating 4f spatial filter filtering out DC)
    E_in = torch.complex(dmd_pattern, torch.zeros_like(dmd_pattern))

    # 3. Propagate through Tissue Transmission Matrix
    E_out = torch.matmul(TM, E_in)

    return E_out


def compute_pbr_loss(counts: torch.Tensor, target_idx: int):
    """Computes Negative Peak-to-Background Ratio (PBR) on CMOS counts/intensity."""
    I_target = counts[target_idx]

    mask = torch.ones(len(counts), dtype=torch.bool, device=counts.device)
    mask[target_idx] = False
    I_background = torch.mean(counts[mask])

    pbr = I_target / (I_background + 1e-8)
    return -pbr, pbr


class CMOSCameraModel(nn.Module):
    """Differentiable CMOS sensor model simulating intensity-to-digital counts.

    Includes photon shot noise, read noise, full-well saturation, and bit quantization.
    """

    def __init__(
        self,
        quantum_efficiency: float = 0.60,
        exposure_time: float = 1e-3,
        pixel_area_m2: float = (3.45e-6) ** 2,
        wavelength_m: float = 632.8e-9,
        read_noise_std: float = 1.5,
        dark_current: float = 10.0,
        full_well_capacity: float = 10000.0,
        adc_bit_depth: int = 12,
        gain: float = 1.0,
    ) -> None:
        super().__init__()
        self.qe = quantum_efficiency
        self.t_exp = exposure_time
        self.A_pix = pixel_area_m2
        self.read_noise = read_noise_std
        self.dark_current = dark_current
        self.fwc = full_well_capacity
        self.adc_max = 2**adc_bit_depth - 1
        self.gain = gain

        # Photon energy h*c / lambda
        self.e_photon = (6.626e-34 * 3.0e8) / wavelength_m

    def forward(self, field_or_intensity: torch.Tensor) -> torch.Tensor:
        """Converts electric field (or optical intensity) into CMOS digital counts (DN)."""
        # 1. Compute Optical Intensity [W/m^2]
        if field_or_intensity.is_complex():
            intensity = torch.abs(field_or_intensity) ** 2
        else:
            intensity = field_or_intensity

        # 2. Expected Photoelectrons
        power_per_pixel = intensity * self.A_pix
        photons_per_pixel = (power_per_pixel * self.t_exp) / self.e_photon
        mean_electrons = (photons_per_pixel * self.qe) + (
            self.dark_current * self.t_exp
        )

        # 3. Shot Noise
        if self.training:
            shot_noise = torch.randn_like(mean_electrons) * torch.sqrt(
                torch.clamp(mean_electrons, min=1e-6)
            )
            electrons = mean_electrons + shot_noise
        else:
            electrons = torch.poisson(torch.clamp(mean_electrons, min=0.0))

        # 4. Read Noise & Full-Well Saturation
        read_noise = torch.randn_like(electrons) * self.read_noise
        total_electrons = torch.clamp(
            electrons + read_noise, min=0.0, max=self.fwc
        )

        # 5. ADC Quantization to Digital Numbers (DN)
        digital_number = (
            (total_electrons / self.fwc) * self.adc_max * self.gain
        )
        return torch.clamp(digital_number, 0.0, float(self.adc_max))