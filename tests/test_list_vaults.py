import os
import sys


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tino_storm.ingest.search import list_vaults  # noqa: E402


def _make_vaults(root: str, names: list[str]) -> None:
    for name in names:
        os.makedirs(os.path.join(root, name))


def test_list_vaults_default_root(tmp_path, monkeypatch):
    vault_root = tmp_path / "research"
    _make_vaults(vault_root, ["v1", "v2"])
    (vault_root / "file.txt").write_text("not a vault")

    monkeypatch.setenv("STORM_VAULT_ROOT", str(vault_root))

    assert set(list_vaults()) == {"v1", "v2"}


def test_list_vaults_custom_root(tmp_path, monkeypatch):
    env_root = tmp_path / "env"
    _make_vaults(env_root, ["ignored"])
    monkeypatch.setenv("STORM_VAULT_ROOT", str(env_root))

    custom_root = tmp_path / "custom"
    _make_vaults(custom_root, ["a", "b"])

    assert set(list_vaults(str(custom_root))) == {"a", "b"}

