from __future__ import annotations

import math
from statistics import mean

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from interconnect import InterconnectSimulator, SimulationConfig, TrafficConfig, make_topology
from interconnect.visualization import average_pair_distance, route_explanation, topology_figure

st.set_page_config(page_title="Interconnect Visual Lab", page_icon="🧠", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2.5rem; max-width: 1500px;}
.hero {padding: 1.2rem 1.4rem; border-radius: 18px; background: linear-gradient(120deg,#0f172a,#1e3a8a); color:white; margin-bottom: 1rem;}
.hero h1 {margin:0; font-size:2.15rem;} .hero p {margin:.35rem 0 0; opacity:.88;}
.info-card {border:1px solid rgba(148,163,184,.35); border-radius:14px; padding:1rem; min-height:118px;}
.small {font-size:.88rem; opacity:.8}
.route-box {border-left:5px solid #f59e0b; padding:.75rem 1rem; background:rgba(245,158,11,.08); border-radius:8px;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>Processor Interconnection Network — Visual Simulation Lab</h1>
<p>See how 2D Mesh and Hypercube processors connect, route packets, become congested, and scale under load.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Global network")
    nodes = st.selectbox("Processors", [4, 16, 64, 256], index=1, help="Use 16 while learning; 64/256 are better for scalability tests.")
    seed = st.number_input("Random seed", 0, 1_000_000, 42)
    st.divider()
    # st.markdown("**Recommended demo order**")
    # st.markdown("1. Topology Explorer\n2. Packet Route\n3. Congestion Trace\n4. Performance Lab\n5. Scalability Sweep")

mesh = make_topology("mesh", int(nodes))
hyper = make_topology("hypercube", int(nodes))


def pct_change(better: float, baseline: float) -> float:
    if baseline == 0:
        return 0.0
    return (better - baseline) / baseline * 100.0


def result_card(label: str, mesh_value: float, hyper_value: float, unit: str = "", lower_is_better: bool = True):
    if lower_is_better:
        winner = "Hypercube" if hyper_value < mesh_value else "Mesh" if mesh_value < hyper_value else "Tie"
    else:
        winner = "Hypercube" if hyper_value > mesh_value else "Mesh" if mesh_value > hyper_value else "Tie"
    st.markdown(
        f"<div class='info-card'><b>{label}</b><br><span style='font-size:1.35rem'>Mesh {mesh_value:.2f}{unit}</span>"
        f"<br><span style='font-size:1.35rem'>Hypercube {hyper_value:.2f}{unit}</span>"
        f"<br><span class='small'>Best: <b>{winner}</b></span></div>",
        unsafe_allow_html=True,
    )


def run_sim(topology_name: str, n: int, cycles: int, load: float, traffic: str, queue: int, link_capacity: int, collect_trace=False):
    topo = make_topology(topology_name, n)
    cfg = SimulationConfig(
        cycles=cycles,
        injection_rate=load,
        queue_limit=queue,
        link_capacity=link_capacity,
        seed=int(seed),
        traffic=TrafficConfig(pattern=traffic),
        collect_trace=collect_trace,
    )
    sim = InterconnectSimulator(topo, cfg)
    result = sim.run()
    return result, sim


@st.cache_data(show_spinner=False)
def cached_sweep(n: int, traffic: str, cycles: int, queue: int, seed_value: int, link_capacity: int):
    rows = []
    for load in np.linspace(0.05, 1.0, 12):
        for topo_name in ("mesh", "hypercube"):
            topo = make_topology(topo_name, n)
            cfg = SimulationConfig(
                cycles=cycles,
                injection_rate=float(load),
                queue_limit=queue,
                link_capacity=link_capacity,
                seed=seed_value,
                traffic=TrafficConfig(pattern=traffic),
            )
            row = InterconnectSimulator(topo, cfg).run().as_dict()
            rows.append(row)
    return pd.DataFrame(rows)


tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "① Topology Explorer", "② Packet Route", "③ Congestion Trace",
    "④ Performance Lab", "⑤ Scalability Sweep", "⑥ Concepts & Report"
])

with tab1:
    st.subheader("What does each network actually look like?")
    st.write("Start here. The diagrams are interactive: hover over a processor to see its address, degree, and neighbors.")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(topology_figure(mesh, title=f"2D Mesh — {nodes} processors"), use_container_width=True)
    with c2:
        st.plotly_chart(topology_figure(hyper, title=f"Hypercube — {nodes} processors"), use_container_width=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1: result_card("Network diameter", mesh.diameter, hyper.diameter, " hops", True)
    with m2: result_card("Average pair distance", average_pair_distance(mesh), average_pair_distance(hyper), " hops", True)
    with m3: result_card("Physical links", mesh.total_links, hyper.total_links, "", True)
    with m4: result_card("Average node degree", mesh.average_degree, hyper.average_degree, "", True)

    st.info(
        "**Key idea:** Mesh keeps each processor's wiring small and regular. Hypercube gives every processor more direct dimensions to travel through, "
        "which usually shortens routes but increases connection cost."
    )

with tab2:
    st.subheader("Follow one packet hop by hop")
    route_topology_name = st.radio("Network", ["2D Mesh", "Hypercube"], horizontal=True)
    route_topo = mesh if route_topology_name == "2D Mesh" else hyper
    a, b = st.columns(2)
    with a:
        source = st.selectbox("Source processor", list(range(nodes)), index=0, format_func=lambda x: f"P{x}")
    with b:
        default_dest = min(nodes - 1, 15)
        destination = st.selectbox("Destination processor", list(range(nodes)), index=default_dest, format_func=lambda x: f"P{x}")
    if source == destination:
        st.warning("Choose different source and destination processors.")
    else:
        path = route_topo.route(int(source), int(destination))
        step = st.slider("Packet position", 0, len(path) - 1, 0, 1, help="Move this slider to advance the packet one router at a time.")
        left, right = st.columns([1.65, 1])
        with left:
            st.plotly_chart(topology_figure(route_topo, path=path, current_step=step, title=f"Route: P{source} → P{destination}"), use_container_width=True)
        with right:
            st.markdown(f"### Route length: **{len(path)-1} hops**")
            st.code(" → ".join(f"P{x}" for x in path), language=None)
            st.markdown(f"<div class='route-box'>{route_explanation(route_topo, path, step)}</div>", unsafe_allow_html=True)
            st.progress(step / (len(path) - 1))
            st.write(f"Current processor: **P{path[step]}**")
            st.write(f"Remaining hops: **{len(path)-1-step}**")
            if route_topology_name == "Hypercube":
                st.caption("Hypercube labels include the processor's binary address. Every hop flips one differing bit.")
            else:
                st.caption("Mesh uses XY routing: finish horizontal movement first, then vertical movement.")

with tab3:
    st.subheader("See congestion build up inside router queues")
    c1, c2, c3, c4 = st.columns(4)
    with c1: trace_topo_name = st.selectbox("Topology", ["mesh", "hypercube"], key="trace_topo")
    with c2: trace_load = st.slider("Injection rate", 0.05, 1.0, 0.65, 0.05, key="trace_load")
    with c3: trace_cycles = st.slider("Cycles", 40, 300, 120, 20, key="trace_cycles")
    with c4: trace_queue = st.select_slider("Queue limit", [4, 8, 16, 32, 64], value=16, key="trace_queue")
    traffic_trace = st.radio("Traffic pattern", ["uniform", "hotspot"], horizontal=True, key="trace_traffic")

    if st.button("Run congestion trace", type="primary"):
        with st.spinner("Tracing queues and link use..."):
            res, sim = run_sim(trace_topo_name, int(nodes), trace_cycles, trace_load, traffic_trace, trace_queue, 1, True)
        st.session_state["trace_res"] = res.as_dict()
        st.session_state["trace_snapshots"] = sim.trace
        st.session_state["trace_topology"] = trace_topo_name

    if "trace_snapshots" in st.session_state:
        snaps = st.session_state["trace_snapshots"]
        trace_df = pd.DataFrame([s.as_dict() for s in snaps])
        res = st.session_state["trace_res"]
        qdepth = np.array([s.queue_depths for s in snaps]).T

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Generated", f"{res['generated_packets']:,}")
        k2.metric("Delivered", f"{res['delivered_packets']:,}", f"{res['delivery_ratio']*100:.1f}%")
        k3.metric("Dropped", f"{res['dropped_packets']:,}", f"{res['drop_ratio']*100:.1f}%")
        k4.metric("Average latency", f"{res['average_latency']:.2f} cycles")

        line = px.line(trace_df, x="cycle", y=["average_queue", "max_queue"], title="Queue buildup over simulation cycles")
        line.update_layout(yaxis_title="Packets waiting in router", legend_title_text="Queue metric")
        st.plotly_chart(line, use_container_width=True)

        heat = go.Figure(data=go.Heatmap(z=qdepth, x=[s.cycle for s in snaps], y=[f"P{i}" for i in range(qdepth.shape[0])], colorscale="YlOrRd"))
        heat.update_layout(title="Router queue heatmap — where congestion occurs", xaxis_title="Cycle", yaxis_title="Processor", height=max(420, min(900, 16 * int(nodes))))
        st.plotly_chart(heat, use_container_width=True)

        avg_q = {i: float(qdepth[i].mean()) for i in range(qdepth.shape[0])}
        topo = make_topology(st.session_state["trace_topology"], int(nodes))
        st.plotly_chart(topology_figure(topo, node_values=avg_q, title="Average congestion mapped back onto the network"), use_container_width=True)
        st.caption("Yellow/red processors accumulated longer queues. This helps show *where* routing contention concentrates, not only the final latency number.")
    else:
        st.info("Run a trace. For an obvious congestion example, try 16 processors, load 0.65–0.90, queue limit 8 or 16.")

with tab4:
    st.subheader("Run the same workload on both networks")
    c1, c2, c3, c4 = st.columns(4)
    with c1: perf_load = st.slider("Injection rate", 0.05, 1.0, 0.45, 0.05, key="perf_load")
    with c2: perf_cycles = st.number_input("Cycles", 100, 3000, 500, 100, key="perf_cycles")
    with c3: perf_queue = st.select_slider("Queue limit", [4, 8, 16, 32, 64, 128], value=32, key="perf_queue")
    with c4: perf_capacity = st.selectbox("Link capacity", [1, 2, 4], key="perf_capacity")
    perf_traffic = st.radio("Traffic pattern", ["uniform", "hotspot"], horizontal=True, key="perf_traffic")

    if st.button("Compare Mesh vs Hypercube", type="primary"):
        with st.spinner("Running identical workloads..."):
            rows = []
            for name in ("mesh", "hypercube"):
                r, _ = run_sim(name, int(nodes), int(perf_cycles), perf_load, perf_traffic, perf_queue, perf_capacity)
                rows.append(r.as_dict())
        st.session_state["perf_results"] = pd.DataFrame(rows)

    if "perf_results" in st.session_state:
        df = st.session_state["perf_results"]
        mesh_r = df[df.topology == "2D Mesh"].iloc[0]
        hyper_r = df[df.topology == "Hypercube"].iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        with c1: result_card("Average latency", mesh_r.average_latency, hyper_r.average_latency, " cycles", True)
        with c2: result_card("Throughput", mesh_r.throughput_packets_per_cycle, hyper_r.throughput_packets_per_cycle, " pkt/cycle", False)
        with c3: result_card("Delivery ratio", mesh_r.delivery_ratio*100, hyper_r.delivery_ratio*100, "%", False)
        with c4: result_card("Average hops", mesh_r.average_hops, hyper_r.average_hops, " hops", True)

        long_rows = []
        for _, row in df.iterrows():
            long_rows += [
                {"Topology": row.topology, "Metric": "Avg latency", "Value": row.average_latency},
                {"Topology": row.topology, "Metric": "P95 latency", "Value": row.p95_latency},
                {"Topology": row.topology, "Metric": "Avg hops", "Value": row.average_hops},
            ]
        comp = px.bar(pd.DataFrame(long_rows), x="Metric", y="Value", color="Topology", barmode="group", title="Delay and route-length comparison")
        st.plotly_chart(comp, use_container_width=True)

        ratios = pd.DataFrame([
            {"Topology": row.topology, "Delivery %": row.delivery_ratio*100, "Drop %": row.drop_ratio*100}
            for _, row in df.iterrows()
        ])
        ratiofig = px.bar(ratios, x="Topology", y=["Delivery %", "Drop %"], barmode="stack", title="Packet outcome")
        st.plotly_chart(ratiofig, use_container_width=True)

        latency_gain = -pct_change(hyper_r.average_latency, mesh_r.average_latency)
        link_cost = pct_change(hyper_r.total_links, mesh_r.total_links)
        st.markdown("### Automatic interpretation")
        if latency_gain > 0:
            st.success(f"For this workload, Hypercube reduces average latency by about **{latency_gain:.1f}%** relative to Mesh.")
        else:
            st.info(f"For this workload, Mesh has about **{-latency_gain:.1f}%** lower average latency.")
        st.warning(f"The trade-off is wiring complexity: Hypercube uses **{hyper_r.total_links:.0f} links** versus Mesh's **{mesh_r.total_links:.0f}**, a difference of {link_cost:.1f}%.")
        st.dataframe(df[["topology","generated_packets","delivered_packets","dropped_packets","pending_packets","average_latency","p95_latency","throughput_packets_per_cycle","average_hops","delivery_ratio","total_links","average_degree","network_diameter"]], hide_index=True, use_container_width=True)
    else:
        st.info("Run the comparison to generate measured results from the simulator.")

with tab5:
    st.subheader("Find the load where each topology starts to struggle")
    c1, c2, c3 = st.columns(3)
    with c1: sweep_traffic = st.selectbox("Traffic", ["uniform", "hotspot"], key="sweep_traffic")
    with c2: sweep_cycles = st.selectbox("Cycles per point", [150, 250, 400], index=1)
    with c3: sweep_queue = st.selectbox("Queue limit", [8, 16, 32, 64], index=2, key="sweep_queue")
    if st.button("Run 12-load sweep", type="primary"):
        with st.spinner("Running 24 simulations..."):
            st.session_state["sweep_df"] = cached_sweep(int(nodes), sweep_traffic, int(sweep_cycles), int(sweep_queue), int(seed), 1)

    if "sweep_df" in st.session_state:
        sdf = st.session_state["sweep_df"].copy()
        sdf["Load"] = sdf.injection_rate
        sdf["Delivery %"] = sdf.delivery_ratio * 100
        f1 = px.line(sdf, x="Load", y="average_latency", color="topology", markers=True, title="Latency vs offered load")
        f1.update_layout(yaxis_title="Average latency (cycles)")
        st.plotly_chart(f1, use_container_width=True)
        f2 = px.line(sdf, x="Load", y="throughput_packets_per_cycle", color="topology", markers=True, title="Throughput vs offered load")
        f2.update_layout(yaxis_title="Delivered packets / cycle")
        st.plotly_chart(f2, use_container_width=True)
        f3 = px.line(sdf, x="Load", y="Delivery %", color="topology", markers=True, title="Delivery ratio vs offered load")
        f3.update_layout(yaxis_title="Delivered packets (%)", yaxis_range=[0, 101])
        st.plotly_chart(f3, use_container_width=True)

        st.markdown("### Approximate congestion onset")
        cols = st.columns(2)
        for idx, topo_name in enumerate(["2D Mesh", "Hypercube"]):
            part = sdf[sdf.topology == topo_name].sort_values("Load")
            bad = part[(part.drop_ratio > 0.01) | (part.pending_packets > 0)]
            onset = float(bad.iloc[0].Load) if not bad.empty else None
            with cols[idx]:
                if onset is None:
                    st.success(f"**{topo_name}:** no >1% drop/pending threshold reached in tested loads.")
                else:
                    st.warning(f"**{topo_name}:** congestion symptoms begin around injection rate **{onset:.2f}** in this run.")
    else:
        st.info("This sweep is your strongest performance graph for the final report because it shows the transition from light load to saturation.")

with tab6:
    st.subheader("Concepts you can explain during presentation")
    left, right = st.columns(2)
    with left:
        st.markdown("""
### 2D Mesh
- Processor address: **(x, y)** coordinate.
- Router degree: at most **4**.
- Routing used here: **XY deterministic routing**.
- Diameter for a √N × √N mesh: **2(√N − 1)**.
- Advantage: regular, simple physical wiring.
- Limitation: paths grow longer as the network becomes larger.

### Performance metrics
- **Latency:** cycles between packet creation and delivery.
- **Throughput:** delivered packets divided by elapsed cycles.
- **Delivery ratio:** delivered / generated packets.
- **Hop count:** number of links crossed.
- **Queue depth:** packets waiting at a router; rising queues indicate congestion.
""")
    with right:
        st.markdown("""
### Hypercube
- Processor address: **d-bit binary number** where N = 2ᵈ.
- Two processors are neighbors if their addresses differ by **one bit**.
- Degree and diameter: **log₂(N)**.
- Routing used here: **bit fixing**.
- Advantage: short routes and many alternative dimensions.
- Limitation: connection degree grows with network size.

### Recommended conclusion
Do not say “Hypercube is always better.” State the trade-off: **Hypercube generally buys shorter communication paths with more links and wiring complexity, while Mesh is structurally simpler but can accumulate longer paths and congestion as scale/load rises.**
""")


