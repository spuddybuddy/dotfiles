#!/usr/bin/env python3

import sys
import http.server
import socketserver

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Tell the browser not to cache the files
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

def Run(HandlerClass=NoCacheHandler):
    host = '127.0.0.1'
    port = 8000

    # Map additional extensions
    HandlerClass.extensions_map.update({'.md': 'text/markdown'})    
    # Fix for MacOS file caching
    HandlerClass.use_sendfile = False     

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if ':' in arg:
            host, port = arg.split(':')
            port = int(port)
        else:
            try:
                port = int(sys.argv[1])
            except ValueError:
                host = sys.argv[1]

    server_address = (host, port)

    # Use allow_reuse_address to make restarting the server easier
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(server_address, HandlerClass) as httpd:
        print(f"Serving HTTP on {host}:{port} (Caching disabled)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
            sys.exit(0)

if __name__ == "__main__":
    Run()
