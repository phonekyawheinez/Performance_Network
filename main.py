from __future__ import annotations

import argparse
import json

from interconnect import InterconnectSimulator, SimulationConfig, TrafficConfig, make_topology


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a processor interconnection network")
    parser.add_argument("--topology", choices=["mesh", "hypercube"], default="mesh")
    parser.add_argument("--nodes", type=int, default=16)
    parser.add_argument("--cycles", type=int, default=500)
    parser.add_argument("--load", type=float, default=0.4, help="Packets generated per node per cycle [0..1]")
    parser.add_argument("--traffic", choices=["uniform", "hotspot"], default="uniform")
    parser.add_argument("--queue-limit", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    topology = make_topology(args.topology, args.nodes)
    config = SimulationConfig(
        cycles=args.cycles,
        injection_rate=args.load,
        queue_limit=args.queue_limit,
        seed=args.seed,
        traffic=TrafficConfig(pattern=args.traffic),
    )
    result = InterconnectSimulator(topology, config).run()
    print(json.dumps(result.as_dict(), indent=2))


if __name__ == "__main__":
    main()
