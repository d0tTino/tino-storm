import pathlib

from tino_storm.ingest import ingest_path


def test_ingest_path(monkeypatch, tmp_path):
    calls = {}

    class DummyHandler:
        def __init__(self, root, **kwargs):
            calls["root"] = root
            calls["kwargs"] = kwargs

        def _handle_file(self, path, vault):
            calls["path"] = pathlib.Path(path)
            calls["vault"] = vault

    monkeypatch.setattr("tino_storm.ingest.VaultIngestHandler", DummyHandler)

    file = tmp_path / "note.txt"
    file.write_text("hello")

    ingest_path(str(file), "topic", root=str(tmp_path), twitter_limit=1)

    assert calls["root"] == str(tmp_path)
    assert calls["kwargs"]["twitter_limit"] == 1
    assert calls["path"] == file
    assert calls["vault"] == "topic"
