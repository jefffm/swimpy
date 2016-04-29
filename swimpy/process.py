from __future__ import absolute_import

import logging
import multiprocessing
import signal
import sys

import msgpack
from tornado.ioloop import PeriodicCallback

from .app import Application
from .constants import (
    PING_INTERVAL,
    SHUTDOWN_TIMEOUT,
)
from .model.message import Sync
from .server import Server
from .tornado.splay_callback import PeriodicCallbackWithSplay


LOGGER = logging.getLogger(__name__)


class SwimpyProcess(multiprocessing.Process):
    def __init__(self, routes, node, pipe, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.routes = routes
        self.node = node
        self.pipe = pipe

        self.bind_addr = node.addr
        self.bind_port = node.port

        # We don't want to initialize these until after we fork
        self.ioloop = None
        self.server = None
        self.app = None

    def _handle_pipe_messages(self, *args, **kwargs):
        message = self.pipe.recv()
        unpacked_message = msgpack.unpackb(message)
        message_type = unpacked_message.pop('type')
        if message_type == Sync.MESSAGE_TYPE:
            self.pipe.send(self.app.nodes)

    def run(self):
        signal.signal(signal.SIGTERM, self.shutdown_sig_handler)
        signal.signal(signal.SIGINT, self.shutdown_sig_handler)

        from tornado.ioloop import IOLoop
        self.ioloop = IOLoop().current()  # get a reference to the IOLoop post-fork

        LOGGER.info('Starting server on tcp://{}:{}'.format(self.bind_addr, self.bind_port))
        self.app = Application(routes=self.routes, node=self.node, pipe=self.pipe)
        self.server = Server(message_handler=self.app.route_stream_message)
        self.server.listen(self.bind_port, address=self.bind_addr)

        self.ioloop.add_handler(self.pipe, self._handle_pipe_messages, self.ioloop.READ)
        self.ioloop.spawn_callback(self.app.send_buffered_gossip)

        # Ping a random node every PING_INVERVAL seconds, +/- 10%
        # This jitter should reduce the average aggregate peak network throughput
        # when running with large cluster sized
        PeriodicCallbackWithSplay(self.app.ping_random_node,
                                  PING_INTERVAL * 1000,
                                  splay_pct=10).start()

        LOGGER.info('Starting ioloop')
        self.ioloop.start()

    def stop(self, shutdown_timeout=SHUTDOWN_TIMEOUT, graceful=True):
        """
        Trigger a graceful stop of the server and the server's ioloop, allowing in-flight
        connections to finish

        Fall back to a "less graceful" stop when stop is reached
        """
        def poll_stop():
            # Tornado uses a "waker" handler internally that we'd like to ignore here
            remaining_handlers = {
                k: v
                for k, v in self.ioloop._handlers.iteritems()
                if k != self.ioloop._waker.fileno()
            }

            # Poll for any remaining connections
            remaining_count = len(remaining_handlers)

            # Once all handlers have been removed, we can stop safely
            if remaining_count == 0:
                LOGGER.info('All finished! Graceful stop complete')
                self.ioloop.stop()
            else:
                LOGGER.info('Waiting on IO handlers ({} remaining). '
                            'Handlers: {!r}'.format(remaining_count,
                                                    remaining_handlers))

        self.ioloop.remove_handler(self.pipe)
        self.server.shutdown()
        self.server.stop()

        if graceful:
            # Poll the IOLoop's handlers until they all shut down.
            poller = PeriodicCallback(poll_stop, 500, io_loop=self.ioloop)
            poller.start()
            self.ioloop.add_timeout(self.ioloop.time() + shutdown_timeout,
                                    self.ioloop.stop)
        else:
            self.ioloop.stop()

    def shutdown_sig_handler(self, sig, frame):
        """
        Signal handler for "stop" signals (SIGTERM, SIGINT)
        """
        LOGGER.warning('{!r} caught signal {!r}! Shutting down'.format(self, sig))

        try:
            self.ioloop.add_callback_from_signal(self.stop)
        except Exception as e:
            LOGGER.error(
                'Encountered exception while shutting down: {}'.format(e)
            )
            sys.exit(1)