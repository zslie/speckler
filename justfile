# justfile for Speckle Logic biophotonic testbench
set dotenv-load := true

# Default recipe: list available commands
default:
    @just --list

# Initialize Python environment & install locked dependencies
setup:
    uv sync
    uv python pin 3.12

# Run the 60Hz real-time camera/DMD control loop
run:
    uv run python runtime/main.py

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