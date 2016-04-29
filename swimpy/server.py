from __future__ import absolute_import

import logging

import msgpack
from tornado.gen import coroutine
from tornado.iostream import StreamClosedError
from tornado.tcpserver import TCPServer

LOGGER = logging.getLogger(__name__)


class Server(TCPServer):
    def __init__(self, message_handler, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.message_handler = message_handler
        self.unpacker = msgpack.Unpacker(encoding='utf-8')
        self.clients = []

    @coroutine
    def handle_stream(self, stream, addr):
        """
        Called for each new connection, stream.socket is
        a reference to socket object
        """
        self.clients.append((stream, addr))
        try:
            while True:
                LOGGER.debug('Receiving on stream ({}, {})'.format(self, stream, addr))
                wire_bytes = yield stream.read_bytes(4096, partial=True)
                self.unpacker.feed(wire_bytes)
                for message in self.unpacker:
                    message_type = message.pop('type')
                    self.io_loop.spawn_callback(self.message_handler,
                                                stream=stream,
                                                message_type=message_type,
                                                message=message)
        except StreamClosedError:
            LOGGER.debug('client disconnected: {}'.format(addr))
            self.clients.remove((stream, addr))
            LOGGER.debug('clients: {!r}'.format(self.clients))
        except Exception as e:
            LOGGER.exception(e)
            self.clients.remove((stream, addr))
            LOGGER.debug('clients: {!r}'.format(self.clients))
            stream.close()

    def shutdown(self):
        LOGGER.info('Shutting down {!r}'.format(self))
        for client, addr in self.clients:
            client.close()
