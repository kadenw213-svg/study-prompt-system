"""Dependency detection/installation for the audio-lectures skill.

Nothing here runs automatically on import -- `check()` only inspects the
environment, and `install_commands()` only returns strings for the calling
skill session to actually execute (one at a time, as its own visible
Bash/PowerShell tool call, the same way every other install in this
project happens) rather than this module silently shelling out on its
own. See docs/setup.md for exactly what each dependency is for and why.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from dataclasses import dataclass, field

_REQUIRED_PACKAGES = ["torch", "kokoro", "soundfile", "numpy"]
_REQUIRED_BINARIES = ["ffmpeg", "espeak-ng"]


@dataclass
class DependencyReport:
    missing_python_packages: list[str] = field(default_factory=list)
    missing_binaries: list[str] = field(default_factory=list)
    cuda_available: bool | None = None  # None = torch itself isn't installed yet, so unknown

    @property
    def is_complete(self) -> bool:
        return not self.missing_python_packages and not self.missing_binaries


def check() -> DependencyReport:
    report = DependencyReport()
    for package_name in _REQUIRED_PACKAGES:
        if importlib.util.find_spec(package_name) is None:
            report.missing_python_packages.append(package_name)
    for binary in _REQUIRED_BINARIES:
        if shutil.which(binary) is None:
            report.missing_binaries.append(binary)
    if "torch" not in report.missing_python_packages:
        import torch

        report.cuda_available = torch.cuda.is_available()
    return report


def install_commands(report: DependencyReport) -> list[str]:
    """Human-auditable shell commands to close every gap in `report`. The
    calling skill session runs each one as its own visible tool call (per
    this project's norm of confirming/showing hard-to-reverse or
    system-affecting actions) rather than this function running them
    itself -- see docs/setup.md for what each command actually installs."""
    commands: list[str] = []
    if report.missing_python_packages:
        commands.append("uv add --optional audio " + " ".join(sorted(report.missing_python_packages)))
        commands.append("uv sync --extra audio")
    if "ffmpeg" in report.missing_binaries:
        commands.append("winget install --id Gyan.FFmpeg -e --source winget")
    if "espeak-ng" in report.missing_binaries:
        commands.append("winget install --id espeak-ng.espeak-ng -e --source winget")
    return commands


def run_command(command: str) -> subprocess.CompletedProcess:
    """Actually executes one install command. Kept as a thin, separately
    callable wrapper (rather than folded into install_commands) so a skill
    session can show the user each command before running it, run them one
    at a time, and stop on the first failure instead of silently plowing
    through the rest."""
    return subprocess.run(command, shell=True, check=False, capture_output=True, text=True)  # noqa: S602
