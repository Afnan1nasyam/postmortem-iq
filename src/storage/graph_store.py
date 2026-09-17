"""NetworkX knowledge graph with JSON persistence."""

import json
from collections import Counter, deque
from pathlib import Path

import networkx as nx
from loguru import logger

from src.config import settings
from src.models.schemas import IncidentExtraction


def _norm(name: str) -> str:
    return name.strip().lower()


class KnowledgeGraph:
    """Directed knowledge graph of incidents, services, root causes, and resolutions."""

    def __init__(self):
        self._path = Path(settings.GRAPH_PATH)
        self._graph: nx.DiGraph = self.load() if self._path.exists() else nx.DiGraph()
        logger.info("KnowledgeGraph ready ({} nodes, {} edges)",
                     self._graph.number_of_nodes(), self._graph.number_of_edges())

    def _add_node(self, node_id: str, **attrs) -> None:
        if not self._graph.has_node(node_id):
            self._graph.add_node(node_id, **attrs)

    def add_incident(self, extraction: IncidentExtraction) -> None:
        """Build graph nodes and edges from a single extraction."""
        iid = extraction.incident_id

        self._add_node(iid, type="Incident", title=extraction.title,
                        severity=extraction.severity, date=extraction.date)

        rc_id = f"rc:{_norm(extraction.root_cause.category)}"
        self._add_node(rc_id, type="RootCause", category=extraction.root_cause.category,
                        description=extraction.root_cause.description)
        self._graph.add_edge(iid, rc_id, type="CAUSED_BY",
                              confidence=1.0)

        res_id = f"res:{iid}"
        self._add_node(res_id, type="Resolution", description=extraction.resolution.description,
                        resolution_type=extraction.resolution.type)
        self._graph.add_edge(iid, res_id, type="RESOLVED_WITH",
                              time_to_resolve=extraction.resolution.time_to_resolve)

        for svc in extraction.affected_services:
            svc_id = f"svc:{_norm(svc.name)}"
            self._add_node(svc_id, type="Service", name=_norm(svc.name))
            self._graph.add_edge(svc_id, iid, type="AFFECTED_BY", role=svc.role)

        for i, step in enumerate(extraction.failure_chain):
            fm_id = f"fm:{iid}:{i}"
            self._add_node(fm_id, type="FailureMode", description=step, step=i)
            self._graph.add_edge(iid, fm_id, type="EXHIBITED")

        for dep in extraction.service_dependencies:
            from_id = f"svc:{_norm(dep.from_service)}"
            to_id = f"svc:{_norm(dep.to_service)}"
            self._add_node(from_id, type="Service", name=_norm(dep.from_service))
            self._add_node(to_id, type="Service", name=_norm(dep.to_service))
            self._graph.add_edge(from_id, to_id, type="DEPENDS_ON",
                                  dependency_type=dep.type)

            if any(s.name.strip().lower() == _norm(dep.from_service) for s in extraction.affected_services) and \
               any(s.name.strip().lower() == _norm(dep.to_service) for s in extraction.affected_services):
                self._graph.add_edge(from_id, to_id, type="CASCADED_TO",
                                      via_incident=iid)

        self.save()
        logger.info("Added incident {} to graph", iid)

    def get_service_dependencies(self, service_name: str, max_hops: int = 2) -> dict:
        """BFS for upstream and downstream dependencies of a service."""
        svc_id = f"svc:{_norm(service_name)}"
        if not self._graph.has_node(svc_id):
            return {"upstream": [], "downstream": []}

        def _bfs(start: str, direction: str) -> list[str]:
            visited = set()
            queue = deque([(start, 0)])
            result = []
            while queue:
                node, depth = queue.popleft()
                if depth > max_hops:
                    continue
                if node != start and self._graph.nodes[node].get("type") == "Service":
                    result.append(self._graph.nodes[node].get("name", node))
                visited.add(node)
                neighbors = (self._graph.predecessors(node) if direction == "upstream"
                             else self._graph.successors(node))
                for nb in neighbors:
                    if nb not in visited:
                        edge = self._graph.edges.get((nb, node) if direction == "upstream"
                                                      else (node, nb), {})
                        if edge.get("type") in ("DEPENDS_ON", "CASCADED_TO"):
                            queue.append((nb, depth + 1))
            return result

        return {
            "upstream": _bfs(svc_id, "upstream"),
            "downstream": _bfs(svc_id, "downstream"),
        }

    def get_blast_radius(self, service_name: str) -> list[str]:
        """All downstream reachable services from a given service."""
        svc_id = f"svc:{_norm(service_name)}"
        if not self._graph.has_node(svc_id):
            return []
        reachable = []
        for node in nx.descendants(self._graph, svc_id):
            if self._graph.nodes[node].get("type") == "Service" and node != svc_id:
                reachable.append(self._graph.nodes[node].get("name", node))
        return reachable

    def get_incidents_for_service(self, service_name: str) -> list[str]:
        """Return incident IDs linked to a service."""
        svc_id = f"svc:{_norm(service_name)}"
        if not self._graph.has_node(svc_id):
            return []
        incidents = []
        for neighbor in self._graph.successors(svc_id):
            if self._graph.nodes[neighbor].get("type") == "Incident":
                incidents.append(neighbor)
        return incidents

    def get_similar_incidents(self, incident_id: str) -> list[dict]:
        """Find incidents sharing services or root cause categories."""
        if not self._graph.has_node(incident_id):
            return []

        my_services = set()
        my_rc = None
        for nb in self._graph.predecessors(incident_id):
            if self._graph.nodes[nb].get("type") == "Service":
                my_services.add(nb)
        for nb in self._graph.successors(incident_id):
            if self._graph.nodes[nb].get("type") == "RootCause":
                my_rc = nb

        similar = []
        for node, attrs in self._graph.nodes(data=True):
            if attrs.get("type") != "Incident" or node == incident_id:
                continue
            shared_svcs = set()
            same_rc = False
            for nb in self._graph.predecessors(node):
                if nb in my_services:
                    shared_svcs.add(self._graph.nodes[nb].get("name", nb))
            if my_rc:
                for nb in self._graph.successors(node):
                    if nb == my_rc:
                        same_rc = True
            if shared_svcs or same_rc:
                similar.append({
                    "incident_id": node,
                    "title": attrs.get("title", ""),
                    "shared_services": list(shared_svcs),
                    "same_root_cause": same_rc,
                })
        return similar

    def get_stats(self) -> dict:
        """Node counts by type, edge counts by type, top 5 most connected services."""
        node_types: Counter = Counter()
        for _, attrs in self._graph.nodes(data=True):
            node_types[attrs.get("type", "unknown")] += 1

        edge_types: Counter = Counter()
        for _, _, attrs in self._graph.edges(data=True):
            edge_types[attrs.get("type", "unknown")] += 1

        service_degrees = []
        for node, attrs in self._graph.nodes(data=True):
            if attrs.get("type") == "Service":
                service_degrees.append((attrs.get("name", node), self._graph.degree(node)))
        service_degrees.sort(key=lambda x: x[1], reverse=True)

        return {
            "total_nodes": self._graph.number_of_nodes(),
            "total_edges": self._graph.number_of_edges(),
            "node_types": dict(node_types),
            "edge_types": dict(edge_types),
            "top_services": service_degrees[:5],
        }

    def get_all_services(self) -> list[str]:
        """Return names of all service nodes."""
        return [
            attrs.get("name", node)
            for node, attrs in self._graph.nodes(data=True)
            if attrs.get("type") == "Service"
        ]

    def save(self) -> None:
        """Persist graph to JSON."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self._graph)
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug("Graph saved to {}", self._path)

    def load(self) -> nx.DiGraph:
        """Load graph from JSON file."""
        data = json.loads(self._path.read_text(encoding="utf-8"))
        graph = nx.node_link_graph(data, directed=True)
        logger.debug("Graph loaded from {}", self._path)
        return graph

    def reset(self) -> None:
        """Clear the graph and delete the persistence file."""
        self._graph = nx.DiGraph()
        if self._path.exists():
            self._path.unlink()
        logger.info("KnowledgeGraph reset")
