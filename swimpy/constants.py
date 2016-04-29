

# IP and port to listen on
BIND_ADDR = '127.0.0.1'
BIND_PORT = '1337'

# How long should we wait for client connections to close
# before closing them during shutdown?
SHUTDOWN_TIMEOUT = 10

# How many peers should we gossip to?
GOSSIP_PEERS = 3

# How many generations should we gossip to?
# 2 generations: node1 -> gossips to n peers -> node2 -> gossips -> node3
# 3 generations: node1 -> gossips to n peers -> node2 -> gossips -> node3 -> gossips -> node4
GOSSIP_GENERATIONS = 2

PING_TIMEOUT = 1
PING_INTERVAL = 0.5

# When sending an ack, we have an opportunity to tack on some gossip.
# How many messages should we attach?
ACK_PAYLOAD_SIZE = 1

