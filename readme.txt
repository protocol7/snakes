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

Plan
* Basic web server
* Basic web client
* Storage
* Threads and queues

Write master:
* snakes http://slave1:8888 http://slave2:8888

Slave:
* snakes