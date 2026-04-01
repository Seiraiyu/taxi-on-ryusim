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
