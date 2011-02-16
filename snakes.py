from optparse import OptionParser
import http.server
import shutil
import hashlib
import os
import os.path
import sys
import httplib2

class SnakesHandler(http.server.BaseHTTPRequestHandler):
            
    def key_to_filename(self, key):
        return hashlib.md5(key.encode("UTF-8")).hexdigest()
    
    def do_GET(self):
        """Respond to a GET request."""
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

        key = self.path[1:]
        print(key)
        file_name = self.key_to_filename(key)
        print(file_name)
        
        data_file = self.server.data_dir + "/" + file_name

        with open(data_file, mode='rb') as the_file:
            shutil.copyfileobj(the_file, self.wfile)

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
            data_file = self.server.data_dir + "/" + file_name
            
            # write to tmp directory so not so corrupt existing data on failure
            with open(tmp_file, mode='wb') as the_file:
                the_file.write(data)
        
            # write succeded, move file
            os.rename(tmp_file, data_file)
            
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
            

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-p", "--port", dest="port",help="local port to listen on", type="int", default=9000)
    parser.add_option("-d", "--data", dest="data_dir",help="data directory", type="string", default="data")
    parser.add_option("-t", "--tmp", dest="tmp_dir",help="tmp directory", type="string", default="tmp")
    (options, slaves) = parser.parse_args()
    
    if not os.path.exists(options.data_dir): os.mkdir(options.data_dir)
    if not os.path.exists(options.tmp_dir): os.mkdir(options.tmp_dir)
    
    httpd = http.server.HTTPServer(("", options.port), SnakesHandler)
    httpd.slaves = slaves
    httpd.data_dir = options.data_dir
    httpd.tmp_dir = options.tmp_dir
    
    print("Server Starts - {}:{}".format("", options.port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server Stops - {}:{}".format("", options.port))