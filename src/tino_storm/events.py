"""Event system for publishing domain events.

Handlers can be subscribed to concrete event types and invoked when events are
emitted. Use :meth:`EventEmitter.emit` within asynchronous code and
:meth:`EventEmitter.emit_sync` from synchronous code. Both methods invoke each
handler safely and log errors without interrupting other subscribers.

Example:
    >>> emitter = EventEmitter()
    >>> emitter.subscribe(ResearchAdded, handle_research)
    >>> emitter.emit_sync(ResearchAdded(topic="ai", information_table={}))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Type, Any, TYPE_CHECKING, Optional
import asyncio
import inspect
import logging

if TYPE_CHECKING:
    from .storm_wiki.modules.storm_dataclass import StormArticle


@dataclass
class ResearchAdded:
    """Event emitted when new research is ingested."""

    topic: str
    information_table: Dict[str, Any]


@dataclass
class DocGenerated:
    """Event emitted when a document is generated."""

    topic: str
    article: "StormArticle"


class EventEmitter:
    def __init__(self) -> None:
        self._subscribers: Dict[Type[Any], List[Callable[[Any], Any]]] = {}

    def subscribe(self, event_type: Type[Any], handler: Callable[[Any], Any]) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: Type[Any], handler: Callable[[Any], Any]) -> None:
        """Remove a previously registered handler.

        The handler is removed from the subscriber list for ``event_type``.
        If the handler or event type is not registered, the call is a no-op.
        """
        handlers = self._subscribers.get(event_type)
        if not handlers:
            return
        try:
            handlers.remove(handler)
        except ValueError:
            return
        if not handlers:
            del self._subscribers[event_type]

    async def emit(
        self,
        event: Any,
        on_error: Optional[
            Callable[[Callable[[Any], Any], Any, Exception], None]
        ] = None,
    ) -> None:
        """Emit an event to all subscribed handlers.

        Each handler is invoked safely. If a handler raises an exception,
        the error is logged and remaining handlers continue to run. A custom
        ``on_error`` callback can be provided to override the default logging
        behavior.

        Args:
            event: The event instance to emit.
            on_error: Optional callback ``(handler, event, exception)`` used
                for custom error logging.
        """
        for handler in self._subscribers.get(type(event), []):
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:  # noqa: BLE001
                if on_error is not None:
                    on_error(handler, event, exc)
                else:
                    handler_name = getattr(handler, "__name__", repr(handler))
                    logging.exception(
                        "Error in handler %s for event %s",
                        handler_name,
                        type(event).__name__,
                    )

    def emit_sync(
        self,
        event: Any,
        on_error: Optional[
            Callable[[Callable[[Any], Any], Any, Exception], None]
        ] = None,
    ) -> None:
        """Synchronously emit an event to all subscribed handlers.

        Handlers are invoked safely. If a handler returns a coroutine, it is
        executed using a fresh asyncio event loop.

        Args:
            event: The event instance to emit.
            on_error: Optional callback ``(handler, event, exception)`` used
                for custom error logging.
        """
        loop: Optional[asyncio.AbstractEventLoop] = None
        for handler in self._subscribers.get(type(event), []):
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    if loop is None:
                        loop = asyncio.new_event_loop()
                    loop.run_until_complete(result)
            except Exception as exc:  # noqa: BLE001
                if on_error is not None:
                    on_error(handler, event, exc)
                else:
                    handler_name = getattr(handler, "__name__", repr(handler))
                    logging.exception(
                        "Error in handler %s for event %s",
                        handler_name,
                        type(event).__name__,
                    )
        if loop is not None:
            loop.close()


event_emitter = EventEmitter()
