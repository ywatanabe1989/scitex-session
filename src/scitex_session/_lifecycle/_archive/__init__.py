#!/usr/bin/env python3
# Timestamp: "2026-05-24 (ywatanabe)"
# File: src/scitex_session/_lifecycle/_archive/__init__.py
"""Archive helpers for scitex-session output dirs.

Provides:
  - archive_session_dir(src_dir, format='tar.gz', remove_src=True) -> Path
  - restore_session_archive(archive_path, dest_dir=None, remove_archive=False) -> Path
  - archive_existing(root, older_than_days=None, format='tar.gz',
                     pattern=None, dry_run=True, max_dirs=None) -> dict
  - restore_existing(root, pattern='*.tar.gz', dest_root=None,
                     remove_archive=False, dry_run=True, max_files=None) -> dict

Format support:
  - "tar.gz" (default): tarfile.open(mode='w:gz', compresslevel=1)
  - "tar"   (uncompressed; for benchmarking or already-compressed inputs)
  - "tar.xz" (slow but small; uses lzma module from stdlib)

Reads use ``tarfile.open(mode='r:*')`` (auto-detect).
"""

from ._bulk import archive_existing, restore_existing
from ._core import SESSION_DIR_PATTERN
from ._single import archive_session_dir, restore_session_archive

__all__ = [
    "archive_session_dir",
    "restore_session_archive",
    "archive_existing",
    "restore_existing",
    "SESSION_DIR_PATTERN",
]

# EOF
