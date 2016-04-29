from time import sleep
import logging

from flaky import flaky
import pytest

from swimpy.routes import ROUTES
from swimpy.model.message import Ping, Ack, PingReq, Alive
from swimpy.model.node import Node
from swimpy.runtime import Runtime
from swimpy.util import send_message

LOGGER = logging.getLogger(__name__)


@pytest.mark.timeout(10)
@pytest.mark.integration()
def test_runtime_responds_to_ping():
    n1 = Node(node_id='node-1', addr='127.0.0.1', port=1338)
    r = Runtime(routes=ROUTES, node=n1)
    try:
        r.start()
        sleep(1)

        assert r.is_alive()

        ping = Ping(seqno=55, node=n1)
        ack = send_message(n1.addr, n1.port, ping, reply_cls=Ack)[0]

        # Make sure the sequence numbers match
        assert ack.seqno == ping.seqno

    finally:
        r.stop()


@pytest.mark.timeout(10)
@pytest.mark.integration()
def test_runtime_responds_to_pingreq():
    n1 = Node(node_id='node-1', addr='127.0.0.1', port=9000)
    r1 = Runtime(routes=ROUTES, node=n1)

    n2 = Node(node_id='node-2', addr='127.0.0.1', port=9001)
    r2 = Runtime(routes=ROUTES, node=n2)
    try:
        LOGGER.info('Starting node1')
        r1.start()

        LOGGER.info('Starting node2')
        r2.start()

        sleep(1)

        assert r1.is_alive()
        assert r2.is_alive()

        LOGGER.info('node1 and node2 are alive')

        # Send a ping-req to node-1 for node-2 and wait for an ack
        pingreq = PingReq(seqno=101, node=n1, target_node=n2)
        ack = send_message(n1.addr, n1.port, pingreq, reply_cls=Ack)[0]
        # Make sure the sequence numbers match
        assert ack.seqno == pingreq.seqno

    finally:
        r1.stop()
        r2.stop()


@flaky
@pytest.mark.timeout(15)
@pytest.mark.parametrize('num_nodes,deadline', [
    (3, 1),
    (12, 7),
])
@pytest.mark.integration()
def test_join(num_nodes, deadline):
    """
    Test that we're able to join <num_nodes> into a cluster within <deadline> secs

    This *usually* passes, but the flaky decorator will retry in the improbable
    case it does fail
    """
    nodes = {}
    runtimes = {}
    port = 10090

    for i in xrange(num_nodes):
        node_id = 'node-{}'.format(i)
        nodes[node_id] = Node(node_id=node_id, addr='127.0.0.1', port=port + i)
        runtimes[node_id] = Runtime(routes=ROUTES, node=nodes[node_id])
    try:
        for runtime in runtimes.values():
            runtime.start()

        sleep(1)

        for node_id, runtime in runtimes.iteritems():
            assert runtime.is_alive()
            LOGGER.info('{} is alive'.format(node_id))

        node_ids = nodes.keys()

        for i, node_id in enumerate(node_ids[:-1]):
            next_node_id = node_ids[i + 1]
            alive = Alive(node=nodes[next_node_id], sender=nodes[next_node_id])
            node = nodes[node_id]
            send_message(node.addr, node.port, alive)

        LOGGER.info('Sleeping for {} seconds'.format(deadline))
        sleep(deadline)

        for node_id in nodes:
            for runtime in runtimes.values():
                LOGGER.info('checking if {} is in runtime {}'.format(node_id, runtime.nodes.keys()))
                assert node_id in runtime.nodes.keys()  # .keys() gives us better debug output

    finally:
        LOGGER.info('Shutting down runtimes')
        for runtime in runtimes.values():
            runtime.stop()


@pytest.mark.timeout(15)
@pytest.mark.integration()
def test_join_with_seed_nodes():
    # Create three swimpy Runtime objects
    n1 = Node(node_id='node-1', addr='127.0.0.1', port=9900)
    r1 = Runtime(routes=ROUTES, node=n1)

    # Configure a list of seed nodes to send JOINs to on startup
    n2 = Node(node_id='node-2', addr='127.0.0.1', port=9901)
    r2 = Runtime(routes=ROUTES, node=n2, seed_nodes=[('127.0.0.1', 9900)])

    n3 = Node(node_id='node-3', addr='127.0.0.1', port=9902)
    r3 = Runtime(routes=ROUTES, node=n3, seed_nodes=[('127.0.0.1', 9901)])

    try:
        r1.start()
        sleep(1)

        r2.start()
        sleep(1)

        r3.start()
        sleep(1)

        for runtime in [r1, r2, r3]:
            nodes_dict = runtime.nodes
            LOGGER.info('Checking {} for all three nodes'.format(runtime))
            assert sorted(nodes_dict) == ['node-1', 'node-2', 'node-3']
    except Exception as e:
        LOGGER.exception(e)

    finally:
        try:
            r1.stop()
            r2.stop()
            r3.stop()
        except Exception as e:
            LOGGER.exception(e)
            raise
