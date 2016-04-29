import inspect

import msgpack
from booby.fields import Integer, Embedded, Collection

from swimpy.constants import GOSSIP_GENERATIONS
from swimpy.model.base import BaseModel
from swimpy.model.node import Node


class Message(BaseModel):
    MESSAGE_TYPE = None

    @property
    def to_msgpack(self):
        data = dict(self)
        data['type'] = self.MESSAGE_TYPE
        return msgpack.dumps(data)


class Ping(Message):
    """ Are you alive? """
    MESSAGE_TYPE = 'ping'
    seqno = Integer(required=True)
    node = Embedded(Node, required=True)
    sender = Embedded(Node)

    def __str__(self):
        return '<{} {} seqno: {}>'.format(self.MESSAGE_TYPE.upper(),
                                          self.node,
                                          self.seqno)


class PingReq(Message):
    """ Hey, can you check if this guy is alive? """
    MESSAGE_TYPE = 'ping-req'

    seqno = Integer(required=True)
    node = Embedded(Node, required=True)
    target_node = Embedded(Node, required=True)

    def __str__(self):
        return '<{} {} from {} seqno: {}>'.format(self.MESSAGE_TYPE.upper(),
                                                  self.target_node,
                                                  self.node,
                                                  self.seqno)


class Sync(Message):
    """ Sync state with me plz! (currently only used for IPC) """
    MESSAGE_TYPE = 'sync'

    seqno = Integer(required=True)
    node = Embedded(Node, required=True)
    sender = Embedded(Node, required=True)


class GossipMessage(Message):
    MAX_INCARNATIONS = GOSSIP_GENERATIONS

    def __str__(self):
        return '<{} {} (from {}) {} of {}>'.format( self.MESSAGE_TYPE.upper(),
                                                    self.node.node_id,
                                                    self.sender.node_id,
                                                    self.incarnation,
                                                    self.MAX_INCARNATIONS)

    node = Embedded(Node, required=True)
    sender = Embedded(Node, required=True)
    incarnation = Integer(default=0)

    class MaxIncarnationsReached(Exception):
        pass

    @property
    def next_incarnation(self):
        if self.incarnation < self.MAX_INCARNATIONS:
            self.incarnation += 1
            return self
        else:
            raise self.MaxIncarnationsReached(self)


class Suspect(GossipMessage):
    MESSAGE_TYPE = 'suspect'


class Alive(GossipMessage):
    MESSAGE_TYPE = 'alive'


class Dead(GossipMessage):
    MESSAGE_TYPE = 'dead'


class Ack(Message):
    MESSAGE_TYPE = 'ack'

    seqno = Integer(required=True)
    payload = Collection(GossipMessage)


def _get_subclasses(cls):
    """
    Recursively iterate over all non-abstract subclasses from a given pipe class
    """
    if not inspect.isabstract(cls):
        yield cls

    for subcls in cls.__subclasses__():
        for cls in _get_subclasses(subcls):
            yield cls


MESSAGE_TYPES = {}


for message_cls in _get_subclasses(Message):
    MESSAGE_TYPES[message_cls.MESSAGE_TYPE] = message_cls
