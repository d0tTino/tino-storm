from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Type, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .storm_wiki.modules.storm_dataclass import StormInformationTable, StormArticle


@dataclass
class ResearchAdded:
    """Event emitted when new research is ingested."""

    topic: str
    information_table: "StormInformationTable"


@dataclass
class DocGenerated:
    """Event emitted when a document is generated."""

    topic: str
    article: "StormArticle"


class EventEmitter:
    def __init__(self) -> None:
        self._subscribers: Dict[Type[Any], List[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: Type[Any], handler: Callable[[Any], None]) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def emit(self, event: Any) -> None:
        for handler in self._subscribers.get(type(event), []):
            handler(event)


event_emitter = EventEmitter()
