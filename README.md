

SWIMPY - gossip-based membership and failure detection
======================================================

Swimpy is a Python library which implements a gossip membership and failure
detection protocol based on the [SWIM
whitepaper](https://www.cs.cornell.edu/~asdas/research/dsn02-swim.pdf). Swimpy
will, given a list of seed nodes, attempt to join and maintain a list of all
non-failing members of the cluster. Lots of inspiration taken from Hashicorp's
[Memberlist](https://github.com/hashicorp/memberlist).

Example use:

```python
from swimpy import Runtime


# Create three swimpy Runtime objects
n1 = Node(node_id='node-1', addr='127.0.0.1', port=9000)
r1 = Runtime(routes=ROUTES, node=n1)

# Configure a list of seed nodes to send JOINs to on startup
n2 = Node(node_id='node-2', addr='127.0.0.1', port=9001)
r2 = Runtime(routes=ROUTES, node=n2, seed_nodes=[('127.0.0.1', 9000)])

n3 = Node(node_id='node-3', addr='127.0.0.1', port=9002)
r3 = Runtime(routes=ROUTES, node=n3, seed_nodes=[('127.0.0.1', 9001)])

try:
    r1.start()
    r2.start()
    r3.start()

    for runtime in [r1, r2, r3]:
        nodes_dict = runtime.nodes
        assert sorted(nodes_dict) == ['node-1', 'node-2', 'node-3']

finally:
    r1.stop()
    r2.stop()
    r3.stop()

```

Development
===========

1. Please update [the CHANGELOG](CHANGELOG.md)
2. Run unit tests via `py.test` or `python setup.py test`
3. Run integration tests via `py.test -m 'integration'`

## License

[MIT](http://opensource.org/licenses/MIT)
