from __future__ import absolute_import

import logging
from abc import ABCMeta, abstractmethod

from tornado.gen import coroutine

LOGGER = logging.getLogger(__name__)


class MessageHandler(object):
    """
    MessageHandlers receive a message and a reference to the sender's TCP stream,
    and make a decision about what to do with the message
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __call__(self, stream, message):
        pass

    def _log_message(self, message):
        LOGGER.debug(
            '{} received {}. {}'.format(
                self.app.local_node.node_id, message, self.app.nodes.keys()
            )
        )

    def __init__(self, app):
        self.app = app


class PingHandler(MessageHandler):
    @coroutine
    def __call__(self, stream, message):
        """
        If we receive a ping, send back an ack and gossip an ALIVE message for the sender
        """
        self._log_message(message)
        if message.node.node_id == self.app.local_node.node_id:
            self.app.ack(stream, message.seqno)
            if message.sender is not None:
                self.app.mark_alive(message.sender)
        else:
            LOGGER.error(
                'received ping intended for a different node: {}'.format(
                    message))


class PingReqHandler(MessageHandler):
    @coroutine
    def __call__(self, stream, message):
        """
        If we receive a ping-req, ping the host in the message
        If we get an ack, send an ack to the stream
        Otherwise, just close the stream.
        """
        self._log_message(message)
        ping_result = yield self.app.ping(message.target_node)
        if ping_result is True:
            self.app.ack(stream, message.seqno)


class AliveHandler(MessageHandler):
    @coroutine
    def __call__(self, stream, message):
        """
        If we get ALIVE, mark that node as ALIVE in our memberlist
        """
        self._log_message(message)
        self.app.mark_alive(message.sender)
        self.app.mark_alive(message.node)
        self.app.queue_gossip_send(message)


class SuspectHandler(MessageHandler):
    @coroutine
    def __call__(self, stream, message):
        """
        If we get SUSPECT, mark that node as SUSPECT in our memberlist
        """
        self._log_message(message)
        self.app.mark_alive(message.sender)
        self.app.mark_suspect(message.node)
        self.app.queue_gossip_send(message)


class DeadHandler(MessageHandler):
    @coroutine
    def __call__(self, stream, message):
        """
        If we get DEAD, mark that node as DEAD in our memberlist
        """
        self._log_message(message)
        self.app.mark_alive(message.sender)
        self.app.mark_dead(message.node)
        self.app.queue_gossip_send(message)
