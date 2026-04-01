# Design: Port fpganinja/taxi Test Suite to RyuSim

**Date:** 2026-04-01
**Status:** Draft
**Goal:** Port all 162 cocotb tests from [fpganinja/taxi](https://github.com/fpganinja/taxi) to run on RyuSim, validating RyuSim's SystemVerilog compilation and simulation against a production-grade FPGA IP library.

---

## 1. Context

### What is taxi?

Taxi is an open-source FPGA IP library (CERN-OHL-S-2.0) with ~20 module families covering AXI, AXI Stream, Ethernet MAC/PHY, DMA, PCIe, LFSR, PTP, APB, XFCP, and more. It includes 162 cocotb-based tests with extensive parameter sweeps, exercising:

- **SystemVerilog interfaces** (`taxi_axis_if`, `taxi_axi_if`, etc.) with modport connections
- **Parameterized modules** with compile-time overrides via Verilator's `-G` flag
- **`.f` file include lists** for recursive source dependency resolution
- **cocotb extensions**: cocotbext-axi, cocotbext-eth, cocotbext-pcie, cocotbext-uart, cocotbext-i2c
- **Protocol-level verification**: AXI transactions, Ethernet frames, PCIe TLPs

### What is RyuSim?

RyuSim (v1.5.4) is a SystemVerilog simulator that compiles synthesizable SV to C++ via Slang parsing + IR + codegen. It integrates with cocotb via VPI (`libryusim_vpi.so`). Key constraints:

- Synthesizable constructs only (no `initial begin`, `#` delays, `fork`/`join`, `$readmemh`)
- Cocotb handles all simulation control (clock, reset, stimulus, termination)
- `-G` parameter override exists as parsed infrastructure (`ParamOption` class) but is not yet wired to Slang's `CompilationOptions::paramOverrides` — will be patched

### Why this port?

The existing RyuSim-Validation suite covers basic cocotb designs, UHDM SV construct tests, and processor benchmarks. Taxi adds a new validation dimension: **real-world IP verification with complex SV interfaces, deep module hierarchies, and protocol-level testing**. Every test failure surfaces a RyuSim gap to fix.

---

## 2. Constraints

- **TDD approach**: Tests are written assuming full RyuSim support. Failures are RyuSim bugs, not test issues.
- **No test modifications for RyuSim compatibility**: If taxi's RTL uses a valid synthesizable SV construct that RyuSim doesn't support, RyuSim gets fixed — the test doesn't get rewritten.
- **Submodule integrity**: The taxi submodule is read-only. All modifications live in this repo's `src/` tree.
- **Seiraiyu cocotb fork required**: The upstream cocotb doesn't have the RyuSim backend. The fork at `github.com/Seiraiyu/cocotb` is required.

---

## 3. Architecture

### Repository layout

```
taxi-on-ryusim/
├── taxi/                              # git submodule → fpganinja/taxi (read-only)
│   └── src/
│       ├── axis/
│       │   ├── rtl/                   # RTL source files
│       │   ├── lib/                   # Library dependencies
│       │   └── tb/
│       │       ├── taxi_axis_fifo/
│       │       │   ├── Makefile       # Original (verilator default)
│       │       │   ├── test_taxi_axis_fifo.py
│       │       │   └── test_taxi_axis_fifo.sv
│       │       └── ...
│       ├── axi/
│       ├── eth/
│       └── ...
│
├── src/                               # Ported tests (mirrors taxi/src/ structure)
│   ├── axis/tb/taxi_axis_fifo/
│   │   ├── Makefile                   # Modified: SIM=ryusim, -G params, adjusted paths
│   │   ├── test_taxi_axis_fifo.py     # Modified: simulator="ryusim"
│   │   └── test_taxi_axis_fifo.sv     # Symlink → taxi/src/axis/tb/taxi_axis_fifo/test_taxi_axis_fifo.sv
│   ├── axis/tb/taxi_axis_adapter/
│   │   └── ...
│   ├── axi/tb/taxi_axi_adapter/
│   │   └── ...
│   ├── eth/tb/taxi_eth_mac_1g/
│   │   └── ...
│   └── ...                            # All 162 test directories
│
├── conftest.py                        # Root pytest config: ryusim fixtures
├── pytest.ini                         # Test discovery, JUnit XML output
├── requirements.txt                   # Python dependencies
├── setup_ryusim.sh                    # RyuSim + environment setup
├── Makefile                           # Top-level: run all/subset of tests
├── CLAUDE.md                          # Agent guidance
├── .gitmodules                        # Submodule config
├── .github/
│   └── workflows/
│       └── regression-tests.yml       # CI pipeline
└── docs/
    └── plans/
        └── 2026-04-01-taxi-port-design.md  # This document
```

### File relationships

For each of the 162 test directories:

| File | Source | Modification |
|------|--------|-------------|
| `Makefile` | Copied from taxi | `SIM ?= ryusim`, paths adjusted to `../../../taxi/src/<module>/rtl`, ryusim `-G` block added |
| `test_*.py` | Copied from taxi | `cocotb_test.simulator.run(simulator="ryusim")`, paths adjusted |
| `test_*.sv` | Symlinked from taxi | None — SV testbenches are simulator-agnostic |

### Path adjustment pattern

Taxi's Makefiles use relative paths:
```makefile
RTL_DIR = ../../rtl          # → taxi/src/<module>/rtl
LIB_DIR = ../../lib          # → taxi/src/<module>/lib
```

Our Makefiles adjust these to reach the submodule:
```makefile
TAXI_ROOT = $(shell git -C $(dir $(lastword $(MAKEFILE_LIST))) rev-parse --show-toplevel)/taxi
RTL_DIR = $(TAXI_ROOT)/src/$(MODULE_FAMILY)/rtl
LIB_DIR = $(TAXI_ROOT)/src/$(MODULE_FAMILY)/lib
```

Or more simply, using relative paths from `src/<module>/tb/<test>/`:
```makefile
RTL_DIR = ../../../../taxi/src/<module>/rtl
LIB_DIR = ../../../../taxi/src/<module>/lib
```

---

## 4. Makefile modifications

Each ported Makefile gets these changes:

### 4.1. Default simulator

```makefile
# Before (taxi original)
SIM ?= verilator

# After (this repo)
SIM ?= ryusim
```

### 4.2. Path adjustments

```makefile
# Before (taxi original)
RTL_DIR = ../../rtl
LIB_DIR = ../../lib
TAXI_SRC_DIR = $(LIB_DIR)/taxi/src

# After (this repo)
TAXI_ROOT = $(abspath $(dir $(lastword $(MAKEFILE_LIST)))../../../../taxi)
RTL_DIR = $(TAXI_ROOT)/src/axis/rtl
LIB_DIR = $(TAXI_ROOT)/src/axis/lib
TAXI_SRC_DIR = $(LIB_DIR)/taxi/src
```

(The exact `$(TAXI_ROOT)/src/<module>/` varies per test directory.)

### 4.3. RyuSim simulator block

Added alongside the existing icarus/verilator blocks:

```makefile
ifeq ($(SIM), ryusim)
    COMPILE_ARGS += $(foreach v,$(filter PARAM_%,$(.VARIABLES)),-G$(subst PARAM_,,$(v))=$($(v)))

    ifeq ($(WAVES), 1)
        COMPILE_ARGS += --trace-fst
    endif
endif
```

The `-G` flag maps directly to Verilator's convention. The cocotb `Makefile.ryusim` passes `COMPILE_ARGS` through to `ryusim compile`.

### 4.4. Filelist (.f) processing

The `.f` file processing macros are preserved unchanged — they expand `.f` files into flat source lists, which are simulator-agnostic.

---

## 5. Python test modifications

Each `test_*.py` file is copied and modified:

### 5.1. Simulator change in cocotb_test.simulator.run()

```python
# Before (taxi original)
cocotb_test.simulator.run(
    simulator="verilator",
    ...
)

# After (this repo)
cocotb_test.simulator.run(
    simulator="ryusim",
    ...
)
```

### 5.2. Path adjustments

```python
# Before (taxi original)
tests_dir = os.path.dirname(__file__)
rtl_dir = os.path.abspath(os.path.join(tests_dir, '..', '..', 'rtl'))
lib_dir = os.path.abspath(os.path.join(tests_dir, '..', '..', 'lib'))

# After (this repo)
tests_dir = os.path.dirname(__file__)
taxi_root = os.path.abspath(os.path.join(tests_dir, '..', '..', '..', '..', 'taxi'))
rtl_dir = os.path.abspath(os.path.join(taxi_root, 'src', '<module>', 'rtl'))
lib_dir = os.path.abspath(os.path.join(taxi_root, 'src', '<module>', 'lib'))
```

### 5.3. Cocotb test functions (unchanged)

The async cocotb test functions (`@cocotb.test()`, `TestFactory`, etc.) are **not modified**. They are simulator-agnostic and run identically on any backend.

---

## 6. Dependencies

### requirements.txt

```
cocotb @ git+https://github.com/Seiraiyu/cocotb.git
cocotb-bus==0.2.1
cocotb-test==0.2.6
cocotbext-axi==0.1.28
cocotbext-eth==0.1.22
cocotbext-i2c==0.1.2
cocotbext-pcie==0.2.16
cocotbext-uart==0.1.4
pytest==8.3.4
pytest-xdist==3.6.1
scapy==2.6.1
```

### System requirements

| Tool | Version | Purpose |
|------|---------|---------|
| RyuSim | >= 1.5.4 | Simulator under test |
| Python | >= 3.10 | cocotb + test runner |
| GNU Make | any | Per-test build system |
| git | any | Submodule management |

---

## 7. Root pytest configuration

### conftest.py

```python
"""Root conftest.py for taxi-on-ryusim validation."""
import shutil
import subprocess
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--ryusim-version", action="store", default=None,
        help="Expected RyuSim version string",
    )


@pytest.fixture(scope="session")
def ryusim_bin():
    """Return path to ryusim binary, skip session if not found."""
    path = shutil.which("ryusim")
    if path is None:
        pytest.skip("ryusim not found in PATH")
    return path


@pytest.fixture(scope="session")
def ryusim_version(ryusim_bin, request):
    """Return installed RyuSim version string."""
    result = subprocess.run(
        [ryusim_bin, "--version"], capture_output=True, text=True,
    )
    version = result.stdout.strip()
    expected = request.config.getoption("--ryusim-version")
    if expected and version != expected:
        pytest.fail(f"RyuSim version mismatch: got {version!r}, expected {expected!r}")
    return version
```

### pytest.ini

```ini
[pytest]
testpaths = src
python_files = test_*.py
python_functions = test_*
addopts = --junitxml=results/junit.xml -v
```

---

## 8. CI Pipeline

### .github/workflows/regression-tests.yml

```yaml
name: Taxi Regression Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-24.04
    strategy:
      fail-fast: false
      matrix:
        group: [1, 2, 3, 4, 5]  # Adjust based on test count/duration
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Install RyuSim
        run: |
          curl -fsSL https://ryusim.seiraiyu.com/install.sh | bash
          echo "$HOME/.ryusim/bin" >> $GITHUB_PATH

      - name: Install Python dependencies
        run: pip install -r requirements.txt

      - name: Run tests (group ${{ matrix.group }})
        run: |
          pytest src/ \
            --junitxml=results/junit-${{ matrix.group }}.xml \
            -v \
            --splits ${{ strategy.job-total }} \
            --group ${{ matrix.group }} \
            --splitting-algorithm least_duration

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results-${{ matrix.group }}
          path: results/
```

---

## 9. Setup script

### setup_ryusim.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Setting up taxi-on-ryusim ==="

# 1. Initialize submodule
git submodule update --init --recursive

# 2. Install RyuSim
if ! command -v ryusim &>/dev/null; then
    echo "Installing RyuSim..."
    curl -fsSL https://ryusim.seiraiyu.com/install.sh | bash
    export PATH="$HOME/.ryusim/bin:$PATH"
fi
echo "RyuSim: $(ryusim --version)"

# 3. Install Python dependencies
pip install -r requirements.txt
echo "cocotb: $(python -c 'import cocotb; print(cocotb.__version__)')"

echo "=== Setup complete ==="
```

---

## 10. Test module inventory

All 162 tests to port, grouped by module family:

| Module | Tests | Key SV features exercised |
|--------|-------|--------------------------|
| **axis** | ~16 | SV interfaces (`taxi_axis_if`), parameterized FIFOs, mux/demux, encoders |
| **axi** | ~20 | SV interfaces (`taxi_axi_if`), crossbars, interconnect, RAM |
| **eth** | ~30 | Ethernet MAC/PHY, GMII/RGMII/XGMII, 10G/25G, BASE-R encoding |
| **dma** | ~12 | AXI DMA engines, streaming clients, PCIe interfaces |
| **pcie** | ~6 | AXI-Lite masters, MSI/MSI-X controllers |
| **lfsr** | ~6 | CRC, PRBS generators/checkers, scramblers |
| **ptp** | ~6 | PTP clocks, CDC, time distribution |
| **xfcp** | ~6 | Control platform, bus switching, arbitration |
| **apb** | ~6 | APB adapters, interconnect, RAM |
| **lss** | ~6 | UART, I2C master/slave, MDIO |
| **stats** | ~3 | Statistics counters and collectors |
| **zircon** | ~3 | IP/UDP processing, checksums |
| **prim** | ~3 | Arbiters, primitives |
| **sync** | ~3 | Clock domain crossing |
| **eth examples** | ~27 | Board-level integration (Alveo, ZCU, KC705, Arty, etc.) |

---

## 11. Error handling

### Compilation failures

When `ryusim compile` fails on a taxi design, the error is a RyuSim gap. The pytest test reports FAIL with the compilation stderr. No workarounds — file a RyuSim issue.

### Simulation mismatches

When cocotb assertions fail, it indicates a simulation behavior difference. The JUnit XML captures the assertion details. No expected-fail markers.

### Missing `-G` support

Until RyuSim wires up `-G` parameter overrides, tests that rely on non-default parameters will fail at compilation. The Makefile-only tests (using default parameters) may still pass. This is the first thing to unblock.

---

## 12. Phase tracking

| Phase | Description | Status | Tested | Pushed |
|-------|-------------|--------|--------|--------|
| 1 | Repo scaffolding: git init, submodule, CLAUDE.md, requirements.txt, setup script, conftest.py, pytest.ini | pending | no | no |
| 2 | Port AXIS tests (~16 tests): Makefiles, Python tests, SV symlinks | pending | no | no |
| 3 | Port AXI tests (~20 tests) | pending | no | no |
| 4 | Port ETH tests (~30 tests) | pending | no | no |
| 5 | Port DMA tests (~12 tests) | pending | no | no |
| 6 | Port remaining modules (PCIe, LFSR, PTP, XFCP, APB, LSS, stats, zircon, prim, sync) (~50 tests) | pending | no | no |
| 7 | Port ETH example tests (~27 tests) | pending | no | no |
| 8 | CI pipeline: GitHub Actions workflow | pending | no | no |
| 9 | Run full suite, triage failures, file RyuSim issues | pending | no | no |

---

## 13. Decisions log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| RTL source management | Git submodule | Stays in sync with upstream, standard pattern |
| Test scope | All 162 tests | Maximize validation coverage |
| Parameter passing | `-G` flag (TDD) | Matches Verilator convention, ryusim will add support |
| SV interface handling | No workarounds | ryusim adapts to support taxi's SV patterns |
| Python test strategy | Copy + modify | Change `simulator="ryusim"` and paths |
| SV testbench strategy | Symlink from submodule | Zero duplication, simulator-agnostic files |
| Failure tracking | pytest + JUnit XML | Standard, CI-friendly, no xfail markers |
| Directory layout | Mirror taxi structure | 1:1 mapping for easy cross-reference |
| Dependencies | requirements.txt with cocotb fork | Explicit, reproducible |
| CI | Include in initial design | Full automation from the start |
