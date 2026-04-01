#!/usr/bin/env python3
"""Port all taxi cocotb tests to run on RyuSim.

Walks the taxi/ submodule, discovers test directories (containing Makefile +
test_*.py), and generates ported versions in src/ with:
  - Makefiles: SIM=ryusim, paths into taxi submodule, ryusim -G block
  - Python tests: simulator="ryusim", paths into taxi submodule
  - SV testbenches: symlinked from taxi submodule
"""

import argparse
import os
import re
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

    For deeper paths like taxi/src/eth/example/ADM_PCIE_9V3/fpga/tb/fpga_core/,
    the module parent is "eth/example/ADM_PCIE_9V3/fpga".

    The rule: find the "tb" component in the path and take everything
    between src/ and tb/.
    """
    rel = test_dir.relative_to(taxi_src)
    parts = rel.parts
    for i, part in enumerate(parts):
        if part == "tb":
            return str(Path(*parts[:i]))
    raise ValueError(f"No 'tb' directory found in path: {test_dir}")


def transform_makefile(content: str, module_parent: str) -> str:
    """Transform a taxi Makefile for ryusim.

    Changes:
    1. SIM ?= verilator  ->  SIM ?= ryusim
    2. Insert TAXI_ROOT computation after COCOTB_HDL_TIMEPRECISION
    3. RTL_DIR = ../../rtl  ->  RTL_DIR = $(TAXI_ROOT)/src/<parent>/rtl
    4. LIB_DIR = ../../lib  ->  LIB_DIR = $(TAXI_ROOT)/src/<parent>/lib
    5. Add ryusim block alongside icarus/verilator blocks
    """
    lines = content.split("\n")
    result = []
    taxi_root_inserted = False

    for line in lines:
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

        result.append(line)

    # 5. Add ryusim block: insert before the final 'endif' that precedes the include
    content_out = "\n".join(result)

    ryusim_block = (
        "else ifeq ($(SIM), ryusim)\n"
        "\tCOMPILE_ARGS += $(foreach v,$(filter PARAM_%,$(.VARIABLES)),-G$(subst PARAM_,,$(v))=$($(v)))\n"
        "\n"
        "\tifeq ($(WAVES), 1)\n"
        "\t\tCOMPILE_ARGS += --trace-fst\n"
        "\tendif\n"
    )

    include_pattern = r"include \$\(shell cocotb-config"
    include_match = re.search(include_pattern, content_out)
    if include_match:
        before_include = content_out[:include_match.start()]
        last_endif = before_include.rfind("endif")
        if last_endif != -1:
            content_out = (
                content_out[:last_endif]
                + ryusim_block
                + content_out[last_endif:]
            )

    return content_out


def transform_python(content: str, module_parent: str) -> str:
    """Transform a taxi Python test file for ryusim.

    Changes:
    1. simulator="verilator"  ->  simulator="ryusim"
    2. Replace rtl_dir/lib_dir path computation to use taxi submodule
    3. Add subprocess import if needed for git rev-parse
    """
    # 1. Change simulator
    content = content.replace('simulator="verilator"', 'simulator="ryusim"')
    content = content.replace("simulator='verilator'", "simulator='ryusim'")

    # 2. Replace rtl_dir path computation
    parent_parts = module_parent.split("/")
    parent_join = ", ".join(f"'{p}'" for p in parent_parts)

    # Add subprocess import if not present
    if "import subprocess" not in content and "from subprocess" not in content:
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
