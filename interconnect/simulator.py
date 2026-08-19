from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Deque

from .topologies import Topology
from .traffic import TrafficConfig, choose_destination


@dataclass
class Packet:
    packet_id: int
    source: int
    destination: int
    created_at: int
    hops: int = 0


@dataclass
class SimulationConfig:
    cycles: int = 500
    injection_rate: float = 0.20
    queue_limit: int = 64
    link_capacity: int = 1
    seed: int = 42
    drain_cycles: int | None = None
    traffic: TrafficConfig = field(default_factory=TrafficConfig)
    collect_trace: bool = False

    def validate(self) -> None:
        if self.cycles <= 0:
            raise ValueError("cycles must be > 0")
        if not 0.0 <= self.injection_rate <= 1.0:
            raise ValueError("injection_rate must be between 0.0 and 1.0")
        if self.queue_limit <= 0:
            raise ValueError("queue_limit must be > 0")
        if self.link_capacity <= 0:
            raise ValueError("link_capacity must be > 0")


@dataclass
class CycleSnapshot:
    cycle: int
    generated_total: int
    delivered_total: int
    dropped_total: int
    pending_packets: int
    average_queue: float
    max_queue: int
    utilized_directed_links: int
    link_utilization: float
    queue_depths: tuple[int, ...]

    def as_dict(self) -> dict:
        row = asdict(self)
        row.pop("queue_depths", None)
        return row


@dataclass
class SimulationResult:
    topology: str
    num_nodes: int
    traffic_pattern: str
    injection_rate: float
    seed: int
    configured_cycles: int
    elapsed_cycles: int
    generated_packets: int
    delivered_packets: int
    dropped_packets: int
    pending_packets: int
    delivery_ratio: float
    drop_ratio: float
    average_latency: float
    p95_latency: float
    average_hops: float
    max_hops_observed: int
    throughput_packets_per_cycle: float
    offered_packets_per_cycle: float
    total_links: int
    average_degree: float
    network_diameter: int

    def as_dict(self) -> dict:
        return asdict(self)


class InterconnectSimulator:
    """Cycle-accurate educational packet simulator with optional congestion trace."""

    def __init__(self, topology: Topology, config: SimulationConfig) -> None:
        config.validate()
        self.topology = topology
        self.config = config
        self.rng = random.Random(config.seed)
        self.queues: dict[int, Deque[Packet]] = {node: deque() for node in range(topology.num_nodes)}
        self.next_packet_id = 0
        self.generated = 0
        self.delivered = 0
        self.dropped = 0
        self.latencies: list[int] = []
        self.hop_counts: list[int] = []
        self.trace: list[CycleSnapshot] = []

    def _inject(self, cycle: int) -> None:
        for source in range(self.topology.num_nodes):
            if self.rng.random() >= self.config.injection_rate:
                continue
            destination = choose_destination(source, self.topology.num_nodes, self.rng, self.config.traffic)
            packet = Packet(self.next_packet_id, source, destination, cycle)
            self.next_packet_id += 1
            self.generated += 1
            if len(self.queues[source]) >= self.config.queue_limit:
                self.dropped += 1
            else:
                self.queues[source].append(packet)

    def _route_one_cycle(self, cycle: int) -> int:
        active: dict[int, list[Packet]] = {}
        for node, queue in self.queues.items():
            active[node] = list(queue)
            queue.clear()

        incoming: dict[int, list[Packet]] = {n: [] for n in range(self.topology.num_nodes)}
        waiting: dict[int, list[Packet]] = {n: [] for n in range(self.topology.num_nodes)}
        used: dict[tuple[int, int], int] = {}

        for node in range(self.topology.num_nodes):
            for packet in active[node]:
                if node == packet.destination:
                    self._record_delivery(packet, cycle)
                    continue
                nxt = self.topology.next_hop(node, packet.destination)
                edge = (node, nxt)
                current_usage = used.get(edge, 0)
                if current_usage >= self.config.link_capacity:
                    waiting[node].append(packet)
                    continue
                used[edge] = current_usage + 1
                packet.hops += 1
                if nxt == packet.destination:
                    self._record_delivery(packet, cycle + 1)
                else:
                    incoming[nxt].append(packet)

        for node in range(self.topology.num_nodes):
            for packet in waiting[node] + incoming[node]:
                if len(self.queues[node]) >= self.config.queue_limit:
                    self.dropped += 1
                else:
                    self.queues[node].append(packet)
        return len(used)

    def _snapshot(self, cycle: int, utilized_links: int) -> None:
        if not self.config.collect_trace:
            return
        depths = tuple(len(self.queues[n]) for n in range(self.topology.num_nodes))
        directed_links = max(1, self.topology.total_links * 2 * self.config.link_capacity)
        self.trace.append(CycleSnapshot(
            cycle=cycle,
            generated_total=self.generated,
            delivered_total=self.delivered,
            dropped_total=self.dropped,
            pending_packets=sum(depths),
            average_queue=(sum(depths) / len(depths)) if depths else 0.0,
            max_queue=max(depths, default=0),
            utilized_directed_links=utilized_links,
            link_utilization=utilized_links / directed_links,
            queue_depths=depths,
        ))

    def _record_delivery(self, packet: Packet, arrival_cycle: int) -> None:
        self.delivered += 1
        self.latencies.append(max(1, arrival_cycle - packet.created_at))
        self.hop_counts.append(packet.hops)

    def _pending(self) -> int:
        return sum(len(q) for q in self.queues.values())

    @staticmethod
    def _percentile(values: list[int], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = (len(ordered) - 1) * percentile
        lower = math.floor(index)
        upper = math.ceil(index)
        if lower == upper:
            return float(ordered[lower])
        weight = index - lower
        return ordered[lower] * (1 - weight) + ordered[upper] * weight

    def run(self) -> SimulationResult:
        for cycle in range(self.config.cycles):
            self._inject(cycle)
            used = self._route_one_cycle(cycle)
            self._snapshot(cycle, used)

        max_drain = self.config.drain_cycles
        if max_drain is None:
            max_drain = max(2 * self.topology.diameter, min(self.config.cycles, 500))

        elapsed = self.config.cycles
        for drain_index in range(max_drain):
            if self._pending() == 0:
                break
            cycle = self.config.cycles + drain_index
            used = self._route_one_cycle(cycle)
            self._snapshot(cycle, used)
            elapsed += 1

        pending = self._pending()
        generated = self.generated
        delivered = self.delivered
        return SimulationResult(
            topology=self.topology.name,
            num_nodes=self.topology.num_nodes,
            traffic_pattern=self.config.traffic.pattern,
            injection_rate=self.config.injection_rate,
            seed=self.config.seed,
            configured_cycles=self.config.cycles,
            elapsed_cycles=elapsed,
            generated_packets=generated,
            delivered_packets=delivered,
            dropped_packets=self.dropped,
            pending_packets=pending,
            delivery_ratio=(delivered / generated) if generated else 0.0,
            drop_ratio=(self.dropped / generated) if generated else 0.0,
            average_latency=mean(self.latencies) if self.latencies else 0.0,
            p95_latency=self._percentile(self.latencies, 0.95),
            average_hops=mean(self.hop_counts) if self.hop_counts else 0.0,
            max_hops_observed=max(self.hop_counts, default=0),
            throughput_packets_per_cycle=(delivered / elapsed) if elapsed else 0.0,
            offered_packets_per_cycle=(generated / self.config.cycles),
            total_links=self.topology.total_links,
            average_degree=self.topology.average_degree,
            network_diameter=self.topology.diameter,
        )
