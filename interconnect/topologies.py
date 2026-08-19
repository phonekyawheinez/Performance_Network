from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable


class TopologyError(ValueError):
    pass


class Topology(ABC):
    """Base class for deterministic processor interconnection topologies."""

    name: str

    def __init__(self, num_nodes: int) -> None:
        if num_nodes < 2:
            raise TopologyError("num_nodes must be at least 2")
        self.num_nodes = num_nodes

    @abstractmethod
    def neighbors(self, node: int) -> list[int]:
        raise NotImplementedError

    @abstractmethod
    def next_hop(self, current: int, destination: int) -> int:
        raise NotImplementedError

    @abstractmethod
    def distance(self, source: int, destination: int) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def diameter(self) -> int:
        raise NotImplementedError

    @property
    def total_links(self) -> int:
        return sum(len(self.neighbors(n)) for n in range(self.num_nodes)) // 2

    @property
    def average_degree(self) -> float:
        return 2.0 * self.total_links / self.num_nodes

    def validate_node(self, node: int) -> None:
        if not 0 <= node < self.num_nodes:
            raise TopologyError(f"node {node} is outside [0, {self.num_nodes - 1}]")

    def route(self, source: int, destination: int) -> list[int]:
        """Return the deterministic route from source to destination, inclusive."""
        self.validate_node(source)
        self.validate_node(destination)
        path = [source]
        current = source
        guard = 0
        while current != destination:
            current = self.next_hop(current, destination)
            path.append(current)
            guard += 1
            if guard > self.num_nodes:
                raise RuntimeError("Routing loop detected")
        return path

    def all_edges(self) -> Iterable[tuple[int, int]]:
        seen: set[tuple[int, int]] = set()
        for u in range(self.num_nodes):
            for v in self.neighbors(u):
                edge = (min(u, v), max(u, v))
                if edge not in seen:
                    seen.add(edge)
                    yield edge


class Mesh2D(Topology):
    """Square 2D mesh using deterministic XY routing."""

    name = "2D Mesh"

    def __init__(self, num_nodes: int) -> None:
        super().__init__(num_nodes)
        side = math.isqrt(num_nodes)
        if side * side != num_nodes:
            raise TopologyError(
                "2D Mesh requires a perfect-square number of nodes (e.g. 4, 16, 64, 256)."
            )
        self.side = side

    def coord(self, node: int) -> tuple[int, int]:
        self.validate_node(node)
        return node % self.side, node // self.side

    def node_id(self, x: int, y: int) -> int:
        return y * self.side + x

    def neighbors(self, node: int) -> list[int]:
        x, y = self.coord(node)
        result: list[int] = []
        if x > 0:
            result.append(self.node_id(x - 1, y))
        if x < self.side - 1:
            result.append(self.node_id(x + 1, y))
        if y > 0:
            result.append(self.node_id(x, y - 1))
        if y < self.side - 1:
            result.append(self.node_id(x, y + 1))
        return result

    def next_hop(self, current: int, destination: int) -> int:
        self.validate_node(current)
        self.validate_node(destination)
        if current == destination:
            return current

        cx, cy = self.coord(current)
        dx, dy = self.coord(destination)

        # XY routing: resolve X first, then Y.
        if cx < dx:
            cx += 1
        elif cx > dx:
            cx -= 1
        elif cy < dy:
            cy += 1
        elif cy > dy:
            cy -= 1
        return self.node_id(cx, cy)

    def distance(self, source: int, destination: int) -> int:
        sx, sy = self.coord(source)
        dx, dy = self.coord(destination)
        return abs(sx - dx) + abs(sy - dy)

    @property
    def diameter(self) -> int:
        return 2 * (self.side - 1)


class Hypercube(Topology):
    """d-dimensional hypercube with bit-fixing routing."""

    name = "Hypercube"

    def __init__(self, num_nodes: int) -> None:
        super().__init__(num_nodes)
        if num_nodes & (num_nodes - 1):
            raise TopologyError(
                "Hypercube requires a power-of-two number of nodes (e.g. 4, 8, 16, 32, 64)."
            )
        self.dimension = int(math.log2(num_nodes))

    def neighbors(self, node: int) -> list[int]:
        self.validate_node(node)
        return [node ^ (1 << bit) for bit in range(self.dimension)]

    def next_hop(self, current: int, destination: int) -> int:
        self.validate_node(current)
        self.validate_node(destination)
        if current == destination:
            return current

        diff = current ^ destination
        # Resolve the least-significant differing dimension first.
        bit = (diff & -diff).bit_length() - 1
        return current ^ (1 << bit)

    def distance(self, source: int, destination: int) -> int:
        self.validate_node(source)
        self.validate_node(destination)
        return (source ^ destination).bit_count()

    @property
    def diameter(self) -> int:
        return self.dimension


TOPOLOGIES = {
    "mesh": Mesh2D,
    "hypercube": Hypercube,
}


def make_topology(name: str, num_nodes: int) -> Topology:
    try:
        cls = TOPOLOGIES[name.lower()]
    except KeyError as exc:
        raise TopologyError(f"Unknown topology: {name}. Choose from {sorted(TOPOLOGIES)}") from exc
    return cls(num_nodes)
