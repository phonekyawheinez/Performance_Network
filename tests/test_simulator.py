from interconnect import InterconnectSimulator, SimulationConfig, TrafficConfig, make_topology


def test_simulator_delivers_packets():
    topology = make_topology("mesh", 16)
    config = SimulationConfig(
        cycles=100,
        injection_rate=0.1,
        queue_limit=64,
        seed=1,
        traffic=TrafficConfig(pattern="uniform"),
    )
    result = InterconnectSimulator(topology, config).run()
    assert result.generated_packets > 0
    assert result.delivered_packets > 0
    assert result.average_hops > 0
    assert 0 <= result.delivery_ratio <= 1
