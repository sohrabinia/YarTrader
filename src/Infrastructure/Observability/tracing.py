import threading
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Infrastructure.Observability.logging import get_correlation_id


class ExecutionSpan:
    """Represents a discrete unit of execution within the overall transaction trace."""

    def __init__(self, name: str, parent: Optional["ExecutionSpan"] = None) -> None:
        self.name = name
        self.parent = parent
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.children: List["ExecutionSpan"] = []
        self.metadata: Dict[str, Any] = {}

    def finish(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.end_time = datetime.now()
        if metadata:
            self.metadata.update(metadata)

    def duration_ms(self) -> float:
        if not self.end_time:
            return (datetime.now() - self.start_time).total_seconds() * 1000.0
        return (self.end_time - self.start_time).total_seconds() * 1000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "duration_ms": round(self.duration_ms(), 2),
            "metadata": self.metadata,
            "children": [c.to_dict() for c in self.children]
        }


class ExecutionTracer:
    """Manages transactional trace graphs and sequential agent execution tracing."""

    def __init__(self) -> None:
        self._active_spans = threading.local()
        self._root_spans: Dict[str, List[ExecutionSpan]] = {}

    def start_span(self, name: str) -> ExecutionSpan:
        correlation_id = get_correlation_id()
        parent = getattr(self._active_spans, "current_span", None)
        span = ExecutionSpan(name, parent)

        if parent:
            parent.children.append(span)
        else:
            if correlation_id not in self._root_spans:
                self._root_spans[correlation_id] = []
            self._root_spans[correlation_id].append(span)

        self._active_spans.current_span = span
        return span

    def end_span(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        span: Optional[ExecutionSpan] = getattr(self._active_spans, "current_span", None)
        if span:
            span.finish(metadata)
            self._active_spans.current_span = span.parent

    def get_trace_tree(self, correlation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cid = correlation_id or get_correlation_id()
        roots = self._root_spans.get(cid, [])
        return [r.to_dict() for r in roots]

    def clear(self) -> None:
        self._root_spans.clear()
        if hasattr(self._active_spans, "current_span"):
            delattr(self._active_spans, "current_span")
