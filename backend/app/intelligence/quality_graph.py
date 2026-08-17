"""Application Quality Knowledge Graph (Phase 6).

A lightweight, dependency-directed graph over the entities the platform reasons
about — requirement, business_rule, api, ui_component, user_journey, test,
defect, incident — so it can answer questions like *"if this API changes, what
could break?"* by transitive dependency traversal.

No database required: it is an in-memory structure that higher-level services
(change-aware regression, production intelligence) consume.
"""
from __future__ import annotations

from typing import Any, Iterable

NODE_TYPES = (
    "requirement",
    "business_rule",
    "api",
    "ui_component",
    "user_journey",
    "test",
    "defect",
    "incident",
)


class QualityGraph:
    """Dependency-directed knowledge graph.

    ``add_dependency(dependent, dependency, relation)`` records that
    ``dependent`` depends on ``dependency`` (i.e. if ``dependency`` changes,
    ``dependent`` is at risk). ``impact_of`` returns the transitive closure of
    everything that depends on a node.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, dict[str, Any]] = {}
        self._dependents: dict[str, set[str]] = {}
        self._relations: dict[tuple[str, str], str] = {}

    # -- nodes ------------------------------------------------------------- #
    def add_node(self, node_id: str, type_: str, **data: Any) -> None:
        if type_ not in NODE_TYPES:
            raise ValueError(f"unknown node type {type_!r}")
        self._nodes[node_id] = {"type": type_, "data": data}

    def node(self, node_id: str) -> dict[str, Any] | None:
        return self._nodes.get(node_id)

    @property
    def nodes(self) -> dict[str, dict[str, Any]]:
        return dict(self._nodes)

    # -- dependencies ------------------------------------------------------ #
    def add_dependency(self, dependent: str, dependency: str, relation: str) -> None:
        if dependent not in self._nodes or dependency not in self._nodes:
            missing = [n for n in (dependent, dependency) if n not in self._nodes]
            raise KeyError(f"unknown node(s): {missing}")
        self._dependents.setdefault(dependency, set()).add(dependent)
        self._relations[(dependent, dependency)] = relation

    def relation(self, dependent: str, dependency: str) -> str | None:
        return self._relations.get((dependent, dependency))

    # -- queries ----------------------------------------------------------- #
    def impact_of(self, node_id: str) -> set[str]:
        """Every node (transitively) that depends on ``node_id``."""
        seen: set[str] = set()
        stack = [node_id]
        while stack:
            cur = stack.pop()
            for dep in self._dependents.get(cur, ()):
                if dep not in seen:
                    seen.add(dep)
                    stack.append(dep)
        return seen

    def affected(self, node_id: str, *types: str) -> set[str]:
        wanted = set(types)
        return {
            n
            for n in self.impact_of(node_id)
            if self._nodes.get(n, {}).get("type") in wanted
        }

    def affected_tests(self, node_id: str) -> set[str]:
        return self.affected(node_id, "test")

    def affected_requirements(self, node_id: str) -> set[str]:
        return self.affected(node_id, "requirement")

    def affected_journeys(self, node_id: str) -> set[str]:
        return self.affected(node_id, "user_journey")

    def explain_impact(self, node_id: str) -> dict[str, Any]:
        """A human-readable impact summary for a changed node."""
        return {
            "node": node_id,
            "requirements": sorted(self.affected_requirements(node_id)),
            "tests": sorted(self.affected_tests(node_id)),
            "user_journeys": sorted(self.affected_journeys(node_id)),
        }

    # -- coverage ---------------------------------------------------------- #
    def uncovered_journeys(self) -> list[str]:
        """Journeys with no test depending on them."""
        journeys = [n for n, d in self._nodes.items() if d["type"] == "user_journey"]
        return [j for j in journeys if not self._dependents.get(j)]

    def coverage_summary(self) -> dict[str, Any]:
        journeys = [n for n, d in self._nodes.items() if d["type"] == "user_journey"]
        covered = sum(1 for j in journeys if self._dependents.get(j))
        return {
            "total_journeys": len(journeys),
            "covered_journeys": covered,
            "coverage": round(covered / len(journeys), 4) if journeys else 0.0,
            "uncovered_journeys": self.uncovered_journeys(),
        }


def build_from_application_model(model: dict[str, Any]) -> QualityGraph:
    """Construct a graph from the platform's application model.

    ``model`` is the discovered application model (pages, apis, workflows,
    requirements). This is a convenience bridge from Phase 1 discovery to the
    Phase 6 graph; the graph itself stays dependency-agnostic.
    """
    g = QualityGraph()
    for req in model.get("requirements", []):
        rid = req.get("id") or req.get("text")
        g.add_node(rid, "requirement", text=req.get("text", ""))
    for api in model.get("apis", []):
        aid = api.get("id") or api.get("path") or api.get("name")
        g.add_node(aid, "api", **api)
    for wf in model.get("business_workflows", []) or model.get("user_journeys", []):
        wid = wf.get("id") or wf.get("name") or wf.get("title")
        g.add_node(wid, "user_journey", **wf)
    return g
