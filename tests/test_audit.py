from tino_storm.security.audit import log_request


def test_log_request(tmp_path, monkeypatch):
    log_path = tmp_path / "audit.log"
    monkeypatch.setattr("tino_storm.security.audit.AUDIT_LOG_PATH", log_path)
    log_request("GET", "http://example.com")
    assert log_path.exists()
    content = log_path.read_text()
    assert "GET http://example.com" in content
