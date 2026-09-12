# justfile for Speckle Logic biophotonic testbench
set dotenv-load := true

# Default recipe: list available commands
default:
    @just --list

# Initialize Python environment & install locked dependencies
setup:
    uv sync
    uv python pin 3.12

log-rp2040:
    uv run --with pyserial python -m serial.tools.miniterm /dev/tty.usbmodem* 115200

# Execute pytest suite against environment
test:
    uv run pytest

# Check code formatting & lint issues
check:
    uv run ruff check .
    uv run ruff format --check .

# Auto-fix linting & format code
format:
    uv run ruff check --fix .
    uv run ruff format .

# Train offline wavefront phase retrieval model
train:
    uv run python training/train.py

# Reset local virtual environment
clean:
    rm -rf .venv
    rm -rf .pytest_cache
    rm -rf __pycache__

sync:
    uv sync

# Run the wavefront shaping pipeline
#   just run virtual    (Runs PyTorch simulation mode)
#   just run hardware   (Runs physical DMD + CMOS camera mode)
run mode="virtual" *args="":
    @if [ "{{mode}}" = "hardware" ]; then \
        uv run python -m speckler.main --hardware {{args}}; \
    elif [ "{{mode}}" = "virtual" ]; then \
        uv run python -m speckler.main {{args}}; \
    else \
        echo "Error: Unknown mode '{{mode}}'. Use 'virtual' or 'hardware'."; \
        exit 1; \
    fi

# Shortcut recipes
virtual *args="":
    just run virtual {{args}}

hardware *args="":
    just run hardware {{args}}

# Run test scripts
align-dmd:
    uv run python -m speckler.scripts.test_dmd_alignment