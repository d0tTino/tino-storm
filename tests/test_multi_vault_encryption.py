from tino_storm.security.crypto import encrypt_bytes, decrypt_bytes
from tino_storm.ingest.watcher import VaultIngestHandler
from tino_storm.ingest.search import search_vaults
from tino_storm.security import config as cfg


class DummyEncryptedCollection:
    def __init__(self, passphrase):
        self.passphrase = passphrase
        self.docs = []

    def add(self, documents=None, metadatas=None, ids=None, embeddings=None, **kw):
        if documents:
            self.docs.extend(
                [encrypt_bytes(d.encode(), self.passphrase) for d in documents]
            )

    def query(self, query_texts=None, n_results=5, **kw):
        docs = [
            decrypt_bytes(d, self.passphrase).decode() for d in self.docs[:n_results]
        ]
        return {"documents": [docs], "metadatas": [[{} for _ in docs]]}


class DummyEncryptedChroma:
    _store: dict[tuple[str, str | None], dict[str, DummyEncryptedCollection]] = {}

    def __init__(self, path, passphrase=None, **kw):
        self.passphrase = passphrase
        key = (path, passphrase)
        self.collections = self._store.setdefault(key, {})

    def get_or_create_collection(self, name, **kw):
        if name not in self.collections:
            self.collections[name] = DummyEncryptedCollection(self.passphrase)
        return self.collections[name]


def test_multi_vault_ingest_and_search(monkeypatch, tmp_path):
    vaults = {"v1": "pw1", "v2": "pw2"}
    monkeypatch.setattr(cfg, "load_config", lambda: {"passphrases": vaults})
    monkeypatch.setattr(
        "tino_storm.ingest.watcher.EncryptedChroma", DummyEncryptedChroma
    )
    monkeypatch.setattr(
        "tino_storm.ingest.search.EncryptedChroma", DummyEncryptedChroma
    )

    chroma_root = tmp_path / "chroma"

    h1 = VaultIngestHandler(str(tmp_path), chroma_path=str(chroma_root), vault="v1")
    h1._ingest_text("doc1", "s1", "v1")
    h2 = VaultIngestHandler(str(tmp_path), chroma_path=str(chroma_root), vault="v2")
    h2._ingest_text("doc2", "s2", "v2")

    res1 = search_vaults("q", ["v1"], chroma_path=str(chroma_root))
    res2 = search_vaults("q", ["v2"], chroma_path=str(chroma_root))
    assert res1[0]["snippets"][0] == "doc1"
    assert res2[0]["snippets"][0] == "doc2"
