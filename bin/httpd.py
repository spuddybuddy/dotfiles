#!/usr/bin/python

import sys
import http.server
import socketserver

def Run(Handler=http.server.SimpleHTTPRequestHandler):

    Handler.protocol_version = 'HTTP/1.0'
    Handler.extensions_map.update({'.md': 'text/markdown'})
    protocol = 'HTTP/1.0'
    host = '127.0.0.1'
    port = 8000
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if ':' in arg:
            host, port = arg.split(':')
            port = int(port)
        else:
            try:
                port = int(sys.argv[1])
            except:
                host = sys.argv[1]

    server_address = (host, port)

    with socketserver.TCPServer(server_address, Handler) as httpd:
        sa = httpd.socket.getsockname()
        print(f"Serving HTTP on {host}:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    Run()
