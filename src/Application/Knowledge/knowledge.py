import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    source_agent_id: str
    record_type: str  # e.g., market_fact, observation
    data: Dict[str, Any]
    captured_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class KnowledgeNode:
    node_id: str
    label: str
    node_type: str  # Asset, Metric, Regime, Agent
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeEdge:
    edge_id: str
    source_id: str
    target_id: str
    relationship_type: str  # e.g., CORRELATES, VALIDATES, INGESTS
    properties: Dict[str, Any] = field(default_factory=dict)


class EvidenceRepository:
    """Manages raw parsed evidence records with complete trace links."""
    def __init__(self) -> None:
        self._store: Dict[str, EvidenceRecord] = {}

    def store_evidence(self, source_agent_id: str, record_type: str, data: Dict[str, Any]) -> str:
        # Scan for safety
        self._scan_object(data)
        evidence_id = f"evid-{uuid.uuid4()}"
        self._store[evidence_id] = EvidenceRecord(
            evidence_id=evidence_id,
            source_agent_id=source_agent_id,
            record_type=record_type,
            data=data
        )
        return evidence_id

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceRecord]:
        return self._store.get(evidence_id)

    def _scan_object(self, obj: Any) -> None:
        forbidden = {"order", "position", "broker", "execute", "buy", "sell"}
        if isinstance(obj, str):
            for f in forbidden:
                if f in obj.lower():
                    raise ValidationException(f"Safety Violation: Evidence contains forbidden term '{f}'")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                self._scan_object(k)
                self._scan_object(v)
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                self._scan_object(item)


class KnowledgeGraph:
    """Represents connections and relationships across intelligence contexts."""
    def __init__(self) -> None:
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: Dict[str, List[KnowledgeEdge]] = {}  # source_id -> edges list

    def add_node(self, label: str, node_type: str, properties: Optional[Dict[str, Any]] = None) -> str:
        node_id = f"node-{uuid.uuid4()}"
        self.nodes[node_id] = KnowledgeNode(node_id, label, node_type, properties or {})
        return node_id

    def add_edge(self, source_id: str, target_id: str, relationship_type: str, properties: Optional[Dict[str, Any]] = None) -> str:
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValidationException("Graph Error: Both source and target nodes must exist in graph.")
        edge_id = f"edge-{uuid.uuid4()}"
        edge = KnowledgeEdge(edge_id, source_id, target_id, relationship_type, properties or {})
        if source_id not in self.edges:
            self.edges[source_id] = []
        self.edges[source_id].append(edge)
        return edge_id

    def get_neighbors(self, node_id: str) -> List[Tuple[KnowledgeNode, str]]:
        """Returns adjacent nodes with relationship type."""
        neighbors = []
        for edge in self.edges.get(node_id, []):
            neighbors.append((self.nodes[edge.target_id], edge.relationship_type))
        return neighbors


class IntelligenceKnowledgeBase:
    """Consolidated Knowledge Indexing and Query Platform."""
    def __init__(self) -> None:
        self.evidence = EvidenceRepository()
        self.graph = KnowledgeGraph()
        self._index: Dict[str, Set[str]] = {}  # tag -> set of node_ids
        self._historical_storage: Dict[str, Any] = {}

    def index_node(self, node_id: str, tags: List[str]) -> None:
        for tag in tags:
            tag_l = tag.lower()
            if tag_l not in self._index:
                self._index[tag_l] = set()
            self._index[tag_l].add(node_id)

    def query_by_tag(self, tag: str) -> List[KnowledgeNode]:
        node_ids = self._index.get(tag.lower(), set())
        return [self.graph.nodes[nid] for nid in node_ids if nid in self.graph.nodes]

    def store_historical_intelligence(self, key: str, payload: Any) -> None:
        self._historical_storage[key] = payload

    def retrieve_historical_intelligence(self, key: str) -> Optional[Any]:
        return self._historical_storage.get(key)
