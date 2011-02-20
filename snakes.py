from optparse import OptionParser
import http.server
import os
import os.path
import sys
import httplib
import threading
import queue
import string
import re
import datetime
import urllib.parse

ASYNC_QUEUE_DEPTH = 10000
DEFAULT_R = 3
DEFAULT_W = 3
NO_OF_ASYNC_THREADS = 1

class SnakesHandler(http.server.BaseHTTPRequestHandler):
    """ HTTP request handler for a snakes server"""
    
    def do_GET(self):
        """Respond to a GET request for getting the value for a key """
        print("Received GET request")
        
        # get the number of nodess to read the value from
        url = urllib.parse.urlparse(self.path)
        r = parse_int_from_qs(url.query, "r", DEFAULT_R)
        
        # validate key
        key = url.path[1:]
        if not self.valid_key(key):
            self.send_response(403)
            self.end_headers()
            return
        
        print("Getting value for key: {}".format(key))
    
        data_file = self.server.keys_dir + "/" + key
        
        value = None
        modified_time = datetime.datetime.min
        
        # do we have a value for this key locally?
        if os.path.exists(data_file):
            modified_time_stamp = os.stat(data_file).st_mtime
            modified_time = datetime.datetime.fromtimestamp(modified_time_stamp)
            last_modified_header = self.date_time_string(modified_time_stamp)
        
            value_length = os.stat(data_file).st_size
            with open(data_file, mode='rb') as the_file:
                value = the_file.read(value_length)
        
        # check with r nodes to get a quorum on the value
        for i in range(min(r - 1, len(self.server.nodes))):
            node = self.server.nodes[i]
            (headers, content) = node.get(key)
            
            if headers["status"] == 200 and not value == content:
                
                last_modified = datetime.datetime.strptime(headers["last-modified"], "%a, %d %b %Y %H:%M:%S %Z")
                
                # we use a very simple quorum, last update wins
                if last_modified > modified_time:
                    # newer value from other node, replace
                    modified_time = last_modified
                    value = content
                    last_modified_header = headers["last-modified"]

        # respond to the client
        if value:
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.send_header("Last-Modified", last_modified_header)
            self.end_headers()
            self.wfile.write(value)
        else:
            self.send_response(404)
            self.end_headers()

            
    def do_PUT(self):
        """Respond to a PUT request for storing a key"""
        print("Received PUT request")
        
        try:
            url = urllib.parse.urlparse(self.path)
            
            # validate key
            key = url.path[1:]            
            if not self.valid_key(key):
                self.send_response(403)
                self.end_headers()
                return
                
            # TODO handle missing content-length
            content_length = int(self.headers.get("Content-length"))
        
            # set up the paths for writing
            data = self.rfile.read(content_length)

            tmp_file = self.server.tmp_dir + "/" + key
            data_file = self.server.keys_dir + "/" + key
            
            # write to tmp directory so not to corrupt existing data on failure
            with open(tmp_file, mode='wb') as the_file:
                the_file.write(data)
        
            # write succeded, move file
            os.rename(tmp_file, data_file)
            
            # TODO clean up tmp if rename fails
            
            # push to nodes, best effort
            w = parse_int_from_qs(url.query, "w", DEFAULT_W)
            w = min(w, len(self.server.nodes) + 1)
            
            successfully_updated = 1
            if w > 0:
                for node in self.server.nodes:
                    try:
                        node.update(key, data, successfully_updated >= w)
                        successfully_updated = successfully_updated + 1
                    except Exception:
                        pass
                
            # respond to client
            if successfully_updated >= w:
                self.send_response(201)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
            else:
                self.send_response(500, "Only {} nodes updated".format(successfully_updated))
                self.end_headers()
            
        except Exception as err:
            print(err)
            self.send_response(500)
            self.end_headers()
    
    __key_pattern = re.compile("^[a-zA-Z0-9]+$")
    
    def valid_key(self, key):
        return self.__key_pattern.match(key)

class SnakesHttpServer(http.server.HTTPServer):
    """ A very basic HTTP server serving requests for the snakes server """
    
    def __init__(self, server_address, RequestHandlerClass, nodes = [], data_dir = "data"):
        super( SnakesHttpServer, self ).__init__(server_address, RequestHandlerClass)
        self.nodes = nodes
        self.data_dir = data_dir
        self.keys_dir = data_dir + "/keys"
        self.tmp_dir = data_dir + "/tmp"
        
        if not os.path.exists(self.data_dir): os.mkdir(self.data_dir)
        if not os.path.exists(self.keys_dir): os.mkdir(self.keys_dir)
        if not os.path.exists(self.tmp_dir): os.mkdir(self.tmp_dir)
        
        async_node_queue = queue.Queue(ASYNC_QUEUE_DEPTH)
        
        # hook up the async queue to the nodes
        for node in nodes:
            node.async_node_queue = async_node_queue
        
        for i in range(0, NO_OF_ASYNC_THREADS):
            self.async_node_updator = AsyncNodeUpdator(async_node_queue)
            print("Starting async updator")
            self.async_node_updator.start()
        

class AsyncNodeUpdator(threading.Thread):
    """ A thread for updated nodes asyncronously. Will wait for updates on a queue and update nodes as needed.  """
    
    http_client = httplib.Http(timeout=5)
    stopped = False
    
    def __init__(self, queue):
        threading.Thread.__init__(self)
        daemon = False
        self.queue = queue
    
    def run(self):
        while(not self.stopped):
            try:
                (url, data) = self.queue.get(False, 1)
                try:
                    print("Pushing async to node {}".format(url))
                    self.http_client.request(url, method="PUT",body=data,headers={'content-type':'text/plain'})
                except Exception:
                    # reset HTTP client
                    self.http_client = httplib.Http(timeout=5)
            except queue.Empty:
                pass

    def stop(self):
        self.stopped = True

class SnakesNode:
    """ Representing a specific node to which this server is connected. Handles communication with the node """
    
    http_client = httplib.Http(timeout=5)
    
    def __init__(self, node_url):
        # validate URL
        parsed_url = urllib.parse.urlparse(node_url)
        if not (parsed_url.scheme == "http" or parsed_url.scheme == "https") or len(parsed_url.netloc) == 0:
            raise Exception("Node URLs must be absolute http or https URLs")
        
        self.url = node_url
        
    def update(self, key, data, async=False):
        """ Update the node with the provided key and data. If async = True, the update will be requested by the AsyncNodeUpdator """
        
        complete_url = self.url + "/" + key + "?w=0"
        
        if not async:
            print("Pushing sync to node {}".format(self.url))
            try:
                (headers, content) = self.http_client.request(complete_url, method="PUT", body=data, headers={'content-type':'text/plain'})
            except Exception as e:
                self.http_client = httplib.Http(timeout=5)
                raise e
        else:
            self.async_node_queue.put((complete_url, data), False, 5)
    

    def get(self, key):
        """ Get a value based on key from the node """
        
        print("Getting from node {}".format(self.url))

        (headers, content) = self.http_client.request(self.url + "/" + key + "?r=1", method="GET", redirections=0)
        return (headers, content)    

def parse_int_from_qs(query, name, default):
    """ Parse a numering value from a query string value"""
    
    try:
        if len(query) > 0:
            qs = urllib.parse.parse_qs(query)
            if name in qs:
                return int(qs[name][0])
    except ValueError:
        pass
        
    return default

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
        
    httpd.async_node_updator.stop()
    httpd.server_close()
    print("Server Stops - {}:{}".format("", options.port))