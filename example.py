## Example of collecting the peers

from MinaClient import Client

# GraphQL Host
graphql_host = "127.0.0.1"
graphql_port = "3085"

# get the client
client = Client( graphql_host=graphql_host, graphql_port=graphql_port )

# get the peers
for peer in client.get_peers()['getPeers']:
    print(peer)