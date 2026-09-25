"""App registry / launcher tests."""

from __future__ import annotations

from jarvis.control.apps import (
    APP_REGISTRY,
    USER_FOLDERS,
    AppLauncher,
    resolve_app_name,
)
from jarvis.control.backends.simulated import SimulatedBackend


def test_registry_has_core_apps():
    expected = {"notepad", "chrome", "edge", "firefox", "blender", "vscode",
                "explorer", "terminal", "calculator"}
    assert expected <= set(APP_REGISTRY)


def test_alias_resolution():
    assert resolve_app_name("notepad").name == "notepad"
    assert resolve_app_name("Note Pad").name == "notepad"
    assert resolve_app_name("vs code").name == "vscode"
    assert resolve_app_name("Visual Studio Code").name == "vscode"
    assert resolve_app_name("Google Chrome").name == "chrome"
    assert resolve_app_name("google").name == "chrome"
    assert resolve_app_name("the Chrome browser").name == "chrome"
    assert resolve_app_name("cmd").name == "terminal"
    assert resolve_app_name("Calc").name == "calculator"
    assert resolve_app_name("unknown-app-xyz") is None


class TestLauncher:
    def test_launch_creates_simulated_window(self):
        launcher = AppLauncher(SimulatedBackend())
        spec = APP_REGISTRY["notepad"]
        handle = launcher.launch(spec)
        assert handle.pid
        windows = launcher.backend.list_windows()
        assert any("Notepad" in w.title for w in windows)

    def test_launch_by_name_known_and_unknown(self):
        launcher = AppLauncher(SimulatedBackend())
        handle, spec = launcher.launch_by_name("chrome")
        assert spec is not None and spec.is_browser
        handle, spec = launcher.launch_by_name("definitely-not-an-app")
        assert spec is None

    def test_launch_at_url_uses_title_hint(self):
        launcher = AppLauncher(SimulatedBackend())
        launcher.launch(APP_REGISTRY["chrome"], url="https://x.co/search",
                        title_hint="query - Search")
        window = launcher.backend.active_window()
        assert window.title == "query - Search"

    def test_generic_command_resolves_from_path(self, tmp_path, monkeypatch):
        fake = tmp_path / "mytool"
        fake.write_text("#!/bin/sh\n")
        fake.chmod(0o755)  # shutil.which only finds executables
        monkeypatch.setenv("PATH", str(tmp_path))  # search only tmp_path
        launcher = AppLauncher(SimulatedBackend(), platform="linux")
        assert launcher.generic_command("mytool") == (str(fake),)
        assert launcher.generic_command("no-such-tool") is None

    def test_user_folder_resolution(self, tmp_path, monkeypatch):
        monkeypatch.setattr("jarvis.control.apps.Path.home", lambda: tmp_path)
        launcher = AppLauncher(SimulatedBackend())
        target = launcher.user_folder("downloads")
        assert target == tmp_path / "Downloads"
        assert target.is_dir()  # created on demand


def test_user_folders_table():
    assert USER_FOLDERS["downloads"] == "Downloads"
    assert USER_FOLDERS["home"] == ""
