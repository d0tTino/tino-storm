import logging
from dataclasses import dataclass

import pytest

from tino_storm.events import EventEmitter


@dataclass
class DummyEvent:
    value: int


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], scope="module")
async def test_failing_subscriber_does_not_block_and_logs_error(caplog, anyio_backend):
    emitter = EventEmitter()
    calls = []

    def failing_handler(event):
        raise RuntimeError("boom")

    def good_handler(event):
        calls.append(event.value)

    emitter.subscribe(DummyEvent, failing_handler)
    emitter.subscribe(DummyEvent, good_handler)

    with caplog.at_level(logging.ERROR):
        await emitter.emit(DummyEvent(5))

    assert calls == [5]
    assert any(
        record.levelno == logging.ERROR
        and "Error in handler failing_handler for event DummyEvent"
        in record.getMessage()
        for record in caplog.records
    )
