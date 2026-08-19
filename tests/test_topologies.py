from interconnect.topologies import Hypercube, Mesh2D


def test_mesh_distance_and_diameter():
    mesh = Mesh2D(16)
    assert mesh.distance(0, 15) == 6
    assert mesh.diameter == 6
    assert mesh.total_links == 24


def test_mesh_xy_routing_reaches_destination():
    mesh = Mesh2D(16)
    current = 0
    route = [current]
    while current != 15:
        current = mesh.next_hop(current, 15)
        route.append(current)
    assert len(route) - 1 == 6
    assert route[-1] == 15


def test_hypercube_distance_and_diameter():
    cube = Hypercube(16)
    assert cube.distance(0, 15) == 4
    assert cube.diameter == 4
    assert cube.total_links == 32


def test_hypercube_routing_reaches_destination():
    cube = Hypercube(16)
    current = 0
    route = [current]
    while current != 15:
        current = cube.next_hop(current, 15)
        route.append(current)
    assert len(route) - 1 == 4
    assert route[-1] == 15
