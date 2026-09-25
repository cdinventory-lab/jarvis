"""Filesystem controller tests."""

from __future__ import annotations

import os

import pytest

from jarvis.control.backends.simulated import SimulatedBackend
from jarvis.control.filesystem import (
    FilesystemController,
    FilesystemError,
    ProtectedPathError,
    is_protected_path,
)


@pytest.fixture()
def fs(tmp_path) -> FilesystemController:
    return FilesystemController(SimulatedBackend())


def test_is_protected_path():
    if os.name == "nt":
        assert is_protected_path(_p("C:\\Windows\\System32"))
        assert not is_protected_path(_p("C:\\Users\\me\\Documents"))
    else:
        assert is_protected_path(_p("/etc/nginx"))
        assert is_protected_path(_p("/usr/bin"))
        assert not is_protected_path(_p("/home/me/Documents"))


def _p(path: str):
    from pathlib import Path

    return Path(path)


def test_create_and_verify_folder(fs, tmp_path):
    target = tmp_path / "projects" / "new"
    created = fs.create_folder(target)
    assert created.is_dir()


def test_create_folder_in_protected_location_refused(fs):
    protected = "/etc/jarvis-test" if os.name != "nt" else "C:\\Windows\\JarvisTest"
    with pytest.raises(ProtectedPathError):
        fs.create_folder(protected)


def test_list_dir_and_metadata(fs, tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "sub").mkdir()
    entries = fs.list_dir(tmp_path)
    assert {e.name for e in entries} == {"a.txt", "sub"}
    info = fs.metadata(tmp_path / "a.txt")
    assert info["size_bytes"] == 5 and info["is_dir"] is False


def test_copy_move_rename(fs, tmp_path):
    source = tmp_path / "a.txt"
    source.write_text("data")
    copy = fs.copy(source, tmp_path / "b.txt")
    assert copy.read_text() == "data"
    moved = fs.move(copy, tmp_path / "c.txt")
    assert moved.exists() and not copy.exists()
    renamed = fs.rename(moved, "d.txt")
    assert renamed.name == "d.txt" and not moved.exists()


def test_missing_source_raises(fs, tmp_path):
    with pytest.raises(FilesystemError):
        fs.copy(tmp_path / "nope.txt", tmp_path / "x.txt")
    with pytest.raises(FilesystemError):
        fs.rename(tmp_path / "nope.txt", "x")
    with pytest.raises(FilesystemError):
        fs.list_dir(tmp_path / "nope")


def test_search_files(fs, tmp_path):
    (tmp_path / "mockup_jacket.png").write_text("x")
    (tmp_path / "mockup_shirt.png").write_text("x")
    (tmp_path / "other.txt").write_text("x")
    found = fs.search_files("mockup_*", root=tmp_path)
    assert len(found) == 2


def test_expand_user_and_relative(fs, tmp_path):
    assert fs.expand("~/something").is_absolute()
    relative = fs.expand("folder", base=tmp_path)
    assert relative == tmp_path / "folder"
