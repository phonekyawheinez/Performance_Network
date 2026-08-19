from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _plot_metric(
    df: pd.DataFrame,
    metric: str,
    ylabel: str,
    title: str,
    output: Path,
    traffic_pattern: str,
) -> None:
    subset = df[df["traffic_pattern"] == traffic_pattern]
    fig, ax = plt.subplots(figsize=(8, 5))
    for topology, group in subset.groupby("topology"):
        # Show one curve per processor count.
        for nodes, node_group in group.groupby("num_nodes"):
            node_group = node_group.sort_values("injection_rate")
            ax.plot(
                node_group["injection_rate"],
                node_group[metric],
                marker="o",
                label=f"{topology} - {nodes} nodes",
            )
    ax.set_xlabel("Injection rate (packets/node/cycle)")
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title} — {traffic_pattern.title()} traffic")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def _plot_scalability(df: pd.DataFrame, output: Path, traffic_pattern: str, load: float = 0.4) -> None:
    pattern_df = df[df["traffic_pattern"] == traffic_pattern]
    if pattern_df.empty:
        return
    available_loads = sorted(pattern_df["injection_rate"].unique())
    selected_load = min(available_loads, key=lambda x: abs(x - load))
    subset = pattern_df[(pattern_df["injection_rate"] - selected_load).abs() < 1e-9]
    fig, ax = plt.subplots(figsize=(8, 5))
    for topology, group in subset.groupby("topology"):
        group = group.sort_values("num_nodes")
        ax.plot(group["num_nodes"], group["average_hops"], marker="o", label=topology)
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Number of processors")
    ax.set_ylabel("Average hop count")
    ax.set_title(f"Scalability of Hop Count — load={selected_load:.1f}, {traffic_pattern.title()} traffic")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def generate_all(summary_csv: Path, graph_dir: Path) -> None:
    df = pd.read_csv(summary_csv)
    graph_dir.mkdir(parents=True, exist_ok=True)

    for pattern in sorted(df["traffic_pattern"].unique()):
        _plot_metric(
            df,
            "average_latency",
            "Average latency (cycles)",
            "Latency vs Traffic Load",
            graph_dir / f"latency_{pattern}.png",
            pattern,
        )
        _plot_metric(
            df,
            "throughput_packets_per_cycle",
            "Delivered packets/cycle",
            "Throughput vs Traffic Load",
            graph_dir / f"throughput_{pattern}.png",
            pattern,
        )
        _plot_metric(
            df,
            "delivery_ratio",
            "Packet delivery ratio",
            "Delivery Ratio vs Traffic Load",
            graph_dir / f"delivery_ratio_{pattern}.png",
            pattern,
        )
        _plot_scalability(df, graph_dir / f"hop_scalability_{pattern}.png", pattern)

    print(f"Graphs written to: {graph_dir.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot simulation results")
    parser.add_argument("--input", type=Path, default=Path("results/summary_results.csv"))
    parser.add_argument("--output", type=Path, default=Path("graphs"))
    args = parser.parse_args()
    generate_all(args.input, args.output)


if __name__ == "__main__":
    main()
