from __future__ import annotations

from audio_lectures.bootstrap import DependencyReport, check, install_commands


def test_check_reports_missing_python_packages_when_not_installed():
    # This dev environment doesn't install the optional "audio" extra, so
    # every one of these should show up as missing -- exercising the real
    # detection path, not a mock.
    report = check()
    assert set(report.missing_python_packages) <= {"torch", "kokoro", "soundfile", "numpy"}
    assert report.cuda_available is None  # torch isn't installed here


def test_is_complete_true_when_nothing_missing():
    assert DependencyReport().is_complete is True


def test_is_complete_false_when_packages_missing():
    assert DependencyReport(missing_python_packages=["torch"]).is_complete is False


def test_install_commands_includes_uv_add_for_missing_packages():
    report = DependencyReport(missing_python_packages=["torch", "kokoro"])
    commands = install_commands(report)
    assert any(c.startswith("uv add --optional audio") for c in commands)
    assert any("kokoro" in c and "torch" in c for c in commands)


def test_install_commands_includes_winget_for_missing_binaries():
    report = DependencyReport(missing_binaries=["ffmpeg", "espeak-ng"])
    commands = install_commands(report)
    assert any("Gyan.FFmpeg" in c for c in commands)
    assert any("espeak-ng" in c for c in commands)


def test_install_commands_empty_when_nothing_missing():
    assert install_commands(DependencyReport()) == []
