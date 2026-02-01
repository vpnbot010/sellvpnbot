import http.server
import socketserver
import threading
import os

class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

def start_health_check():
    port = int(os.getenv("PORT", 8080))
    with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
        print(f"✅ Health check сервер запущен на порту {port}")
        httpd.serve_forever()

def run_health_check():
    thread = threading.Thread(target=start_health_check, daemon=True)
    thread.start()
