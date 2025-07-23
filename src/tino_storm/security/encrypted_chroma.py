"""Encrypted wrappers for Chroma vector stores."""

from __future__ import annotations

import base64
from typing import Any, List, Optional

from chromadb import PersistentClient
from chromadb.api import Collection
from chromadb.config import Settings

from .config import get_passphrase
from .crypto import encrypt_bytes, decrypt_bytes


class EncryptedCollection:
    """A thin wrapper over a Chroma ``Collection`` that encrypts documents."""

    def __init__(self, collection: Collection, passphrase: Optional[str] = None):
        self._collection = collection
        self._passphrase = passphrase or get_passphrase()

    def add(
        self,
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[dict]] = None,
        documents: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Any:
        if documents and self._passphrase:
            documents = [
                base64.b64encode(encrypt_bytes(d.encode(), self._passphrase)).decode()
                for d in documents
            ]
        return self._collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
            **kwargs,
        )

    def query(self, **kwargs: Any) -> Any:
        res = self._collection.query(**kwargs)
        if self._passphrase and res.get("documents"):
            res["documents"] = [
                [
                    decrypt_bytes(base64.b64decode(doc), self._passphrase).decode()
                    for doc in docs
                ]
                for docs in res["documents"]
            ]
        return res

    def __getattr__(self, item: str) -> Any:
        return getattr(self._collection, item)


class EncryptedChroma:
    """Helper that creates encrypted Chroma collections."""

    def __init__(self, path: str, passphrase: Optional[str] = None, **settings: Any):
        self._passphrase = passphrase or get_passphrase()
        self._client = PersistentClient(path=path, settings=Settings(**settings))

    def get_or_create_collection(self, name: str, **kwargs: Any) -> EncryptedCollection:
        col = self._client.get_or_create_collection(name, **kwargs)
        return EncryptedCollection(col, passphrase=self._passphrase)

    def __getattr__(self, item: str) -> Any:
        return getattr(self._client, item)
