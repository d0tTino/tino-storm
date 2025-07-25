from tino_storm.security.parquet import encrypt_parquet_files, decrypt_parquet_files


def test_parquet_encrypt_round_trip(tmp_path):
    data = b"testdata"
    file = tmp_path / "sample.parquet"
    file.write_bytes(data)

    encrypt_parquet_files(tmp_path, "pw")
    enc = tmp_path / "sample.parquet.enc"
    assert enc.exists() and not file.exists()

    decrypt_parquet_files(tmp_path, "pw")
    assert file.exists() and not enc.exists()
    assert file.read_bytes() == data
