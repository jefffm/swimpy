from __future__ import absolute_import

import logging
import random

import datetime
import msgpack
from tornado.gen import coroutine, with_timeout, Return, TimeoutError
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from tornado.locks import Event
from tornado.queues import Queue, QueueEmpty, QueueFull
from tornado.tcpclient import TCPClient

from swimpy.model.message import MESSAGE_TYPES, Ack, Ping, Alive, Dead, Suspect
from swimpy.model.node import State
from .constants import GOSSIP_PEERS, PING_TIMEOUT, ACK_PAYLOAD_SIZE

LOGGER = logging.getLogger(__name__)


class Application(object):
    def __init__(self, routes, node, pipe):
        """
        Application instantiates and registers handlers for each message type,
        and routes messages to the pre-instantiated instances of each message handler

        :param routes: list of tuples in the form of (<message type str>, <MessageHandler class>)
        :param node: Node instance of the local node
        :param pipe: Instance of multiprocessing.Pipe for communicating with the parent process
        """
        # We don't really have to worry about synchronization
        # so long as we're careful about explicit context switching
        self.nodes = {node.node_id: node}

        self.local_node = node
        self.handlers = {}

        self.tcpclient = TCPClient()

        self.gossip_inbox = Queue()
        self.gossip_outbox = Queue()

        self.sequence_number = 0

        if routes:
            self.add_handlers(routes)

        self.pipe = pipe
        self.ioloop = IOLoop.current()

        self.add_node_event = Event()

    def next_sequence_number(self):
        self.sequence_number += 1
        return self.sequence_number

    @coroutine
    def ping_random_node(self):
        node = yield self.get_random_node()
        LOGGER.debug('{} pinging random node: {}'.format(self.local_node.node_id,
                                                         node.node_id))
        try:
            yield self.ping(node)
        except TimeoutError:
            self.mark_suspect(node)

    @coroutine
    def add_node(self, node):
        if node.node_id not in self.nodes:
            LOGGER.debug('Adding node {} to {}'.format(node, self.nodes))
            self.add_node_event.set()
            self.nodes[node.node_id] = node
            LOGGER.debug('Added node {} to {}'.format(node, self.nodes))

    @coroutine
    def remove_node(self, node):
        if node.node_id in self.nodes:
            del self.nodes[node.node_id]

            other_nodes = yield self.get_other_nodes
            if not other_nodes:
                self.add_node_event.clear()

    def add_handlers(self, handlers):
        for message_type, handler_cls in handlers:
            assert message_type in MESSAGE_TYPES, (
                'Message type {!r} not found in MESSAGE TYPES {}'.format(
                    message_type,
                    MESSAGE_TYPES.keys()
                )
            )
            self.handlers[message_type] = handler_cls(self)

    def route_stream_message(self, stream, message_type, message):
        LOGGER.debug('{!r} received {} message from {!r}'.format(self, message_type, stream))
        message_cls = MESSAGE_TYPES[message_type]
        message_obj = message_cls(**message)

        handler = self.handlers[message_type]
        LOGGER.debug('Routing {} to {}'.format(message_type, handler))
        handler(stream, message_obj)

    @coroutine
    def send_message(self, stream, message):
        LOGGER.debug('Sending message {!r} to {}'.format(message.MESSAGE_TYPE, stream))
        try:
            yield stream.write(message.to_msgpack)
        except StreamClosedError:
            LOGGER.warn('Unable to send {} to {} - stream closed'.format(message.MESSAGE_TYPE, stream))

    @coroutine
    def _get_next_message(self, stream):
        # get the next message from the stream
        unpacker = msgpack.Unpacker()
        try:
            wire_bytes = yield with_timeout(
                datetime.timedelta(seconds=PING_TIMEOUT),
                stream.read_bytes(4096, partial=True)
            )
        except StreamClosedError:
            LOGGER.warn('Unable to get next message from {} - stream closed'.format(stream))
        else:
            unpacker.feed(wire_bytes)
            LOGGER.debug('Deserializing object from stream {}'.format(stream))
            message = unpacker.next()
            message.pop('type')
            raise Return(message)

    @coroutine
    def ping(self, node):
        """
        Ping a node

        :param node: Instance of Node to ping
        :returns: Boolean, True if successful/False if fail
        """
        host = node.addr
        port = node.port

        LOGGER.debug('pinging {}:{}'.format(host, port))
        ping = Ping(seqno=self.next_sequence_number(),
                    node=node,
                    sender=self.local_node)

        # Connect to the node
        try:
            stream = yield self.tcpclient.connect(host, port)
        except StreamClosedError:
            LOGGER.error('Unable to connect from {} to {} (pinging host)'.format(self.local_node.node_id, node.node_id))
            raise Return(False)

        try:
            # Send the ping
            LOGGER.debug('Sending {!r} to {!r}'.format(ping.MESSAGE_TYPE, node))
            yield self.send_message(stream, ping)

            # Wait for an ACK message in response
            LOGGER.debug('Getting next message from {}:{}'.format(host, port))
            message = yield self._get_next_message(stream)
            if message is None:
                raise Return(False)

            ack = Ack(**message)
            LOGGER.debug('Received {!r} from {!r} (response to {!r})'.format(ack.MESSAGE_TYPE,
                                                                             node.node_id,
                                                                             ping.MESSAGE_TYPE))

            # Check that the ACK sequence number matches the PING sequence number
            if ack.seqno == ping.seqno:
                LOGGER.debug('Sequence number matches. Node {} looks good to !'.format(node.node_id,
                                                                                       self.local_node.node_id))
                # Process the gossip messages tacked onto the ACK message's payload
                for message in ack.payload:
                    try:
                        self.gossip_inbox.put_nowait(message)
                    except QueueFull:
                        LOGGER.error('Unable to add {} message from {} to gossip inbox'.format(message.MESSAGE_TYPE,
                                                                                               node.node_id))
                # mark the node as ALIVE in self.nodes
                self.mark_alive(node)

                # Send gossip that this node is alive
                self.queue_gossip_send(
                    Alive(node=node, sender=self.local_node)
                )

                raise Return(True)
            else:
                raise Return(False)
        finally:
            stream.close()

    @coroutine
    def ack(self, stream, seqno):
        payload = []
        for _ in xrange(ACK_PAYLOAD_SIZE):
            try:
                gossip = self.gossip_outbox.get_nowait()
                payload.append(gossip)
            except QueueEmpty:
                break

        ack = Ack(seqno=seqno, payload=payload)
        LOGGER.debug('Trying to send ack: {}'.format(ack))
        try:
            yield stream.write(ack.to_msgpack)
        except StreamClosedError:
            LOGGER.error('Unable to connect from {} to stream (acking PING)'.format(self.local_node.node_id))
        LOGGER.debug('Sent ack to {}'.format(stream))

    @coroutine
    def _change_node_state(self, node, state):
        """
        Because Tornado has explicit context switching, we don't need to worry much about synchronization here
        """
        LOGGER.debug('{} knows about {}: {}'.format(self.local_node.node_id, node.node_id, state))
        self.add_node(node)
        self.nodes[node.node_id].state = state

    @coroutine
    def mark_alive(self, node):
        if node.node_id != self.local_node.node_id:
            LOGGER.debug('Marking {} ALIVE'.format(node.node_id))
            self._change_node_state(node, State.ALIVE)

    @coroutine
    def mark_dead(self, node):
        self._change_node_state(node, State.DEAD)

    @coroutine
    def mark_suspect(self, node):
        self._change_node_state(node, State.SUSPECT)

    @coroutine
    def ingest_gossip_inbox(self):
        while True:
            LOGGER.debug('checking inbox')
            message = yield self.gossip_inbox.get()
            LOGGER.debug('Received message {} from gossip inbox'.format(message.MESSAGE_TYPE))
            if message.MESSAGE_TYPE == Alive.MESSAGE_TYPE:
                self.mark_alive(message.sender)
                self.mark_alive(message.node)
                self.queue_gossip_send(message)
            elif message.MESSAGE_TYPE == Suspect.MESSAGE_TYPE:
                self.mark_alive(message.sender)
                self.mark_suspect(message.node)
                self.queue_gossip_send(message)
            elif message.MESSAGE_TYPE == Dead.MESSAGE_TYPE:
                self.mark_alive(message.sender)
                self.mark_dead(message.node)
                self.queue_gossip_send(message)

    @coroutine
    def queue_gossip_send(self, message):
        """
        If the message is gossipable, add it to the outbox
        """
        try:
            next_incarnation = message.next_incarnation
            next_incarnation.sender = self.local_node
        except message.MaxIncarnationsReached:
            LOGGER.debug('Max incarnations reached for {}! No gossip 4 u'.format(message.MESSAGE_TYPE))
        else:
            LOGGER.debug('Enqueuing {} gossips for {}'.format(GOSSIP_PEERS, message))
            for _ in xrange(GOSSIP_PEERS):
                yield self.gossip_outbox.put(next_incarnation)

    @coroutine
    def send_buffered_gossip(self):
        while True:
            random_node = yield self.get_random_node()
            message = yield self.gossip_outbox.get()
            LOGGER.debug('{} connecting to {} for gossip'.format(self.local_node, random_node))
            try:
                stream = yield self.tcpclient.connect(random_node.addr, random_node.port)
            except StreamClosedError:
                LOGGER.error('Unable to connect from {} to {} (sending gossip)'.format(self.local_node.node_id,
                                                                                       random_node.node_id))
                LOGGER.warning('Putting the gossip back on our queue')
                try:
                    self.gossip_outbox.put_nowait(message)
                except QueueFull:
                    LOGGER.error('Unable to put gossip back onto the queue. Giving up!')
            else:
                try:
                    LOGGER.debug('{} gossipping with {}'.format(self.local_node.node_id, random_node.node_id))
                    yield self.send_message(stream, message)
                finally:
                    stream.close()

    @coroutine
    def get_other_nodes(self, exclude=None):
        if exclude is None:
            exclude = (self.local_node,)

        exclude_node_ids = [n.node_id for n in exclude]

        raise Return([n for n in self.nodes if n not in exclude_node_ids])

    @coroutine
    def get_random_node(self, exclude=None):
        LOGGER.debug('Waiting for more nodes')
        yield self.add_node_event.wait()
        LOGGER.debug('Getting non-self random node')

        other_nodes = yield self.get_other_nodes(exclude=exclude)
        LOGGER.debug('{} got something! choices: {}'.format(self.local_node.node_id, other_nodes))
        assert other_nodes

        node_id = random.choice(other_nodes)
        raise Return(self.nodes[node_id])
