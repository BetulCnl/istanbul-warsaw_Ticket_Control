"""Siteyi bu bilgisayarda açar (http://localhost:8765). Tarayıcı eski sürümü önbellekten göstermesin diye no-cache gönderir."""
import http.server, functools, os
class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()
os.chdir(os.path.dirname(os.path.abspath(__file__)))
http.server.ThreadingHTTPServer(("127.0.0.1", 8765), NoCache).serve_forever()
