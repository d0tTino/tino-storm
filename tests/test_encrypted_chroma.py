from tino_storm.security.encrypted_chroma import EncryptedChroma
from tino_storm.security.crypto import encrypt_bytes, decrypt_bytes


def test_crypto_round_trip():
    data = b"hello world"
    passphrase = "secret"
    encrypted = encrypt_bytes(data, passphrase)
    assert encrypted != data
    decrypted = decrypt_bytes(encrypted, passphrase)
    assert decrypted == data


def test_encrypted_collection_round_trip(tmp_path):
    db_path = tmp_path / "chroma"
    client = EncryptedChroma(str(db_path), passphrase="mypw")
    collection = client.get_or_create_collection("test")
    # provide dummy embeddings so Chroma does not attempt to download models
    collection.add(ids=["1"], embeddings=[[0.0]], documents=["my doc"])
    res = collection.query(query_embeddings=[[0.0]], n_results=1)
    assert res["documents"][0][0] == "my doc"
