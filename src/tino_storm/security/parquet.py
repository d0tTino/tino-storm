from __future__ import annotations

from pathlib import Path

from .crypto import encrypt_file, decrypt_file


def encrypt_parquet_files(root: str | Path, passphrase: str) -> None:
    """Encrypt all ``.parquet`` files under ``root`` if not already encrypted."""
    root_p = Path(root)
    for file in root_p.rglob("*.parquet"):
        enc = file.with_suffix(file.suffix + ".enc")
        if not enc.exists():
            encrypt_file(str(file), str(enc), passphrase)
            file.unlink()


def decrypt_parquet_files(root: str | Path, passphrase: str) -> None:
    """Decrypt all ``.parquet.enc`` files under ``root``."""
    root_p = Path(root)
    for file in root_p.rglob("*.parquet.enc"):
        dec = file.with_suffix("")
        decrypt_file(str(file), str(dec), passphrase)
        file.unlink()
