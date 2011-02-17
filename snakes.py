from optparse import OptionParser
import http.server
import shutil
import hashlib
import os
import os.path
import sys
import httplib2
import threading
import string
import re

class SnakesHandler(http.server.BaseHTTPRequestHandler):
            
    def key_to_filename(self, key):
        return hashlib.md5(key.encode("UTF-8")).hexdigest()
    
    def do_GET(self):
        """Respond to a GET request."""
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

        key = self.path[1:]
        
        if len(key) > 0:
            print("Getting value for key: {}".format(key))
            file_name = self.key_to_filename(key)
        
            data_file = self.server.keys_dir + "/" + file_name

            with open(data_file, mode='rb') as the_file:
                shutil.copyfileobj(the_file, self.wfile)
        else:
            # print last transaction ID
            self.wfile.write(str(self.server.transaction_log.transaction_seq).encode("utf-8"))
            
    def do_PUT(self):
        """Respond to a PUT request."""
        try:
            key = self.path[1:]
            print(key)
            # TODO handle empty key
        
            file_name = self.key_to_filename(key)
            print(file_name)
        
            # TODO handle collisions

            # TODO handle missing content-length
            content_length = int(self.headers.get("Content-length"))
        
            # TODO stream
            data = self.rfile.read(content_length)

            tmp_file = self.server.tmp_dir + "/" + file_name
            data_file = self.server.keys_dir + "/" + file_name
            
            # write to tmp directory so not to corrupt existing data on failure
            with open(tmp_file, mode='wb') as the_file:
                the_file.write(data)
        
            # write succeded, move file
            os.rename(tmp_file, data_file)
            
            # TODO clean up tmp if rename fails
            self.server.transaction_log.writeTransaction(key)
            
            # push to slaves
            # TODO do async
            for slave in self.server.slaves:
                print("Pushing to slave {}".format(slave))
                http_client = httplib2.Http()
                http_client.request(slave + "/" + key, method="PUT", redirections=0,body=data, 
                    headers={'content-type':'text/plain'})
                
            self.send_response(201)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
        except IOError:
            self.send_response(500)
            self.end_headers()

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
        
        self.transaction_log = TransactionLog(self.data_dir + "/transactions")
    

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
    (options, slaves) = parser.parse_args()
    
    httpd = SnakesHttpServer(("", options.port), SnakesHandler, slaves, options.data_dir)
    
    print("Server Starts - {}:{}".format("", options.port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server Stops - {}:{}".format("", options.port))