# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Purpose

taxi-on-ryusim ports all 162 cocotb tests from [fpganinja/taxi](https://github.com/fpganinja/taxi) to run on [RyuSim](https://ryusim.seiraiyu.com), validating RyuSim's SystemVerilog compilation and simulation against a production-grade FPGA IP library.

## Architecture

- `taxi/` — Git submodule (read-only) containing the taxi FPGA IP library and original tests
- `src/` — Ported tests mirroring taxi's directory structure, modified to use RyuSim
- `scripts/` — Automation tooling (porting script)

### Per-test structure

Each ported test directory contains:
- `Makefile` — Copied from taxi, modified: `SIM ?= ryusim`, paths redirect into `taxi/` submodule, ryusim `-G` parameter block added
- `test_*.py` — Copied from taxi, modified: `simulator="ryusim"`, paths redirect into `taxi/` submodule
- `test_*.sv` — Symlink into `taxi/` submodule (only present when taxi has a SV testbench wrapper)

### Path resolution

Makefiles use `TAXI_ROOT` (computed via `git rev-parse --show-toplevel`) to locate RTL sources in the submodule:
```makefile
TAXI_ROOT := $(shell git -C $(dir $(lastword $(MAKEFILE_LIST))) rev-parse --show-toplevel)/taxi
RTL_DIR = $(TAXI_ROOT)/src/<module>/rtl
LIB_DIR = $(TAXI_ROOT)/src/<module>/lib
```

Python tests use the same approach:
```python
repo_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
taxi_root = os.path.join(repo_root, 'taxi')
```

## Key Constraints

- **TDD approach**: Tests assume full RyuSim support. Failures are RyuSim bugs, not test issues.
- **No workarounds**: If taxi's RTL uses a valid synthesizable SV construct that RyuSim doesn't support, RyuSim gets fixed.
- **Submodule is read-only**: All modifications live in this repo's `src/` tree.

## Commands

```bash
# Setup
./setup_ryusim.sh

# Run all tests
pytest src/ -v

# Run a single module's tests
pytest src/axis/ -v

# Run a single test via Makefile
cd src/axis/tb/taxi_axis_fifo && make

# Run with waveforms
cd src/axis/tb/taxi_axis_fifo && make WAVES=1

# Re-port tests from taxi submodule (after taxi update)
python scripts/port_tests.py
```

## Dependencies

- RyuSim >= 1.6.0 (install via `curl -fsSL https://ryusim.seiraiyu.com/install.sh | bash`)
- Python 3.10+ with packages from `requirements.txt`
- cocotb from Seiraiyu fork (`pip install git+https://github.com/Seiraiyu/cocotb.git`)
