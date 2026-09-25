"""Filesystem controller (spec section 8).

Read operations are low-risk; modifications go through the permission layer
before reaching this class, and protected system locations are always
refused outright.
"""

from __future__ import annotations

import fnmatch
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from jarvis.control.backend import ComputerBackend


class FilesystemError(RuntimeError):
    """A filesystem operation failed or was refused."""


class ProtectedPathError(FilesystemError):
    """The path is in a protected system location - never modified automatically."""


_WIN_PROTECTED = (
    "c:\\windows", "c:\\program files", "c:\\program files (x86)", "c:\\programdata",
    "c:\\users\\all users", "c:\\users\\default",
)
_POSIX_PROTECTED = (
    "/bin", "/sbin", "/usr", "/etc", "/var", "/lib", "/lib64", "/boot",
    "/sys", "/proc", "/dev", "/opt", "/root",
)


def is_protected_path(path: Path) -> bool:
    """True for system-critical locations JARVIS must never modify."""
    resolved = str(path.resolve()).lower().replace("/", os.sep).rstrip(os.sep) + os.sep
    if os.name == "nt":
        return any(resolved.startswith(marker.rstrip(os.sep) + os.sep) for marker in _WIN_PROTECTED)
    return any(resolved == marker + os.sep or resolved.startswith(marker + "/") for marker in _POSIX_PROTECTED)


@dataclass(frozen=True)
class EntryInfo:
    name: str
    is_dir: bool
    size: int
    modified: float


class FilesystemController:
    def __init__(self, backend: ComputerBackend) -> None:
        self.backend = backend

    # ------------------------------------------------------------------ helpers

    def expand(self, path: str | Path, base: str | Path | None = None) -> Path:
        """Expand ~ / variables; relative paths resolve against `base` (or cwd)."""
        target = Path(os.path.expandvars(str(path))).expanduser()
        if not target.is_absolute():
            target = (Path(base) if base else Path.cwd()) / target
        return target

    def _writable_target(self, path: Path) -> Path:
        if is_protected_path(path):
            raise ProtectedPathError(
                f"{path} is in a protected system location; I won't modify it."
            )
        return path

    # ------------------------------------------------------------------- reads

    def exists(self, path: str | Path) -> bool:
        return self.expand(path).exists()

    def list_dir(self, path: str | Path) -> list[EntryInfo]:
        target = self.expand(path)
        if not target.is_dir():
            raise FilesystemError(f"not a directory: {target}")
        entries: list[EntryInfo] = []
        for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            try:
                stat = child.stat()
                entries.append(
                    EntryInfo(
                        name=child.name,
                        is_dir=child.is_dir(),
                        size=0 if child.is_dir() else stat.st_size,
                        modified=stat.st_mtime,
                    )
                )
            except OSError:
                continue
        return entries

    def metadata(self, path: str | Path) -> dict[str, object]:
        target = self.expand(path)
        if not target.exists():
            raise FilesystemError(f"no such file: {target}")
        stat = target.stat()
        return {
            "path": str(target),
            "name": target.name,
            "is_dir": target.is_dir(),
            "size_bytes": stat.st_size,
            "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime)),
        }

    def search_files(
        self,
        pattern: str,
        root: str | Path | None = None,
        max_results: int = 200,
    ) -> list[Path]:
        """Find files/dirs whose name matches a glob pattern under `root`."""
        base = self.expand(root) if root else Path.home()
        if not base.is_dir():
            raise FilesystemError(f"not a directory: {base}")
        results: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(base):
            # Skip hidden/system dirs for speed and privacy.
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for name in dirnames + filenames:
                if fnmatch.fnmatch(name.lower(), pattern.lower()):
                    results.append(Path(dirpath) / name)
                    if len(results) >= max_results:
                        return results
        return results

    # -------------------------------------------------------------- open (LOW)

    def open_folder(self, path: str | Path) -> Path:
        target = self.expand(path)
        if not target.is_dir():
            raise FilesystemError(f"folder does not exist: {target}")
        self.backend.open_path(str(target))
        return target

    def open_file(self, path: str | Path) -> Path:
        target = self.expand(path)
        if not target.is_file():
            raise FilesystemError(f"file does not exist: {target}")
        self.backend.open_path(str(target))
        return target

    # ------------------------------------------------------------ writes (MEDIUM)

    def create_folder(self, path: str | Path) -> Path:
        target = self._writable_target(self.expand(path))
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise FilesystemError(f"could not create folder {target}: {exc}") from exc
        return target

    def copy(self, src: str | Path, dst: str | Path) -> Path:
        source, destination = self.expand(src), self.expand(dst)
        if not source.exists():
            raise FilesystemError(f"source does not exist: {source}")
        self._writable_target(destination if destination.is_dir() else destination.parent)
        try:
            if source.is_dir():
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(source, destination)
        except OSError as exc:
            raise FilesystemError(f"could not copy {source} -> {destination}: {exc}") from exc
        return destination

    def move(self, src: str | Path, dst: str | Path) -> Path:
        source, destination = self.expand(src), self.expand(dst)
        if not source.exists():
            raise FilesystemError(f"source does not exist: {source}")
        self._writable_target(destination if destination.is_dir() else destination.parent)
        self._writable_target(source)
        try:
            shutil.move(str(source), str(destination))
        except OSError as exc:
            raise FilesystemError(f"could not move {source} -> {destination}: {exc}") from exc
        return destination

    def rename(self, path: str | Path, new_name: str) -> Path:
        target = self.expand(path)
        if not target.exists():
            raise FilesystemError(f"no such file: {target}")
        if target.parent is None:
            raise FilesystemError("cannot rename a filesystem root")
        destination = target.parent / new_name
        self._writable_target(destination)
        try:
            target.rename(destination)
        except OSError as exc:
            raise FilesystemError(f"could not rename to {destination}: {exc}") from exc
        return destination
