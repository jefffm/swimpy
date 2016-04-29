from __future__ import absolute_import

from swimpy.handlers import (
    AliveHandler,
    DeadHandler,
    PingHandler,
    PingReqHandler,
    SuspectHandler,
)

ROUTES = [
    ['ping', PingHandler],
    ('ping-req', PingReqHandler),
    ('suspect', SuspectHandler),
    ('alive', AliveHandler),
    ('dead', DeadHandler),
]