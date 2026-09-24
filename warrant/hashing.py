"""Content addressing: digests of JSON values and of directory trees."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from pathlib import Path

from warrant.errors import WarrantError

# Never part of a snapshot: version control, caches, local environments and Warrant's own state.
EXCLUDED_NAMES = frozenset({
    ".git", ".hg", ".svn", ".warrant", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".venv", "venv", "node_modules", ".DS_Store",
})


def canonical_json(value) -> bytes:
    """The single byte encoding of a JSON value that every digest is computed over."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def digest_json(value) -> str:
    return digest_bytes(canonical_json(value))


def hex_part(digest: str) -> str:
    return digest.partition(":")[2]


def short(digest: str | None) -> str:
    return f"sha256:{hex_part(digest)[:12]}" if digest else "none"


def tree_digest(root: Path) -> str:
    """Digest of every file's path, content and executable bit under root."""
    if not root.is_dir():
        raise WarrantError(f"{root} is not a directory")
    listing = "".join(f"{kind} {relative}\n" for relative, kind in sorted(_entries(root)))
    return digest_bytes(listing.encode("utf-8"))


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, symlinks=True, ignore=shutil.ignore_patterns(*EXCLUDED_NAMES))


def _entries(root: Path):
    for current, dirs, files in os.walk(root):
        base = Path(current)
        descend = []
        for name in sorted(dirs):
            if name in EXCLUDED_NAMES:
                continue
            path = base / name
            if path.is_symlink():
                yield _relative(root, path), _link(path)
            else:
                descend.append(name)
        dirs[:] = descend
        for name in files:
            if name in EXCLUDED_NAMES:
                continue
            path = base / name
            if path.is_symlink():
                yield _relative(root, path), _link(path)
                continue
            kind = "exec" if path.stat().st_mode & stat.S_IXUSR else "file"
            with path.open("rb") as handle:
                content = hashlib.file_digest(handle, "sha256").hexdigest()
            yield _relative(root, path), f"{kind} {content}"


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _link(path: Path) -> str:
    return "link " + hashlib.sha256(os.readlink(path).encode("utf-8")).hexdigest()
