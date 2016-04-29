from __future__ import absolute_import

import logging
import multiprocessing

from swimpy.model.message import Sync, Alive
from swimpy.process import SwimpyProcess
from swimpy.util import send_message

LOGFORMAT = '%(process)d\t%(name)s\t[%(levelname)s]\t%(message)s'
DATEFORMAT = '%a %b %d %H:%M:%S %Y %Z'

logging.basicConfig(level=logging.INFO, format=LOGFORMAT, datefmt=DATEFORMAT)
LOGGER = logging.getLogger(__name__)


class Runtime(object):
    def __init__(self, routes, node, seed_nodes=None):
        if seed_nodes is None:
            seed_nodes = []

        self.local_node = node
        self.pipe, child = multiprocessing.Pipe()
        self.process = SwimpyProcess(routes=routes, node=node, pipe=child)
        self.process.daemon = True
        self.seed_nodes = seed_nodes

    def start(self):
        LOGGER.info('Starting Swimpy child process')
        try:
            self.process.start()
        except Exception as e:
            LOGGER.exception(e)

        LOGGER.info('Attempt to join {} to seed nodes: {}'.format(self.local_node,
                                                                  self.seed_nodes))
        for host, port in self.seed_nodes:
            self.join(host, port)

    def is_alive(self):
        return self.process.is_alive()

    def stop(self):
        self.process.terminate()

    def join(self, host, port):
        """
        Given the address and port of a running Swimpy node,
        gossip an Alive message for the local node
        """
        message = Alive(node=self.local_node, sender=self.local_node)
        send_message(host, port, message)

    @property
    def nodes(self):
        self.pipe.send(Sync(node=self.local_node,
                            sender=self.local_node).to_msgpack)
        if self.pipe.poll(1):
            return self.pipe.recv()  # recv the next object and return it
        else:
            raise Exception
