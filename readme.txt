HTTP GET and PUT
Single write master (limitation)
No failover (limitation)
HTTP for sync 
String values only (limitation), could be json or whatever
Stored in files with hashed keys, no buckets (limitation)
No in-memory cache (limitation)
No authentication (limitation)
Logging
No transactions (would use e-tags for optimistic locking)
No configurable number of write slaves
Small values
Locale

Plan
* Basic web server
* Basic web client
* Storage
* Threads and queues

Write master:
* snakes http://slave1:8888 http://slave2:8888

Slave:
* snakes


Some examples:
Start a few nodes:
python3.1 snakes.py http://127.0.0.1:9001 http://127.0.0.1:9002
python3.1 snakes.py -p 9001 -d data2 http://127.0.0.1:9000 http://127.0.0.1:9002
python3.1 snakes.py -p 9002 -d data3 http://127.0.0.1:9000 http://127.0.0.1:9001

curl -v http://localhost:9000
curl -X PUT -d val -v http://localhost:9000
