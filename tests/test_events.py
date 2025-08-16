import logging
import asyncio
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


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], scope="module")
async def test_unsubscribed_handler_not_called(anyio_backend):
    emitter = EventEmitter()
    calls: list[int] = []

    def handler(event):
        calls.append(event.value)

    emitter.subscribe(DummyEvent, handler)
    emitter.unsubscribe(DummyEvent, handler)

    await emitter.emit(DummyEvent(42))

    assert calls == []


def test_emit_sync_runs_sync_and_async_handlers():
    emitter = EventEmitter()
    calls = []

    def sync_handler(event):
        calls.append(("sync", event.value))

    async def async_handler(event):
        await asyncio.sleep(0)
        calls.append(("async", event.value))

    emitter.subscribe(DummyEvent, sync_handler)
    emitter.subscribe(DummyEvent, async_handler)

    emitter.emit_sync(DummyEvent(1))

    assert calls == [("sync", 1), ("async", 1)]


def test_emit_sync_failing_handler_does_not_block_and_logs_error(caplog):
    emitter = EventEmitter()
    calls = []

    def failing_handler(event):
        raise RuntimeError("boom")

    def good_handler(event):
        calls.append(event.value)

    emitter.subscribe(DummyEvent, failing_handler)
    emitter.subscribe(DummyEvent, good_handler)

    with caplog.at_level(logging.ERROR):
        emitter.emit_sync(DummyEvent(5))

    assert calls == [5]
    assert any(
        record.levelno == logging.ERROR
        and "Error in handler failing_handler for event DummyEvent"
        in record.getMessage()
        for record in caplog.records
    )


def test_emit_sync_multiple_handlers_with_failures_logs_errors_and_continues(caplog):
    emitter = EventEmitter()
    calls = []

    def failing_handler_one(event):
        raise RuntimeError("boom1")

    async def async_failing_handler(event):
        await asyncio.sleep(0)
        raise RuntimeError("boom2")

    def good_handler_one(event):
        calls.append(("good1", event.value))

    async def good_handler_two(event):
        await asyncio.sleep(0)
        calls.append(("good2", event.value))

    emitter.subscribe(DummyEvent, failing_handler_one)
    emitter.subscribe(DummyEvent, good_handler_one)
    emitter.subscribe(DummyEvent, async_failing_handler)
    emitter.subscribe(DummyEvent, good_handler_two)

    with caplog.at_level(logging.ERROR):
        emitter.emit_sync(DummyEvent(7))

    assert calls == [("good1", 7), ("good2", 7)]
    error_messages = [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.ERROR
    ]
    assert any("failing_handler_one" in msg for msg in error_messages)
    assert any("async_failing_handler" in msg for msg in error_messages)
