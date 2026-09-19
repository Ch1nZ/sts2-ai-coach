import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import signal
from .engine import Engine

PAGE = Path(__file__).resolve().parent / 'web' / 'index.html'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=18765)
    args = parser.parse_args()
    engine = Engine()
    csrf = secrets.token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, code, body, content='application/json'):
            self.send_response(code)
            self.send_header('Content-Type', content)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; frame-ancestors 'none'")
            self.end_headers()
            try:
                self.wfile.write(body.encode())
            except (BrokenPipeError, ConnectionResetError):
                pass

        def valid_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{args.port}', f'localhost:{args.port}')

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, '{}')
            if self.path == '/':
                self.send(200, PAGE.read_text().replace('__TOKEN__', csrf), 'text/html; charset=utf-8')
            elif self.path == '/api/status':
                self.send(200, json.dumps(engine.snapshot()))
            else:
                self.send(404, '{}')

        def do_POST(self):
            if not self.valid_host() or self.headers.get('X-CSRF-Token') != csrf:
                return self.send(403, '{}')
            if self.path not in ('/api/pause', '/api/resume', '/api/retry'):
                return self.send(404, '{}')
            engine.control(self.path.rsplit('/', 1)[-1])
            self.send(200, '{}')

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    engine.thread.start()
    print(f'STS2 AI Coach — http://127.0.0.1:{args.port}', flush=True)
    def terminate(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        engine.close()
        server.server_close()


if __name__ == '__main__':
    main()
