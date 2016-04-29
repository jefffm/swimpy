

from swimpy.model.node import Node, State


def test_node():
    attrs = dict(node_id='a-node-id', addr='127.0.0.1', port='1337')
    n = Node(**attrs)
    for k, v in attrs.iteritems():
        assert dict(n)[k] == v
