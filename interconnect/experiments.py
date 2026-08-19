from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .simulator import InterconnectSimulator, SimulationConfig
from .topologies import make_topology
from .traffic import TrafficConfig


def run_experiment_grid(
    node_counts: list[int],
    loads: list[float],
    traffic_patterns: list[str],
    cycles: int,
    repeats: int,
    queue_limit: int,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict] = []

    for num_nodes in node_counts:
        for load in loads:
            for pattern in traffic_patterns:
                for topology_name in ("mesh", "hypercube"):
                    for repeat in range(repeats):
                        seed = 1000 * repeat + 100 * num_nodes + int(load * 100)
                        topology = make_topology(topology_name, num_nodes)
                        config = SimulationConfig(
                            cycles=cycles,
                            injection_rate=load,
                            queue_limit=queue_limit,
                            seed=seed,
                            traffic=TrafficConfig(pattern=pattern),
                        )
                        result = InterconnectSimulator(topology, config).run()
                        row = result.as_dict()
                        row["repeat"] = repeat
                        rows.append(row)
                        print(
                            f"done topology={result.topology:<9} nodes={num_nodes:<4} "
                            f"load={load:.2f} traffic={pattern:<7} repeat={repeat}"
                        )

    raw = pd.DataFrame(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "raw_results.csv"
    raw.to_csv(raw_path, index=False)

    group_cols = ["topology", "num_nodes", "traffic_pattern", "injection_rate"]
    numeric_metrics = [
        "generated_packets",
        "delivered_packets",
        "dropped_packets",
        "pending_packets",
        "delivery_ratio",
        "drop_ratio",
        "average_latency",
        "p95_latency",
        "average_hops",
        "max_hops_observed",
        "throughput_packets_per_cycle",
        "offered_packets_per_cycle",
        "total_links",
        "average_degree",
        "network_diameter",
    ]
    summary = raw.groupby(group_cols, as_index=False)[numeric_metrics].mean()
    summary_path = output_dir / "summary_results.csv"
    summary.to_csv(summary_path, index=False)
    return raw, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run processor interconnection network experiments")
    parser.add_argument("--nodes", nargs="+", type=int, default=[4, 16, 64])
    parser.add_argument("--loads", nargs="+", type=float, default=[0.2, 0.4, 0.6, 0.8, 1.0])
    parser.add_argument("--traffic", nargs="+", default=["uniform", "hotspot"])
    parser.add_argument("--cycles", type=int, default=500)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--queue-limit", type=int, default=64)
    parser.add_argument("--output", type=Path, default=Path("results"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_experiment_grid(
        node_counts=args.nodes,
        loads=args.loads,
        traffic_patterns=args.traffic,
        cycles=args.cycles,
        repeats=args.repeats,
        queue_limit=args.queue_limit,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()
