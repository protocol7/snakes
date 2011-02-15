import http.server
import shutil
import hashlib
import os
import os.path

HOST_NAME = '' 
PORT_NUMBER = 9000

DATA_DIR = "data"
TMP_DIR = "tmp"


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

        with open(file_name, mode='rb') as theFile:
            shutil.copyfileobj(theFile, self.wfile)

    def do_PUT(self):
        """Respond to a PUT request."""
        try:
            key = self.path[1:]
            print(key)
            # TODO handle empty key
        
            file_name = self.key_to_filename(key)
            print(file_name)
        
            # TODO handle collisions

            content_length = int(self.headers.get("Content-length"))
        
            # TODO stream
            data = self.rfile.read(content_length)

            tmp_file = TMP_DIR + "/" + file_name
            data_file = DATA_DIR + "/" + file_name
            with open(tmp_file, mode='wb') as the_file:
                the_file.write(data)
        
            # write succeded, move file
            os.rename(tmp_file, data_file)
        
            self.send_response(201)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
        except IOError:
            self.send_response(500)
            self.end_headers()
            

if __name__ == '__main__':
    if not os.path.exists(DATA_DIR): os.mkdir(DATA_DIR)
    if not os.path.exists(TMP_DIR): os.mkdir(TMP_DIR)
    
    server_class = http.server.HTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), SnakesHandler)
    print("Server Starts - {}:{}".format(HOST_NAME, PORT_NUMBER))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server Stops - {}:{}".format(HOST_NAME, PORT_NUMBER))