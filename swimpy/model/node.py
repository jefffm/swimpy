import time

from booby.fields import String, Integer
from booby.models import Model


class State(object):
    """
    Here's an ASCII state diagram:

    fails ping   +-------+  fails indirect ping
         +------>|SUSPECT|-------+
         |       +---+---+       |
         |           ^ bad       v
     +---+---+       |         +----+
     |UNKNOWN|      ping       |DEAD|
     +---+---+       |         +----+
         |           v ok        ^
         |        +-----+        |
         +------->|ALIVE|--------+
     passes ping  +-----+   sends LEAVE

    """
    UNKNOWN = 'unknown'
    ALIVE = 'alive'
    SUSPECT = 'suspect'
    DEAD = 'dead'


class Node(Model):
    node_id = String(required=True)
    addr = String(required=True)
    port = Integer(required=True)
    incarnation = Integer(default=1)
    state = String(choices=[State.UNKNOWN,
                            State.ALIVE,
                            State.DEAD,
                            State.SUSPECT],
                   default=State.UNKNOWN)
    last_update = Integer(default=time.time())

    def __str__(self):
        return '<{} {} {}:{}>'.format(self.state.upper(),
                                      self.node_id,
                                      self.addr,
                                      self.port)
