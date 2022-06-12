# Mina GraphQL
GraphQL Python Module

### Description
Generalized GraphQL query for the Mina Protocol to obtain data such as the number of peers, sending transactions, etc. It is forked from the GraphQL script provided by the Mina Protocol.

### Warning
Ideally, the GraphQL port is ideally only exposed to an internal network and not exposed to the rest of the world. If the port is exposed to the internet, utilize a proxy so that only a select subet of commands are available.

### How to Install
Assuming Python3 is installed, the required modules can be installed via:
```
pip3 install -r requirements
```

### Example:
An example GraphQL query is provided for obtaining the number of peers in the example.py
```
python3 example.py
```
#### Output:
```
{'host': '94.130.71.174', 'libp2pPort': 8302, 'peerId': '12D3KooWF7XX3RLnHBYSH3ykKEyX2Zvy1wRkWg8Ck4dTBkteAPBx'}
{'host': '213.133.109.6', 'libp2pPort': 8302, 'peerId': '12D3KooWBed9D51ZWMqhRsUQ9R5LfxhD3eGj7FSiVBpAmh92GPPG'}
...
{'host': '65.108.107.174', 'libp2pPort': 8302, 'peerId': '12D3KooWLXEpKq7B4pE9xDkGgEWa2dshfRatZvZBQuZB5q1jXXBv'}
```
