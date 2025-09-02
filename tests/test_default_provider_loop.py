from tino_storm.providers.base import (
    DefaultProvider,
    _get_loop,
    _get_loop_thread,
    _stop_loop,
)


def test_summarize_reuses_loop_and_shutdown(monkeypatch):
    monkeypatch.delenv("STORM_SUMMARY_MODEL", raising=False)
    provider = DefaultProvider()

    provider._summarize(["a"])
    loop1 = _get_loop()
    thread1 = _get_loop_thread()
    assert loop1 is not None
    assert thread1 is not None and thread1.is_alive()

    provider._summarize(["b"])
    loop2 = _get_loop()
    assert loop1 is loop2

    _stop_loop()
    assert _get_loop() is None
    thread2 = _get_loop_thread()
    assert thread2 is None or not thread2.is_alive()
