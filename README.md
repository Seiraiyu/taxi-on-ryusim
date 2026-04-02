# taxi-on-ryusim

Ports all 162 [cocotb](https://www.cocotb.org/) tests from [fpganinja/taxi](https://github.com/fpganinja/taxi) to run on [RyuSim](https://ryusim.seiraiyu.com), validating RyuSim's SystemVerilog compilation and simulation against a production-grade FPGA IP library.

## Overview

The [taxi](https://github.com/fpganinja/taxi) library is a comprehensive FPGA IP collection covering AXI, AXI-Stream, Ethernet, PCIe, DMA, PTP, and more. This repo re-targets its entire test suite to RyuSim, serving as a large-scale regression suite that exercises RyuSim against real-world synthesizable SystemVerilog.

**Modules under test:** apb, axi, axis, cndm, cndm_proto, dma, eth, lfsr, lss, math, pcie, prim, ptp, stats, xfcp, zircon

## Quick Start

```bash
# Clone with submodule
git clone --recurse-submodules https://github.com/<owner>/taxi-on-ryusim.git
cd taxi-on-ryusim

# One-step setup (installs RyuSim + Python deps)
./setup_ryusim.sh

# Run all 162 tests
pytest src/ -v

# Run tests for a single module
pytest src/eth/ -v

# Run a single test via Make
cd src/axis/tb/taxi_axis_fifo && make

# Run with waveform dump
cd src/axis/tb/taxi_axis_fifo && make WAVES=1
```

## Requirements

- **RyuSim** >= 1.5.4
- **Python** >= 3.10
- **cocotb** (Seiraiyu fork)

All Python dependencies are listed in `requirements.txt` and installed by `setup_ryusim.sh`.

## Repository Structure

```
taxi-on-ryusim/
├── taxi/                  # Git submodule — upstream taxi (read-only)
├── src/                   # Ported tests, mirroring taxi's layout
│   ├── axis/tb/...        #   e.g. AXI-Stream tests
│   ├── eth/tb/...         #   e.g. Ethernet tests
│   └── ...                #   16 module directories, 162 tests total
├── scripts/
│   └── port_tests.py      # Re-ports tests after a taxi submodule update
├── setup_ryusim.sh        # One-step environment setup
├── pytest.ini             # Pytest configuration
├── requirements.txt       # Python dependencies
└── .github/workflows/     # CI pipeline (5-way parallel split)
```

Each test directory under `src/` contains:

| File | Description |
|---|---|
| `Makefile` | Copied from taxi, patched to target RyuSim and resolve paths into the submodule |
| `test_*.py` | Cocotb test module, patched to use `simulator="ryusim"` |
| `test_*.sv` | Symlink to the upstream SV testbench wrapper (when present) |

## How It Works

Tests are mechanically ported from taxi using `scripts/port_tests.py`. The script copies each test's Makefile and Python file, then applies a small set of transforms:

1. Sets `SIM ?= ryusim` in the Makefile
2. Redirects source paths to resolve through the `taxi/` submodule via `TAXI_ROOT`
3. Adds RyuSim-specific `-G` parameter blocks for generics
4. Updates the Python test runner to `simulator="ryusim"`

The upstream taxi submodule is never modified. All changes live in `src/`.

## Re-porting After a Taxi Update

```bash
git -C taxi pull origin master
python scripts/port_tests.py
pytest src/ -v
```

## CI

GitHub Actions runs the full suite on every push and PR, split across 5 parallel jobs using `pytest-split` for faster feedback. Results are uploaded as JUnit XML artifacts.

## Philosophy

- **TDD for the simulator**: Tests assume every valid synthesizable SV construct should work. A test failure means a RyuSim bug, not a test bug.
- **No workarounds**: If RyuSim doesn't support a construct that taxi uses, RyuSim gets fixed upstream.
- **Submodule is read-only**: This repo never patches taxi's RTL or testbenches.

## License

See the upstream [taxi repository](https://github.com/fpganinja/taxi) for RTL and original test licensing.
