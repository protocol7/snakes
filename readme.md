snakes is a very basic distributed key-value store. With snakes, you can run multiple nodes that are all able to act as read and write masters. Nodes will attempt to keep each other up-to-date. snakes is merely a prototype and therefore has many limitations. Below you will find a list of snakes basic features and limitations:

* snakes communicates over HTTP, both with clients and among nodes. To interact as a client, you issue simple HTTP requests.
* Keys must be alphanumeric strings
* Values should be strings of limited size (snakes will hold and compare values in-memory). The contents of the values are opaque to snakes, it can be anything (e.g. JSON, XML)
* snakes uses a very simple file storage. It uses one file per key. This keeps snakes simple but will not result in optimal performance as snakes will have to do a lot of seeks. SSD drives are recommended.
* snakes does not currently support any authentication. However, snakes is meant to be placed behind a reverse proxy (such as Apache httpd or Nginx) where authentication could be performed.
* snakes has very limited logging
* snakes does not support any form of transactions. However, a future improvement might support optimistic locking with the use of HTTP e-tags.
* snakes does not support partitioning
* Nodes in a snakes cluster will sync updated among themselves, but only as long as nodes are available. During node downtime or network partitions, nodes might get out-of-date. Nodes will not actively try to sync themselves after such an incident. Instead, snakes relies on clients to update values. snakes uses a simple quorum algorithm (last update wins) to determine which value to serve a client. A future improvement might provide the client with all existing values (and update times) to choose among in order to merge a conflict.

## Starting snakes
snakes is very simple to start. You can run as many nodes as you like. Each must have a unique IP address/port combination and a separate storage directory. To start three nodes on the same server, run:

    python3.1 snakes.py http://127.0.0.1:9001 http://127.0.0.1:9002
    python3.1 snakes.py -p 9001 -d data2 http://127.0.0.1:9000 http://127.0.0.1:9002
    python3.1 snakes.py -p 9002 -d data3 http://127.0.0.1:9000 http://127.0.0.1:9001

snakes requires Python 3.1.

snakes will default to running on port 9000 and use a data directory named "data". To provide a different port, use the -p option. To provide a different data directory, use the -d option. You must also provide the URLs for all other nodes in the cluster. A future update of snakes might instead use mDNS to automatically locate nodes in a cluster.

## Interacting as a client
To communicate with snakes you use simple HTTP requests. 

### Get a value
To get the value of a key, issue an HTTP GET request. The examples below uses curl, but any HTTP client can be used:

    curl http://localhost:9002/key

This request will return the value as the content of the response. If the key is not known to the cluster, a 404 response code will be returned. 

You can also configure how many nodes in the snakes cluster that should be ask to provide a value for the key. You do this using the r query string parameter. By default, r=3. Here's an example:

    curl http://localhost:9002/key?r=2

### Store a value
To store (create or update) a value for a key, issue an HTTP PUT request, for example:

    curl -X PUT -d "some value" http://localhost:9002/key

On a successful update, a 201 response code will be returned.

On updates, snakes will update all nodes in a cluster. Some of these will be done synchronously before returning a response to the client. The remaining will be done on a background thread pool. By default, 3 nodes gets updated synchronously. However, you can tell snakes if you want a different number of nodes updated synchronously by using the "w" query string parameter. For example:

    curl -X PUT -d "some value" http://localhost:9002/key?w=4

That's all there is to it. Now go and play :-)