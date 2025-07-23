"""Helper functions for encrypting and decrypting data."""

from __future__ import annotations

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))


def encrypt_bytes(data: bytes, passphrase: str) -> bytes:
    """Encrypt bytes with the given passphrase."""
    salt = os.urandom(16)
    key = _derive_key(passphrase, salt)
    f = Fernet(key)
    encrypted = f.encrypt(data)
    return salt + encrypted


def decrypt_bytes(data: bytes, passphrase: str) -> bytes:
    """Decrypt bytes previously encrypted with :func:`encrypt_bytes`."""
    salt = data[:16]
    encrypted = data[16:]
    key = _derive_key(passphrase, salt)
    f = Fernet(key)
    return f.decrypt(encrypted)


def encrypt_str(text: str, passphrase: str) -> str:
    """Encrypt a string and return a base64 encoded string."""
    encrypted = encrypt_bytes(text.encode(), passphrase)
    return base64.b64encode(encrypted).decode()


def decrypt_str(text: str, passphrase: str) -> str:
    """Decrypt a base64 encoded string previously encrypted with :func:`encrypt_str`."""
    data = base64.b64decode(text.encode())
    return decrypt_bytes(data, passphrase).decode()


def encrypt_file(input_path: str, output_path: str, passphrase: str) -> None:
    """Encrypt a file and write the encrypted bytes to ``output_path``."""
    with open(input_path, "rb") as f:
        data = f.read()
    encrypted = encrypt_bytes(data, passphrase)
    with open(output_path, "wb") as f:
        f.write(encrypted)


def decrypt_file(input_path: str, output_path: str, passphrase: str) -> None:
    """Decrypt a file created with :func:`encrypt_file`."""
    with open(input_path, "rb") as f:
        data = f.read()
    decrypted = decrypt_bytes(data, passphrase)
    with open(output_path, "wb") as f:
        f.write(decrypted)
