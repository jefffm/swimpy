from multiprocessing import Pipe

import pytest
from mock import MagicMock

from swimpy.app import Application
from swimpy.handlers import MessageHandler
from swimpy.model.message import MESSAGE_TYPES
from swimpy.model.node import Node


def create_mock_handler(name):
    return name, MagicMock(name=name, autospec=MessageHandler)


@pytest.fixture()
def node():
    return Node(node_id='asdf-id', addr='127.0.0.1', port=1337)


@pytest.fixture()
def mock_app(node):
    routes = map(create_mock_handler, MESSAGE_TYPES.keys())
    return Application(routes=routes, node=node, pipe=MagicMock(name='pipe', autospec=Pipe))


def test_app_init(mock_app):
    assert isinstance(mock_app, Application)
