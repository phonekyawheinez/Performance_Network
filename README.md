# Processor Interconnection Network Visual Simulation Lab v2

An interactive academic simulator for **2D Mesh vs Hypercube processor interconnection networks**. Version 2 adds topology visualization, hop-by-hop routing, router queue/congestion tracing, interactive performance charts, and load-sweep analysis so the project can be demonstrated visually instead of only presenting final numbers.

## Research question

> How do 2D Mesh and Hypercube processor interconnection networks differ in communication latency, throughput, hop count, congestion, packet delivery, and physical connection cost as processor count and offered traffic increase?

## What is new in v2

The Streamlit application is organized as a teaching/demo workflow:

1. **Topology Explorer** — interactive Mesh and Hypercube diagrams with processor addresses, neighbors, degree, diameter, link count, and average pair distance.
2. **Packet Route Explorer** — select any source and destination and move a packet hop-by-hop through XY routing or Hypercube bit-fixing routing.
3. **Congestion Trace** — records router queues every cycle and visualizes queue buildup as a time-series, processor heatmap, and congestion-colored topology.
4. **Performance Lab** — run identical workloads on both networks and automatically compare latency, throughput, delivery ratio, hop count, and link cost.
5. **Scalability Sweep** — automatically tests 12 offered-load points and plots latency, throughput, delivery ratio, and approximate congestion onset.
6. **Concepts & Report** — concise explanations and methodology text for presentations/reports.

## Main metrics

- Average latency and 95th-percentile latency
- Throughput (delivered packets/cycle)
- Average and maximum hop count
- Packet delivery/drop ratio
- Pending packets after drain
- Per-cycle router queue depth
- Link utilization
- Network diameter
- Physical link count
- Average processor degree
- Average pairwise communication distance

## Traffic models

- **Uniform random** — destinations are distributed across processors.
- **Hotspot** — many packets target one processor to demonstrate contention and bottlenecks.

## Simulation model

- Discrete cycle simulation
- At most one new packet per processor per cycle
- One hop maximum movement per packet per cycle
- Configurable directed-link capacity
- Finite shared router queues
- Deterministic routing
- Drain phase after traffic injection
- Optional cycle-by-cycle queue/link trace

This is an educational network-level model. It is deliberately more understandable than a transistor/RTL or flit-level NoC simulator, while still demonstrating routing distance, contention, queueing, saturation, and topology cost.

## Project structure

```text
processor_interconnect_project_v2/
├── dashboard.py                  # interactive visual lab
├── main.py                       # one simulation from CLI
├── requirements.txt
├── pyproject.toml
├── interconnect/
│   ├── topologies.py             # Mesh + Hypercube + routes
│   ├── traffic.py                # uniform + hotspot traffic
│   ├── simulator.py              # packet simulator + cycle trace
│   ├── visualization.py          # Plotly network/route visualizations
│   ├── experiments.py            # experiment grid
│   └── plot_results.py           # report graph generation
├── tests/
│   ├── test_topologies.py
│   ├── test_simulator.py
│   └── test_visualization.py
├── results/
└── graphs/
```

## Setup — use a clean virtual environment

Do this because other Python tools such as FastAPI/PlatformIO may require incompatible shared dependency versions.

### Kali / Ubuntu / Linux

```bash
cd processor_interconnect_project_v2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
```

### Windows PowerShell

```powershell
cd processor_interconnect_project_v2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
```

## Start the visual dashboard

```bash
streamlit run dashboard.py
```

Open the local address printed by Streamlit, normally:

```text
http://localhost:8501
```

## Best demonstration sequence

Use **16 processors** first because both topologies are easy to see.

### Demo 1 — understand topology

Open **① Topology Explorer** and compare:

- Mesh processor coordinates and local neighbors
- Hypercube binary processor addresses
- Diameter
- Average pair distance
- Physical links
- Average node degree

### Demo 2 — show routing

Open **② Packet Route**.

Try:

```text
Source: P0
Destination: P15
```

For 16 processors:

- 4×4 Mesh route P0→P15 requires 6 hops with XY routing.
- 4-D Hypercube P0→P15 requires 4 bit-fixing hops.

Move the **Packet position** slider one step at a time. The diagram highlights the planned route, traversed links, and current processor.

### Demo 3 — make congestion visible

Open **③ Congestion Trace** and try:

```text
Processors:      16
Injection rate:  0.75
Cycles:          120
Queue limit:     8 or 16
Traffic:         hotspot
Link capacity:   1
```

The app then shows:

1. Average/max queue size vs cycle
2. Router queue heatmap
3. Congestion mapped onto network processors
4. Generated/delivered/dropped packet counts

### Demo 4 — fair side-by-side comparison

Open **④ Performance Lab** and use the same workload on both networks.

Recommended starting point:

```text
Injection rate: 0.45
Cycles:         500
Queue limit:    32
Link capacity:  1
Traffic:        uniform
```

The dashboard calculates the winner per metric and produces an automatic interpretation including latency change and physical-link cost.

### Demo 5 — strongest report experiment

Open **⑤ Scalability Sweep**.

This runs 12 injection rates from light traffic toward saturation for both topologies and produces:

- Latency vs load
- Throughput vs load
- Delivery ratio vs load
- Approximate congestion onset

This is more informative than one single bar chart because it shows *where the network stops scaling well*.

## CLI simulation

Mesh:

```bash
python main.py --topology mesh --nodes 16 --cycles 500 --load 0.4 --traffic uniform
```

Hypercube:

```bash
python main.py --topology hypercube --nodes 16 --cycles 500 --load 0.4 --traffic uniform
```

## Batch experiment for final report

```bash
python -m interconnect.experiments \
  --nodes 4 16 64 256 \
  --loads 0.2 0.4 0.6 0.8 1.0 \
  --traffic uniform hotspot \
  --cycles 1000 \
  --repeats 5
```

Outputs:

```text
results/raw_results.csv
results/summary_results.csv
```

Generate report PNG graphs:

```bash
python -m interconnect.plot_results
```

## Theory used by the simulator

### 2D Mesh

For `P = k²` processors:

```text
Diameter       = 2(k - 1)
Maximum degree = 4
Physical links = 2k(k - 1)
```

Routing is **XY routing**: resolve X first, then Y.

### Hypercube

For `P = 2^d` processors:

```text
Dimension      = d = log2(P)
Diameter       = d
Node degree    = d
Physical links = P*d/2
```

Routing is **bit fixing**: each hop flips one differing address bit until the destination address is reached.

## Correct conclusion style

Do **not** conclude simply that one topology is always superior.

A stronger conclusion is:

> Hypercube generally reduces communication distance and can sustain traffic with lower latency because its graph diameter grows logarithmically, but this performance is obtained with a higher processor degree and more physical links. The 2D Mesh has regular low-degree wiring and is easier to implement physically, but routes grow longer and central links/routers can experience greater contention as network size and offered load increase.

## Tests

```bash
python -m pip install pytest
pytest -q
```

Current v2 test suite: **8 tests** covering topology behavior, routing paths, simulation accounting, and visualization helper logic.

## Advanced extensions for a future v3

- Torus as a third topology
- Adaptive routing vs deterministic routing
- Virtual channels
- Per-port router buffers
- Wormhole/flit-level switching
- Variable packet lengths
- Faulty processor/link injection and rerouting
- Energy-per-packet / power estimation
- Bisection bandwidth analysis
- NoC traffic patterns: transpose, bit-complement, shuffle, neighbor, tornado
