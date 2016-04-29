import logging
import socket

import msgpack
import select

LOGGER = logging.getLogger(__name__)


def recvall(sock, cls):
    unpacker = msgpack.Unpacker()
    while select.select([sock], [], [], 0.1)[0]:  # while select has readable sockets (first field)
        buf = sock.recv(4096)
        unpacker.feed(buf)
        for o in unpacker:
            LOGGER.debug('got {} from stream'.format(o))
            o.pop('type')
            yield cls(**o)


def send_message(host, port, message, reply_cls=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
        sock.send(message.to_msgpack)

        if reply_cls:
            return list(recvall(sock, reply_cls))
    finally:
        sock.close()
