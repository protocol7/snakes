from optparse import OptionParser
import http.server
import shutil
import hashlib
import os
import os.path
import sys
import httplib
import threading
import string
import re
import datetime
import urllib.parse

DFAULT_R = 3

class SnakesHandler(http.server.BaseHTTPRequestHandler):
            
    def do_GET(self):
        """Respond to a GET request."""
        print("Received GET request")
        
        r = DFAULT_R
        url = urllib.parse.urlparse(self.path)
        if len(url.query) > 0:
            qs = urllib.parse.parse_qs(url.query)
            if "r" in qs:
                r = int(qs["r"][0])
        
        key = url.path[1:]
        if not self.valid_key(key):
            self.send_response(403)
            self.end_headers()
            return
        
        print("Getting value for key: {}".format(key))
    
        data_file = self.server.keys_dir + "/" + key
        
        value = None
        modified_time = datetime.datetime.min
        if os.path.exists(data_file):
            modified_time_stamp = os.stat(data_file).st_mtime
            modified_time = datetime.datetime.fromtimestamp(modified_time_stamp)
            last_modified_header = self.date_time_string(modified_time_stamp)
        
            value_length = os.stat(data_file).st_size
            with open(data_file, mode='rb') as the_file:
                value = the_file.read(value_length)
        
        for i in range(min(r - 1, len(self.server.slaves))):
            slave = self.server.slaves[i]
            (headers, content) = slave.get(key)
            
            if not value == content:
                last_modified = datetime.datetime.strptime(headers["last-modified"], "%a, %d %b %Y %H:%M:%S %Z")
                if last_modified > modified_time:
                    # newer value from other node, replace
                    modified_time = last_modified
                    value = content
                    last_modified_header = headers["last-modified"]

        if not value == None:
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.send_header("Last-Modified", last_modified_header)
            self.end_headers()
            self.wfile.write(value)
        else:
            self.send_response(404)
            self.end_headers()


        # TODO ignore?
        #        else:
        # print last transaction ID
        #            self.wfile.write(str(self.server.transaction_log.transaction_seq).encode("utf-8"))
            
    def do_PUT(self):
        """Respond to a PUT request."""
        try:
            url = urllib.parse.urlparse(self.path)
            
            key = url.path[1:]            
            if not self.valid_key(key):
                self.send_response(403)
                self.end_headers()
                return
                
            print(key)
        
            # TODO handle missing content-length
            content_length = int(self.headers.get("Content-length"))
        
            # TODO stream
            data = self.rfile.read(content_length)

            tmp_file = self.server.tmp_dir + "/" + key
            data_file = self.server.keys_dir + "/" + key
            
            # write to tmp directory so not to corrupt existing data on failure
            with open(tmp_file, mode='wb') as the_file:
                the_file.write(data)
        
            # write succeded, move file
            os.rename(tmp_file, data_file)
            
            # TODO clean up tmp if rename fails
            
            # Ignore transaction log for now
            # self.server.transaction_log.writeTransaction(key)
            
            # push to slaves
            # TODO do async

            qs = urllib.parse.parse_qs(url.query)
            if not "push" in qs:
                for slave in self.server.slaves:
                    slave.update(key, data)
                
            self.send_response(201)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
        except IOError:
            self.send_response(500)
            self.end_headers()
    
    key_pattern = re.compile("^[a-zA-Z0-9]+$")
    
    def valid_key(self, key):
        return self.key_pattern.match(key)

class SnakesHttpServer(http.server.HTTPServer):
    
    def __init__(self, server_address, RequestHandlerClass, slaves = [], data_dir = "data"):
        super( SnakesHttpServer, self ).__init__(server_address, RequestHandlerClass)
        self.slaves = slaves
        self.data_dir = data_dir
        self.keys_dir = data_dir + "/keys"
        self.tmp_dir = data_dir + "/tmp"
        
        if not os.path.exists(self.data_dir): os.mkdir(self.data_dir)
        if not os.path.exists(self.keys_dir): os.mkdir(self.keys_dir)
        if not os.path.exists(self.tmp_dir): os.mkdir(self.tmp_dir)
        
        # Ignore transaction log for now
        # self.transaction_log = TransactionLog(self.data_dir + "/transactions")

class SnakesNode:
    
    http_client = httplib.Http(timeout=5)
    
    def __init__(self, node_url):
        # validate URL
        parsed_url = urllib.parse.urlparse(node_url)
        if not (parsed_url.scheme == "http" or parsed_url.scheme == "https") or len(parsed_url.netloc) == 0:
            raise Exception("Node URLs must be absolute http or https URLs")
        
        self.url = node_url
        
    def update(self, key, data):
        print("Pushing to slave {}".format(self.url))

        self.http_client.request(self.url + "/" + key + "?push=true", method="PUT", redirections=0,body=data, 
            headers={'content-type':'text/plain'})

    def get(self, key):
        print("Getting from node {}".format(self.url))

        (headers, content) = self.http_client.request(self.url + "/" + key + "?r=1", method="GET", redirections=0)
        return (headers, content)


# TODO remove?
class TransactionLog:
    transaction_seq = 0
    
    write_lock = threading.Lock()
    
    def __init__(self, transaction_log_file):
        # read the last transaction ID
        if os.path.exists(transaction_log_file):
            transaction_log_length = os.stat(transaction_log_file).st_size

            if transaction_log_length > 0:
                print("Reading last transaction ID from transaction log")
                with open(transaction_log_file, mode="r", encoding='utf-8') as self.transaction_log:
                    block_size = 100
                    seek_pos = transaction_log_length - block_size
                    if seek_pos < 0:
                        seek_pos = 0
                    self.transaction_log.seek(seek_pos)
                    data = self.transaction_log.read(block_size).split('\n')

                    match = re.match("(\d+),.+", data.pop())
                    if match:
                        self.transaction_seq = int(match.group(1)) + 1
                        print("New transaction sequence: {}".format(self.transaction_seq))
        
            print("Appending to existing transaction log: {}".format(transaction_log_file))
            self.transaction_log = open(transaction_log_file, mode="a", encoding='utf-8')
        else:
            print("Creating new transaction log: {}".format(transaction_log_file))
            self.transaction_log = open(transaction_log_file, mode="w", encoding='utf-8')
        
    
    def writeTransaction(self, key):
        # make sure only one thread is writing at any given time
        with self.write_lock:
            print("writing to transaction log: {}".format(key))
            self.transaction_log.write("\n{},{}".format(self.transaction_seq, key))
            self.transaction_log.flush()
            os.fsync(self.transaction_log.fileno())
            self.transaction_seq = self.transaction_seq + 1
    
    

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-p", "--port", dest="port",help="local port to listen on", type="int", default=9000)
    parser.add_option("-d", "--data", dest="data_dir",help="data directory", type="string", default="data")
    (options, node_urls) = parser.parse_args()
    
    nodes = []
    for node_url in node_urls:
        nodes.append(SnakesNode(node_url))
        
    httpd = SnakesHttpServer(("", options.port), SnakesHandler, nodes, options.data_dir)
    
    print("Server Starts - {}:{}".format("", options.port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server Stops - {}:{}".format("", options.port))