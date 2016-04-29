[![Build Status](https://travis-ci.org/jefffm/swimpy.svg?branch=master)](https://travis-ci.org/jefffm/swimpy)



SWIMPY - gossip-based membership and failure detection
======================================================

Swimpy is a Python library which implements a gossip membership and failure
detection protocol based on the [SWIM whitepaper][]. Swimpy will, given a list
of seed nodes, attempt to join and maintain a list of all non-failing members of
the cluster. Lots of inspiration taken from Hashicorp's [Memberlist][].

Swimpy talks to other nodes using msgpack RPC over TCP sockets, via nonblocking
io (Tornado). While there hasn't yet been any benchmarking, it seems very
snappy.

The `swimpy.runtime.Runtime.start()` method forks a child process that handles
the SWIM backend asynchronously. Consumers of this libary don't need to worry
about the Tornado ioloop, and can be written with basically any framework.


[SWIM whitepaper]: https://www.cs.cornell.edu/~asdas/research/dsn02-swim.pdf 
[Memberlist]: https://github.com/hashicorp/memberlist


```python
from swimpy import Runtime


# Create three swimpy Runtime objects
n1 = Node(node_id='node-1', addr='127.0.0.1', port=9000)
r1 = Runtime(routes=ROUTES, node=n1)

# Configure a list of seed nodes to join on startup
n2 = Node(node_id='node-2', addr='127.0.0.1', port=9001)
r2 = Runtime(routes=ROUTES, node=n2, seed_nodes=[('127.0.0.1', 9000)])

n3 = Node(node_id='node-3', addr='127.0.0.1', port=9002)
r3 = Runtime(routes=ROUTES, node=n3, seed_nodes=[('127.0.0.1', 9001)])

try:
    r1.start()
    r2.start()
    r3.start()

    # Verify that the cluster has converged
    for runtime in [r1, r2, r3]:
        nodes_dict = runtime.nodes
        assert sorted(nodes_dict) == ['node-1', 'node-2', 'node-3']

finally:
    r1.stop()
    r2.stop()
    r3.stop()

```

TODOs
==============

### network optimization
- [x] Pings are sent at fuzzy intervals (ie. jitter)
- [ ] Add support for UDP handlers
- [ ] Migrate gossip dissemination to UDP

### failure detection
- [x] Nodes ping each other regularly
- [x] Nodes check that PINGs and ACKs have matching sequence numbers
- [x] Nodes attach gossip messages to ACK replies
- [x] Nodes add new ALIVE nodes from their node list
- [x] Nodes mark nodes failing pings as SUSPECT
- [ ] Nodes ask peers to doublecheck SUSPECT nodes
- [ ] Nodes mark SUSPECT nodes failing pings as DEAD
- [ ] Nodes remove DEAD nodes from their node list

### dissemination and discovery
- [x] Nodes can advertise themselves to other nodes
- [x] Nodes receive and disseminate membership data via gossip
- [x] Nodes learn about other nodes indirectly via dissemination

### testing
- [x] Unit test coverage > 50%
- [ ] Unit test coverage > 80%
- [ ] Unit test coverage, 100%
- [x] Integration tests > 50%
- [x] Integration tests > 80%
- [ ] Integration tests, 100%

Development
===========

1. Please update [the CHANGELOG](CHANGELOG.md)
2. Create a virtualenv and run `python setup.py develop`
3. Run unit tests via `py.test` or `python setup.py test`
4. Run integration tests via `py.test -m 'integration'`

## License

[MIT](http://opensource.org/licenses/MIT)
