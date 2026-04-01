# Taxi-on-RyuSim Implementation Plan

**Goal:** Port all 162 cocotb tests from fpganinja/taxi to run on RyuSim, using an automated porting script to transform Makefiles and Python tests.
**Architecture:** Git submodule for taxi RTL (read-only). Mirror directory structure in `src/`. Porting script automates Makefile/Python transformations and SV symlinks. CI runs full suite with JUnit XML reporting.
**Tech Stack:** Python 3.10+, cocotb (Seiraiyu fork), RyuSim >= 1.5.4, GNU Make, pytest, GitHub Actions

---

| Task | Description | Status | Tested | Pushed |
|------|-------------|--------|--------|--------|
| 1 | Add taxi as git submodule | pending | no | no |
| 2 | Create .gitignore | pending | no | no |
| 3 | Create requirements.txt | pending | no | no |
| 4 | Create setup_ryusim.sh | pending | no | no |
| 5 | Create conftest.py | pending | no | no |
| 6 | Create pytest.ini | pending | no | no |
| 7 | Create CLAUDE.md | pending | no | no |
| 8 | Create top-level Makefile | pending | no | no |
| 9 | Commit scaffolding | pending | no | no |
| 10 | Build porting script (scripts/port_tests.py) | pending | no | no |
| 11 | Run porting script to generate all 162 test dirs | pending | no | no |
| 12 | Verify: run one AXIS test with SIM=ryusim via Makefile | pending | no | no |
| 13 | Commit all ported tests | pending | no | no |
| 14 | Create CI workflow (.github/workflows/regression-tests.yml) | pending | no | no |
| 15 | Commit CI | pending | no | no |

---

### Task 1: Add taxi as git submodule

**Files:**
- Create: `.gitmodules`
- Create: `taxi/` (submodule checkout)

**Step 1: Add submodule**
Run:
```bash
cd /home/stonelyd/taxi-on-ryusim
git submodule add https://github.com/fpganinja/taxi.git taxi
```
Expected: `taxi/` directory appears with full taxi repo, `.gitmodules` created.

**Step 2: Verify submodule**
Run:
```bash
ls taxi/src/axis/tb/taxi_axis_fifo/Makefile
```
Expected: File exists.

---

### Task 2: Create .gitignore

**Files:**
- Create: `.gitignore`

**Step 1: Write file**
```
# Simulation artifacts
sim_build/
obj_dir/
__pycache__/
*.pyc

# Waveforms
*.vcd
*.fst

# Test results
results/
*.xml

# cocotb
results.xml

# Editor
*.swp
*.swo
*~
.vscode/
.idea/

# OS
.DS_Store
```

---

### Task 3: Create requirements.txt

**Files:**
- Create: `requirements.txt`

**Step 1: Write file**
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
pytest-split==0.10.0
scapy==2.6.1
```

---

### Task 4: Create setup_ryusim.sh

**Files:**
- Create: `setup_ryusim.sh`

**Step 1: Write file**
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

**Step 2: Make executable**
Run:
```bash
chmod +x setup_ryusim.sh
```

---

### Task 5: Create conftest.py

**Files:**
- Create: `conftest.py`

**Step 1: Write file**
```python
"""Root conftest.py for taxi-on-ryusim validation."""

import shutil
import subprocess

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--ryusim-version",
        action="store",
        default=None,
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
        [ryusim_bin, "--version"],
        capture_output=True,
        text=True,
    )
    version = result.stdout.strip()
    expected = request.config.getoption("--ryusim-version")
    if expected and version != expected:
        pytest.fail(f"RyuSim version mismatch: got {version!r}, expected {expected!r}")
    return version
```

---

### Task 6: Create pytest.ini

**Files:**
- Create: `pytest.ini`

**Step 1: Write file**
```ini
[pytest]
testpaths = src
python_files = test_*.py
python_functions = test_*
addopts = --junitxml=results/junit.xml -v
```

---

### Task 7: Create CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

**Step 1: Write file**
```markdown
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

- RyuSim >= 1.5.4 (install via `curl -fsSL https://ryusim.seiraiyu.com/install.sh | bash`)
- Python 3.10+ with packages from `requirements.txt`
- cocotb from Seiraiyu fork (`pip install git+https://github.com/Seiraiyu/cocotb.git`)
```

---

### Task 8: Create top-level Makefile

**Files:**
- Create: `Makefile`

**Step 1: Write file**
```makefile
# Top-level Makefile for taxi-on-ryusim
.PHONY: all test clean setup

all: test

setup:
	./setup_ryusim.sh

test:
	pytest src/ -v --junitxml=results/junit.xml

clean:
	find src/ -name sim_build -type d -exec rm -rf {} + 2>/dev/null || true
	find src/ -name obj_dir -type d -exec rm -rf {} + 2>/dev/null || true
	find src/ -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find src/ -name results.xml -delete 2>/dev/null || true
	find src/ -name "*.fst" -delete 2>/dev/null || true
	find src/ -name "*.vcd" -delete 2>/dev/null || true
	rm -rf results/
```

---

### Task 9: Commit scaffolding

**Step 1: Stage and commit**
Run:
```bash
cd /home/stonelyd/taxi-on-ryusim
git add .gitmodules taxi .gitignore requirements.txt setup_ryusim.sh conftest.py pytest.ini CLAUDE.md Makefile
git commit -m "Add repo scaffolding: submodule, deps, pytest config, setup script

- Add fpganinja/taxi as git submodule for RTL source
- Add requirements.txt with Seiraiyu cocotb fork and extensions
- Add conftest.py with ryusim session fixtures
- Add pytest.ini for test discovery and JUnit XML output
- Add setup_ryusim.sh for environment setup
- Add CLAUDE.md with project documentation
- Add top-level Makefile for test/clean targets

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Build porting script (scripts/port_tests.py)

This is the core automation. The script walks the taxi submodule, discovers all 162 test directories, and generates the ported versions.

**Files:**
- Create: `scripts/port_tests.py`

**Step 1: Write the complete porting script**

```python
#!/usr/bin/env python3
"""Port all taxi cocotb tests to run on RyuSim.

Walks the taxi/ submodule, discovers test directories (containing Makefile +
test_*.py), and generates ported versions in src/ with:
  - Makefiles: SIM=ryusim, paths into taxi submodule, ryusim -G block
  - Python tests: simulator="ryusim", paths into taxi submodule
  - SV testbenches: symlinked from taxi submodule
"""

import argparse
import glob
import os
import re
import stat
import subprocess
import sys
from pathlib import Path


def find_repo_root():
    """Find the git repo root."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return Path(result.stdout.strip())


def find_test_dirs(taxi_root: Path) -> list[Path]:
    """Find all test directories in the taxi submodule.

    A test directory contains at least a Makefile and a test_*.py file.
    """
    test_dirs = []
    for makefile in sorted(taxi_root.rglob("Makefile")):
        test_dir = makefile.parent
        py_files = list(test_dir.glob("test_*.py"))
        if py_files:
            test_dirs.append(test_dir)
    return test_dirs


def get_module_parent(test_dir: Path, taxi_src: Path) -> str:
    """Determine the module parent path for RTL_DIR/LIB_DIR resolution.

    Given a test dir like taxi/src/axis/tb/taxi_axis_fifo/, the module parent
    is "axis" (the dir containing both tb/ and rtl/).

    For deeper paths like taxi/src/cndm/board/VCU118/fpga/tb/fpga_core/,
    the module parent is "cndm/board/VCU118/fpga".

    The rule: find the "tb" component in the path and take everything
    between src/ and tb/.
    """
    rel = test_dir.relative_to(taxi_src)
    parts = rel.parts
    # Find the 'tb' directory in the path
    for i, part in enumerate(parts):
        if part == "tb":
            return str(Path(*parts[:i]))
    raise ValueError(f"No 'tb' directory found in path: {test_dir}")


def transform_makefile(content: str, module_parent: str) -> str:
    """Transform a taxi Makefile for ryusim.

    Changes:
    1. SIM ?= verilator  →  SIM ?= ryusim
    2. RTL_DIR = ../../rtl  →  RTL_DIR = $(TAXI_ROOT)/src/<parent>/rtl
    3. LIB_DIR = ../../lib  →  LIB_DIR = $(TAXI_ROOT)/src/<parent>/lib
    4. Insert TAXI_ROOT computation after COCOTB_HDL_TIMEPRECISION
    5. Add ryusim block alongside icarus/verilator blocks
    6. Remove VERILATOR_TRACE references
    """
    lines = content.split("\n")
    result = []
    taxi_root_inserted = False
    in_sim_block = False
    last_sim_block_end = -1

    for i, line in enumerate(lines):
        # 1. Change default simulator
        if re.match(r"^SIM\s*\?=\s*verilator", line):
            result.append("SIM ?= ryusim")
            continue

        # 2. Insert TAXI_ROOT after COCOTB_HDL_TIMEPRECISION
        if not taxi_root_inserted and "COCOTB_HDL_TIMEPRECISION" in line:
            result.append(line)
            result.append("")
            result.append("TAXI_ROOT := $(shell git -C $(dir $(lastword $(MAKEFILE_LIST))) rev-parse --show-toplevel)/taxi")
            taxi_root_inserted = True
            continue

        # 3. Replace RTL_DIR
        if re.match(r"^RTL_DIR\s*=\s*\.\./\.\./rtl", line):
            result.append(f"RTL_DIR = $(TAXI_ROOT)/src/{module_parent}/rtl")
            continue

        # 4. Replace LIB_DIR
        if re.match(r"^LIB_DIR\s*=\s*\.\./\.\./lib", line):
            result.append(f"LIB_DIR = $(TAXI_ROOT)/src/{module_parent}/lib")
            continue

        # 5. Remove TAXI_SRC_DIR if present (it derives from LIB_DIR which now
        #    points into the submodule, and the submodule's lib/ has the
        #    taxi symlink, so TAXI_SRC_DIR still works)
        # Actually, keep it — it still works because LIB_DIR points into taxi/

        result.append(line)

    # 6. Add ryusim block: find the last simulator block and add after it
    content_out = "\n".join(result)

    # Find the include line and insert ryusim block before it
    ryusim_block = (
        "else ifeq ($(SIM), ryusim)\n"
        "\tCOMPILE_ARGS += $(foreach v,$(filter PARAM_%,$(.VARIABLES)),-G$(subst PARAM_,,$(v))=$($(v)))\n"
        "\n"
        "\tifeq ($(WAVES), 1)\n"
        "\t\tCOMPILE_ARGS += --trace-fst\n"
        "\tendif\n"
    )

    # Insert ryusim block before the final 'endif' that precedes the include
    # Pattern: find the last 'endif' before 'include $(shell cocotb-config'
    include_pattern = r"include \$\(shell cocotb-config"
    include_match = re.search(include_pattern, content_out)
    if include_match:
        # Find the 'endif' before the include
        before_include = content_out[:include_match.start()]
        last_endif = before_include.rfind("endif")
        if last_endif != -1:
            # Insert ryusim block before the endif
            content_out = (
                content_out[:last_endif]
                + ryusim_block
                + content_out[last_endif:]
            )

    return content_out


def transform_python(content: str, module_parent: str) -> str:
    """Transform a taxi Python test file for ryusim.

    Changes:
    1. simulator="verilator"  →  simulator="ryusim"
    2. Replace rtl_dir/lib_dir path computation to use taxi submodule
    3. Add subprocess import if needed for git rev-parse
    """
    # 1. Change simulator
    content = content.replace('simulator="verilator"', 'simulator="ryusim"')
    content = content.replace("simulator='verilator'", "simulator='ryusim'")

    # 2. Replace rtl_dir path computation
    # Original pattern:
    #   rtl_dir = os.path.abspath(os.path.join(tests_dir, '..', '..', 'rtl'))
    # New pattern:
    #   _repo_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
    #   _taxi_root = os.path.join(_repo_root, 'taxi')
    #   rtl_dir = os.path.join(_taxi_root, 'src', '<parent>', 'rtl')

    parent_parts = module_parent.split("/")
    parent_join = ", ".join(f"'{p}'" for p in parent_parts)

    # Add subprocess import if not present
    if "import subprocess" not in content and "from subprocess" not in content:
        # Insert after the last 'import' line in the top-level imports
        # Find a good insertion point
        if "import os" in content:
            content = content.replace(
                "import os\n",
                "import os\nimport subprocess\n",
                1,
            )

    # Replace rtl_dir computation
    old_rtl = re.compile(
        r"rtl_dir\s*=\s*os\.path\.abspath\(os\.path\.join\(tests_dir,\s*'\.\.'\s*,\s*'\.\.'\s*,\s*'rtl'\)\)"
    )
    new_rtl = (
        f"_repo_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()\n"
        f"_taxi_root = os.path.join(_repo_root, 'taxi')\n"
        f"rtl_dir = os.path.join(_taxi_root, 'src', {parent_join}, 'rtl')"
    )
    content = old_rtl.sub(new_rtl, content)

    # Replace lib_dir computation
    old_lib = re.compile(
        r"lib_dir\s*=\s*os\.path\.abspath\(os\.path\.join\(tests_dir,\s*'\.\.'\s*,\s*'\.\.'\s*,\s*'lib'\)\)"
    )
    new_lib = f"lib_dir = os.path.join(_taxi_root, 'src', {parent_join}, 'lib')"
    content = old_lib.sub(new_lib, content)

    # Also handle taxi_src_dir if present
    old_taxi_src = re.compile(
        r"taxi_src_dir\s*=\s*os\.path\.abspath\(os\.path\.join\(lib_dir,\s*'taxi'\s*,\s*'src'\)\)"
    )
    new_taxi_src = "taxi_src_dir = os.path.join(lib_dir, 'taxi', 'src')"
    content = old_taxi_src.sub(new_taxi_src, content)

    return content


def port_test(taxi_test_dir: Path, repo_root: Path, dry_run: bool = False) -> dict:
    """Port a single test directory from taxi to this repo.

    Returns a dict with stats about what was done.
    """
    taxi_root = repo_root / "taxi"
    taxi_src = taxi_root / "src"
    rel_path = taxi_test_dir.relative_to(taxi_src)
    dest_dir = repo_root / "src" / rel_path
    module_parent = get_module_parent(taxi_test_dir, taxi_src)

    stats = {"dir": str(rel_path), "makefile": False, "python": [], "sv_symlinks": []}

    if dry_run:
        print(f"  [DRY RUN] Would create: src/{rel_path}/")
        return stats

    dest_dir.mkdir(parents=True, exist_ok=True)

    # 1. Transform Makefile
    makefile_src = taxi_test_dir / "Makefile"
    if makefile_src.exists():
        content = makefile_src.read_text()
        transformed = transform_makefile(content, module_parent)
        (dest_dir / "Makefile").write_text(transformed)
        stats["makefile"] = True

    # 2. Transform Python test files
    for py_file in sorted(taxi_test_dir.glob("test_*.py")):
        content = py_file.read_text()
        transformed = transform_python(content, module_parent)
        (dest_dir / py_file.name).write_text(transformed)
        stats["python"].append(py_file.name)

    # 3. Symlink SV testbench files
    for sv_file in sorted(taxi_test_dir.glob("test_*.sv")):
        symlink_path = dest_dir / sv_file.name
        # Compute relative path from dest_dir to sv_file
        target = os.path.relpath(sv_file, dest_dir)
        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()
        symlink_path.symlink_to(target)
        stats["sv_symlinks"].append(sv_file.name)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Port taxi cocotb tests to RyuSim")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--module", type=str, help="Only port tests for this module (e.g., 'axis')")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    repo_root = find_repo_root()
    taxi_root = repo_root / "taxi"
    taxi_src = taxi_root / "src"

    if not taxi_src.exists():
        print("ERROR: taxi submodule not found. Run: git submodule update --init --recursive")
        sys.exit(1)

    print(f"Repo root: {repo_root}")
    print(f"Taxi root: {taxi_root}")
    print()

    test_dirs = find_test_dirs(taxi_src)
    print(f"Found {len(test_dirs)} test directories in taxi/src/")

    if args.module:
        test_dirs = [d for d in test_dirs if d.relative_to(taxi_src).parts[0] == args.module]
        print(f"Filtered to {len(test_dirs)} tests for module '{args.module}'")

    print()

    total_makefiles = 0
    total_python = 0
    total_symlinks = 0

    for test_dir in test_dirs:
        rel = test_dir.relative_to(taxi_src)
        if args.verbose or args.dry_run:
            print(f"Porting: {rel}")

        stats = port_test(test_dir, repo_root, dry_run=args.dry_run)
        if stats["makefile"]:
            total_makefiles += 1
        total_python += len(stats["python"])
        total_symlinks += len(stats["sv_symlinks"])

    print()
    print(f"Done! Ported {len(test_dirs)} test directories:")
    print(f"  Makefiles:    {total_makefiles}")
    print(f"  Python tests: {total_python}")
    print(f"  SV symlinks:  {total_symlinks}")


if __name__ == "__main__":
    main()
```

**Step 2: Make executable**
Run:
```bash
mkdir -p scripts
chmod +x scripts/port_tests.py
```

---

### Task 11: Run porting script to generate all 162 test dirs

**Step 1: Run the script**
Run:
```bash
cd /home/stonelyd/taxi-on-ryusim
python scripts/port_tests.py -v
```
Expected output (approximately):
```
Repo root: /home/stonelyd/taxi-on-ryusim
Taxi root: /home/stonelyd/taxi-on-ryusim/taxi

Found 162 test directories in taxi/src/
Porting: apb/tb/taxi_apb_adapter
Porting: apb/tb/taxi_apb_axil_adapter
...
Porting: zircon/tb/zircon_ip_tx_deparse

Done! Ported 162 test directories:
  Makefiles:    162
  Python tests: 162
  SV symlinks:  ~95
```

**Step 2: Verify directory count**
Run:
```bash
find src/ -name Makefile | wc -l
```
Expected: `162`

**Step 3: Verify symlinks**
Run:
```bash
find src/ -type l -name "*.sv" | head -5
```
Expected: symlinks pointing into `../../../../../../taxi/src/...`

**Step 4: Verify Makefile transformation**
Run:
```bash
head -25 src/axis/tb/taxi_axis_fifo/Makefile
```
Expected: Should show `SIM ?= ryusim`, `TAXI_ROOT := ...`, adjusted `RTL_DIR`.

**Step 5: Verify Python transformation**
Run:
```bash
grep -n "simulator=" src/axis/tb/taxi_axis_fifo/test_taxi_axis_fifo.py | head -3
```
Expected: `simulator="ryusim"`

**Step 6: Spot-check a deeply nested test**
Run:
```bash
head -20 src/cndm/board/VCU118/fpga/tb/fpga_core/Makefile
```
Expected: `SIM ?= ryusim`, `RTL_DIR = $(TAXI_ROOT)/src/cndm/board/VCU118/fpga/rtl`

---

### Task 12: Verify — run one AXIS test with SIM=ryusim via Makefile

**Step 1: Run a simple test**
Run:
```bash
cd /home/stonelyd/taxi-on-ryusim/src/axis/tb/taxi_axis_fifo
make SIM=ryusim 2>&1 | tail -20
```
Expected: Either passes (RyuSim handles everything) or fails with a specific RyuSim compilation/simulation error. Either outcome is valid — this is TDD. The test infrastructure is confirmed working.

**Step 2: If compilation fails, verify it's a RyuSim issue**
Run:
```bash
cd /home/stonelyd/taxi-on-ryusim/src/axis/tb/taxi_axis_fifo
make SIM=verilator 2>&1 | tail -5
```
Expected: Passes on Verilator (confirming the test is correct and only RyuSim has the gap).

---

### Task 13: Commit all ported tests

**Step 1: Stage and commit**
Run:
```bash
cd /home/stonelyd/taxi-on-ryusim
git add scripts/ src/
git commit -m "Port all 162 taxi cocotb tests to RyuSim

Add scripts/port_tests.py automation that transforms:
- Makefiles: SIM=ryusim default, TAXI_ROOT path resolution into
  submodule, -G parameter passing block for ryusim
- Python tests: simulator='ryusim', path adjustments for submodule
- SV testbenches: symlinked from taxi submodule (read-only)

Test directories mirror taxi/src/ structure exactly.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 14: Create CI workflow

**Files:**
- Create: `.github/workflows/regression-tests.yml`

**Step 1: Write workflow**
```yaml
name: Taxi Regression Tests

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-24.04
    strategy:
      fail-fast: false
      matrix:
        group: [1, 2, 3, 4, 5]
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install RyuSim
        run: |
          curl -fsSL https://ryusim.seiraiyu.com/install.sh | bash
          echo "$HOME/.ryusim/bin" >> $GITHUB_PATH

      - name: Verify RyuSim
        run: ryusim --version

      - name: Install Python dependencies
        run: pip install -r requirements.txt

      - name: Run tests (group ${{ matrix.group }})
        run: |
          mkdir -p results
          pytest src/ \
            --junitxml=results/junit-${{ matrix.group }}.xml \
            -v \
            --splits 5 \
            --group ${{ matrix.group }} \
            --splitting-algorithm least_duration \
            || true

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results-${{ matrix.group }}
          path: results/
```

Note: `|| true` on the pytest command because we expect failures (TDD approach — RyuSim gaps will cause failures). CI should still report results even when tests fail.

---

### Task 15: Commit CI

**Step 1: Stage and commit**
Run:
```bash
cd /home/stonelyd/taxi-on-ryusim
mkdir -p .github/workflows
git add .github/workflows/regression-tests.yml
git commit -m "Add CI pipeline for taxi regression tests

GitHub Actions workflow with 5-way parallel split. Installs RyuSim
and Seiraiyu cocotb fork, runs full test suite, publishes JUnit XML
artifacts. Uses || true since failures are expected (TDD for RyuSim
validation).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Porting Script Design Notes

### Pattern detection

The script discovers test directories by finding all directories containing both a `Makefile` and a `test_*.py` file under `taxi/src/`. This catches all 162 tests regardless of nesting depth.

### Module parent computation

The "module parent" is the path between `src/` and `tb/` in the test directory path:

| Test path | Module parent |
|-----------|--------------|
| `src/axis/tb/taxi_axis_fifo/` | `axis` |
| `src/axi/tb/taxi_axi_adapter/` | `axi` |
| `src/cndm/board/VCU118/fpga/tb/fpga_core/` | `cndm/board/VCU118/fpga` |
| `src/eth/example/Arty/fpga/tb/fpga_core/` | `eth/example/Arty/fpga` |

This determines where `RTL_DIR` and `LIB_DIR` point in the taxi submodule.

### Makefile transformation rules

1. `SIM ?= verilator` → `SIM ?= ryusim`
2. Insert `TAXI_ROOT` computation after `COCOTB_HDL_TIMEPRECISION`
3. `RTL_DIR = ../../rtl` → `RTL_DIR = $(TAXI_ROOT)/src/<parent>/rtl`
4. `LIB_DIR = ../../lib` → `LIB_DIR = $(TAXI_ROOT)/src/<parent>/lib`
5. `TAXI_SRC_DIR` left unchanged (derives from LIB_DIR; taxi submodule's lib/ has the taxi symlink)
6. `.f` file processing macros left unchanged (simulator-agnostic)
7. All `PARAM_*` exports left unchanged
8. icarus/verilator blocks left unchanged
9. New `ryusim` block added before final `endif`: `-G` parameter passing + `--trace-fst`

### Python transformation rules

1. `simulator="verilator"` → `simulator="ryusim"`
2. `rtl_dir = os.path.abspath(os.path.join(tests_dir, '..', '..', 'rtl'))` → uses `git rev-parse` + taxi_root
3. `lib_dir` same treatment
4. `import subprocess` added if not present
5. All cocotb test functions left unchanged (simulator-agnostic)
6. `process_f_files()` helper left unchanged

### SV symlink computation

For each `test_*.sv` in the taxi test dir, create a relative symlink from `src/<path>/test_*.sv` → `taxi/src/<path>/test_*.sv`. The symlink uses `os.path.relpath()` for portability.
