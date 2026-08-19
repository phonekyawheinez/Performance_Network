from __future__ import annotations

from math import cos, pi, sin
from typing import Iterable

import networkx as nx
import plotly.graph_objects as go

from .topologies import Hypercube, Mesh2D, Topology


def route_nodes(topology: Topology, source: int, destination: int) -> list[int]:
    topology.validate_node(source)
    topology.validate_node(destination)
    path = [source]
    current = source
    guard = 0
    while current != destination:
        current = topology.next_hop(current, destination)
        path.append(current)
        guard += 1
        if guard > topology.num_nodes:
            raise RuntimeError("Routing loop detected")
    return path


def average_pair_distance(topology: Topology) -> float:
    total = 0
    pairs = 0
    for source in range(topology.num_nodes):
        for destination in range(source + 1, topology.num_nodes):
            total += topology.distance(source, destination)
            pairs += 1
    return total / pairs if pairs else 0.0


def _layout(topology: Topology) -> dict[int, tuple[float, float]]:
    if isinstance(topology, Mesh2D):
        return {node: (float(topology.coord(node)[0]), -float(topology.coord(node)[1])) for node in range(topology.num_nodes)}

    # Use a deterministic force layout for small hypercubes. For larger graphs,
    # a circular layout stays readable and avoids expensive layout iterations.
    graph = nx.Graph()
    graph.add_nodes_from(range(topology.num_nodes))
    graph.add_edges_from(topology.all_edges())
    if topology.num_nodes <= 32:
        raw = nx.spring_layout(graph, seed=7, iterations=120)
        return {int(node): (float(xy[0]), float(xy[1])) for node, xy in raw.items()}

    result: dict[int, tuple[float, float]] = {}
    for i, node in enumerate(range(topology.num_nodes)):
        angle = 2 * pi * i / topology.num_nodes
        result[node] = (cos(angle), sin(angle))
    return result


def _node_label(topology: Topology, node: int) -> str:
    if isinstance(topology, Hypercube):
        return f"P{node}<br>{node:0{topology.dimension}b}"
    return f"P{node}"


def _hover_text(topology: Topology, node: int) -> str:
    neighbors = topology.neighbors(node)
    if isinstance(topology, Mesh2D):
        x, y = topology.coord(node)
        address = f"coordinate=({x}, {y})"
    else:
        address = f"binary={node:0{topology.dimension}b}"
    return (
        f"Processor P{node}<br>{address}<br>degree={len(neighbors)}"
        f"<br>neighbors={', '.join('P'+str(n) for n in neighbors)}"
    )


def topology_figure(
    topology: Topology,
    *,
    path: list[int] | None = None,
    current_step: int | None = None,
    node_values: dict[int, float] | None = None,
    title: str | None = None,
) -> go.Figure:
    pos = _layout(topology)
    path = path or []
    path_edges = {tuple(sorted((a, b))) for a, b in zip(path, path[1:])}
    traversed_edges: set[tuple[int, int]] = set()
    if current_step is not None and path:
        upto = max(0, min(current_step, len(path) - 1))
        traversed_edges = {tuple(sorted((a, b))) for a, b in zip(path[:upto], path[1:upto + 1])}

    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    route_x: list[float | None] = []
    route_y: list[float | None] = []
    traversed_x: list[float | None] = []
    traversed_y: list[float | None] = []

    for u, v in topology.all_edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        key = tuple(sorted((u, v)))
        target_x, target_y = edge_x, edge_y
        if key in traversed_edges:
            target_x, target_y = traversed_x, traversed_y
        elif key in path_edges:
            target_x, target_y = route_x, route_y
        target_x.extend([x0, x1, None])
        target_y.extend([y0, y1, None])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines", hoverinfo="skip",
        line=dict(width=1.2, color="rgba(100,116,139,0.45)"), showlegend=False,
    ))
    if route_x:
        fig.add_trace(go.Scatter(
            x=route_x, y=route_y, mode="lines", hoverinfo="skip",
            line=dict(width=4, color="#60A5FA"), name="Planned route",
        ))
    if traversed_x:
        fig.add_trace(go.Scatter(
            x=traversed_x, y=traversed_y, mode="lines", hoverinfo="skip",
            line=dict(width=6, color="#F59E0B"), name="Traversed",
        ))

    node_x, node_y, labels, hover = [], [], [], []
    marker_colors: list[float | str] = []
    marker_sizes: list[int] = []
    source = path[0] if path else None
    destination = path[-1] if path else None
    current = path[current_step] if path and current_step is not None and 0 <= current_step < len(path) else None

    for node in range(topology.num_nodes):
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        labels.append(_node_label(topology, node))
        hover.append(_hover_text(topology, node))
        marker_sizes.append(25 if topology.num_nodes <= 16 else 16 if topology.num_nodes <= 64 else 9)

        if node_values is not None:
            marker_colors.append(float(node_values.get(node, 0.0)))
        elif node == current:
            marker_colors.append("#F59E0B")
        elif node == source:
            marker_colors.append("#22C55E")
        elif node == destination:
            marker_colors.append("#EF4444")
        elif node in path:
            marker_colors.append("#60A5FA")
        else:
            marker_colors.append("#CBD5E1")

    marker: dict = dict(size=marker_sizes, line=dict(width=1, color="#0F172A"))
    if node_values is not None:
        marker.update(
            color=marker_colors,
            colorscale="YlOrRd",
            showscale=True,
            colorbar=dict(title="Avg queue"),
        )
    else:
        marker["color"] = marker_colors

    fig.add_trace(go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text" if topology.num_nodes <= 32 else "markers",
        text=labels,
        textposition="top center",
        hovertext=hover,
        hoverinfo="text",
        marker=marker,
        name="Processors",
    ))

    fig.update_layout(
        title=title or topology.name,
        margin=dict(l=10, r=10, t=50, b=10),
        height=570,
        hovermode="closest",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def route_explanation(topology: Topology, path: list[int], step: int) -> str:
    if not path:
        return "No route."
    step = max(0, min(step, len(path) - 1))
    current = path[step]
    if step == 0:
        if isinstance(topology, Mesh2D):
            return f"Packet starts at P{current}, coordinate {topology.coord(current)}."
        return f"Packet starts at P{current}, binary {current:0{topology.dimension}b}."

    previous = path[step - 1]
    if isinstance(topology, Mesh2D):
        px, py = topology.coord(previous)
        cx, cy = topology.coord(current)
        if cx != px:
            direction = "right" if cx > px else "left"
            reason = "XY routing resolves the X coordinate first"
        else:
            direction = "down" if cy > py else "up"
            reason = "X now matches, so XY routing resolves Y"
        return f"Hop {step}: P{previous} → P{current} ({direction}); {reason}."

    changed = previous ^ current
    bit = changed.bit_length() - 1
    return (
        f"Hop {step}: P{previous} ({previous:0{topology.dimension}b}) → "
        f"P{current} ({current:0{topology.dimension}b}); bit {bit} is flipped to match the destination."
    )
