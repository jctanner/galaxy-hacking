#!/usr/bin/env python3

import http.server
import http.client


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.proxy_request()

    def do_POST(self):
        self.proxy_request()

    def do_PUT(self):
        self.proxy_request()

    def do_PATCH(self):
        self.proxy_request()

    def proxy_request(self):
        # Define the target servers for "api" and "ux" routes
        api_server = ('api', 8000)
        ux_server = ('ux', 8002)

        # Determine the target server based on the request path
        if self.path.startswith('/api'):
            target_server = api_server
        else:
            target_server = ux_server

        # Create a connection to the target server
        proxy_connection = http.client.HTTPConnection(*target_server)

        try:
            # Send the original request to the target server
            proxy_connection.request(self.command, self.path, body=self.rfile.read(), headers=self.headers)

            # Get the response from the target server
            response = proxy_connection.getresponse()

            # Send the response back to the client
            self.send_response(response.status)
            for header, value in response.getheaders():
                self.send_header(header, value)
            self.end_headers()
            self.wfile.write(response.read())
        except Exception as e:
            # Handle exceptions and errors here
            self.send_error(500, f'Proxy Error: {str(e)}')


if __name__ == '__main__':
    # Set the server address and port
    server_address = ('0.0.0.0', 80)

    # Create and start the proxy server
    httpd = http.server.HTTPServer(server_address, ProxyHandler)
    print(f'Starting proxy server on {server_address[0]}:{server_address[1]}')
    httpd.serve_forever()

