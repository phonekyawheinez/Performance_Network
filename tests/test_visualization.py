from interconnect.topologies import Hypercube, Mesh2D
from interconnect.visualization import average_pair_distance, route_nodes


def test_mesh_route_nodes():
    topo = Mesh2D(16)
    path = route_nodes(topo, 0, 15)
    assert path[0] == 0 and path[-1] == 15
    assert len(path) - 1 == 6


def test_hypercube_route_nodes():
    topo = Hypercube(16)
    path = route_nodes(topo, 0, 15)
    assert path[0] == 0 and path[-1] == 15
    assert len(path) - 1 == 4


def test_average_distance_hypercube_less_than_mesh_for_16():
    assert average_pair_distance(Hypercube(16)) < average_pair_distance(Mesh2D(16))
