from http.server import BaseHTTPRequestHandler,HTTPServer
import json
import events
import threading
import config
from irc import IrcConnection

irc = None

# handle POST events from github server
# We should also make sure to ignore requests from the IRC, which can clutter
# the output with errors
CONTENT_TYPE = 'content-type'
CONTENT_LEN = 'content-length'
EVENT_TYPE = 'x-github-event'

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pass
    def do_CONNECT(self):
        pass
    def do_POST(self):
        print(self.headers)
        if not all(x in self.headers for x in [CONTENT_TYPE, CONTENT_LEN, EVENT_TYPE]):
            return
        content_type = self.headers['content-type']
        content_len = int(self.headers['content-length'])
        event_type = self.headers['x-github-event']

        data = self.rfile.read(content_len)

        self.send_response(200)
        self.send_header('content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes('OK', 'utf-8'))

        events.handle_event(irc, event_type, json.loads(data.decode()))
        return

def worker():
    irc.loop()

irc = IrcConnection('config.ini')

t = threading.Thread(target=worker)
t.start()

if irc.widelands['webhook']['start']:
    # Run Github webhook handling server
    try:
        server = HTTPServer((irc.widelands['webhook']['host'], irc.widelands['webhook']['port']), MyHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("Exiting")
        server.socket.close()
        irc.stop_loop()

