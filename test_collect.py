# test_collect.py
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/collect":
            self.send_response(404); self.end_headers(); return
        length = int(self.headers.get('Content-Length','0'))
        body = self.rfile.read(length)
        print("Got:", body.decode('utf-8'))
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
httpd = HTTPServer(("127.0.0.1", 8080), H)
httpd.serve_forever()
