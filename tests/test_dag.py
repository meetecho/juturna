from juturna.components._dag import DAG
import pytest

def test_add_node():
    dag = DAG()
    dag.add_node('node_a')

    assert dag._adj['node_a'] == set()

def test_add_edge():
    dag = DAG()
    dag.add_node('node_a')
    dag.add_node('node_b')
    dag.add_edge('node_a', 'node_b')

    assert ('node_a', 'node_b') in dag.edges
    assert 'node_b' in dag._adj['node_a']
    assert dag._adj['node_b'] == set()
    
def test_add_edge_missing_destination():
    dag = DAG()
    dag.add_node('node_a')

    with pytest.raises(ValueError):
        dag.add_edge('node_a', 'node_b')  # node_b not added yet

def test_add_edge_missing_source():
    dag = DAG()
    dag.add_node('node_b')

    with pytest.raises(ValueError):
        dag.add_edge('node_a', 'node_b')  # node_a not added yet
                    
def test_has_cycle():
    dag = DAG()
    dag.add_node('node_a')
    dag.add_node('node_b')
    dag.add_edge('node_a', 'node_b')
    dag.add_edge('node_b', 'node_a')  # creates a cycle

    assert dag.has_cycle() is True

def test_has_complex_cycle():
    dag = DAG()
    dag.add_node('node_a')
    dag.add_node('node_b')
    dag.add_node('node_c')
    dag.add_edge('node_a', 'node_b')
    dag.add_edge('node_b', 'node_c')
    dag.add_edge('node_c', 'node_a')  # creates a cycle

    assert dag.has_cycle() is True
    
def test_no_cycle():
    dag = DAG()
    dag.add_node('node_a')
    dag.add_node('node_b')
    dag.add_edge('node_a', 'node_b')

    assert dag.has_cycle() is False
    
def test_bfs_layers():
    dag = DAG()
    dag.add_node('node_a')
    dag.add_node('node_b')
    dag.add_node('node_c')
    dag.add_edge('node_a', 'node_b')
    dag.add_edge('node_a', 'node_c')

    layers = dag.BFS()

    for layer in layers:
        layer.sort()
        
    assert layers == [['node_a'], ['node_b', 'node_c']]

def test_bfs_isolated_node():
    dag = DAG()
    dag.add_node('node_a')
    dag.add_node('node_b')
    dag.add_node('node_c')
    dag.add_edge('node_a', 'node_b')

    layers = dag.BFS()

    for layer in layers:
        layer.sort()

    assert layers == [['node_a', 'node_c'], ['node_b']]
    
def test_in_degree():
    dag = DAG()
    dag.add_node('node_a')
    dag.add_node('node_b')
    dag.add_edge('node_a', 'node_b')

    in_deg = dag.in_degree()
    assert in_deg['node_a'] == 0
    assert in_deg['node_b'] == 1

def test_out_degree():
    dag = DAG()
    dag.add_node('node_a')
    dag.add_node('node_b')
    dag.add_edge('node_a', 'node_b')

    out_deg = dag.out_degree()
    assert out_deg['node_a'] == 1
    assert out_deg['node_b'] == 0

def test_in_out_degree_complex():
    dag = DAG()
    dag.add_node('node_a')
    dag.add_node('node_b')
    dag.add_node('node_c')
    dag.add_edge('node_a', 'node_b')
    dag.add_edge('node_a', 'node_c')
    dag.add_edge('node_b', 'node_c')

    in_deg = dag.in_degree()
    out_deg = dag.out_degree()

    assert in_deg['node_a'] == 0
    assert in_deg['node_b'] == 1
    assert in_deg['node_c'] == 2

    assert out_deg['node_a'] == 2
    assert out_deg['node_b'] == 1
    assert out_deg['node_c'] == 0

def test_as_dict():
    dag = DAG()
    dag.add_node("node_a")
    dag.add_node("node_b")
    dag.add_edge("node_a", "node_b")
    
    result = dag.as_dict()
    
    assert "edges" in result
    assert "in_degree" in result
    assert "out_degree" in result
    assert "layers" in result
    
def test_as_dict_contents():
    dag = DAG()
    dag.add_node("node_a")
    dag.add_node("node_b")
    dag.add_edge("node_a", "node_b")
    
    result = dag.as_dict()
    
    assert result["edges"] == [("node_a", "node_b")]
    assert result["in_degree"] == {"node_a": 0, "node_b": 1}
    assert result["out_degree"] == {"node_a": 1, "node_b": 0}
    assert result["layers"] == [["node_a"], ["node_b"]]