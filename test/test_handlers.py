import pytest
from mock import MagicMock
from tornado.iostream import IOStream

from swimpy.app import Application
from swimpy.handlers import PingHandler
from swimpy.model.message import Ping
from swimpy.model.node import Node, State


@pytest.fixture()
def node():
    return Node(node_id='asdf-id', addr='127.0.0.1', port=1337)


@pytest.fixture()
def ping_handler():
    return PingHandler(MagicMock(name='app',
                                 autospec=Application))


@pytest.fixture()
def ping_msg(node):
    return Ping(seqno=1, node=node)


@pytest.fixture()
def stream():
    return MagicMock(name='stream', autospec=IOStream)


def test_ping_handler_sends_ack_when_node_id_matches(ping_handler, ping_msg, stream):
    ping_msg.node.node_id = mock_node_id = 'asdf-id'
    ping_handler.app.local_node.node_id = mock_node_id

    ping_handler(stream, ping_msg)
    ping_handler.app.ack.assert_called_once_with(stream, ping_msg.seqno)
