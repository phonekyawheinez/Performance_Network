from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class TrafficConfig:
    pattern: str = "uniform"
    hotspot_node: int = 0
    hotspot_probability: float = 0.70


def choose_destination(
    source: int,
    num_nodes: int,
    rng: random.Random,
    config: TrafficConfig,
) -> int:
    """Choose a destination different from source."""
    pattern = config.pattern.lower()

    if pattern == "uniform":
        candidate = rng.randrange(num_nodes - 1)
        return candidate if candidate < source else candidate + 1

    if pattern == "hotspot":
        hotspot = config.hotspot_node % num_nodes
        if source != hotspot and rng.random() < config.hotspot_probability:
            return hotspot
        candidate = rng.randrange(num_nodes - 1)
        return candidate if candidate < source else candidate + 1

    raise ValueError("Unsupported traffic pattern. Use 'uniform' or 'hotspot'.")
