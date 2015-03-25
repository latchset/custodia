# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

try:
    # pylint: disable=import-error
    from BaseHTTPServer import BaseHTTPRequestHandler
    from SocketServer import ForkingMixIn, UnixStreamServer
except ImportError:
    # pylint: disable=import-error
    from http.server import BaseHTTPRequestHandler
    from socketserver import ForkingMixIn, UnixStreamServer
import io
import os
import shutil
import six
import socket
import struct
import sys
import traceback

SO_PEERCRED = 17


class HTTPError(Exception):

    def __init__(self, code=None, message=None):
        self.code = code if code is not None else 500
        self.mesg = message
        super(HTTPError, self).__init__('%d: %s' % (self.code, self.mesg))


def stacktrace():
    with io.BytesIO() as f:
        _, _, tb = sys.exc_info()
        traceback.print_tb(tb, None, file=f)
        del tb
        return f.getvalue()


class ForkingLocalHTTPServer(ForkingMixIn, UnixStreamServer):

    server_string = "Custodia/0.1"
    allow_reuse_address = True
    socket_file = None

    def __init__(self, server_address, handler_class, config):
        UnixStreamServer.__init__(self, server_address, handler_class)
        if 'consumers' not in config:
            raise ValueError('Configuration does not provide any consumer')
        self.config = config
        if 'server_string' in self.config:
            self.server_string = self.config['server_string']

    def server_bind(self):
        UnixStreamServer.server_bind(self)
        self.socket_file = self.socket.getsockname()

    def pipeline(self, request):

        # auth framework here
        authers = self.config.get('authenticators')
        if authers is None:
            raise HTTPError(403)
        for auth in authers:
            authers[auth].handle(request)
        if 'valid_auth' not in request or request['valid_auth'] is not True:
            raise HTTPError(403)

        # Select consumer
        path = request.get('path', '')
        if not os.path.isabs(path):
            raise HTTPError(400)

        trail = []
        while path != '':
            if path in self.config['consumers']:
                con = self.config['consumers'][path]
                if len(trail) != 0:
                    request['trail'] = trail
                return con.handle(request)
            if path == '/':
                path = ''
            else:
                head, tail = os.path.split(path)
                trail.insert(0, tail)
                path = head

        raise HTTPError(404)


class LocalHTTPRequestHandler(BaseHTTPRequestHandler):

    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
        self.requestline = ''
        self.request_version = ''
        self.command = ''
        self.raw_requestline = None
        self.close_connection = 0

    def version_string(self):
        return self.server.server_string

    @property
    def peer_creds(self):

        creds = self.request.getsockopt(socket.SOL_SOCKET, SO_PEERCRED,
                                        struct.calcsize('3i'))
        pid, uid, gid = struct.unpack('3i', creds)
        return {'pid': pid, 'uid': uid, 'gid': gid}

    def handle_one_request(self):
        # Set a fake client address to make log functions happy
        self.client_address = ['127.0.0.1', 0]
        try:
            if not self.server.pipeline:
                self.close_connection = 1
                return
            self.raw_requestline = self.rfile.readline(65537)
            if not self.raw_requestline:
                self.close_connection = 1
                return
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(414)
                self.wfile.flush()
                return
            if not self.parse_request():
                return
            request = {'creds': self.peer_creds,
                       'command': self.command,
                       'path': self.path,
                       'version': self.request_version,
                       'headers': self.headers}
            try:
                response = self.server.pipeline(request)
                if response is None:
                    raise HTTPError(500)
            except HTTPError as e:
                self.send_error(e.code, e.mesg)
                self.wfile.flush()
                return
            except socket.timeout as e:
                self.log_error("Request timed out: %r", e)
                self.close_connection = 1
                return
            except Exception as e:  # pylint: disable=broad-except
                self.log_error("Handler failed: %r", e)
                self.log_traceback()
                self.send_error(500)
                self.wfile.flush()
                return
            self.send_response(response.get('code', 200))
            for header, value in six.iteritems(response.get('headers', {})):
                self.send_header(header, value)
            self.end_headers()
            output = response.get('output', None)
            if hasattr(output, 'read'):
                shutil.copyfileobj(output, self.wfile)
                output.close()
            else:
                self.wfile.write(output.encode('utf-8'))
            self.wfile.flush()
            return
        except socket.timeout as e:
            self.log_error("Request timed out: %r", e)
            self.close_connection = 1
            return

    def log_traceback(self):
        self.log_error('Traceback:\n%s' % stacktrace())


class LocalHTTPServer(object):

    def __init__(self, address, config):
        if address[0] != '/':
            raise ValueError('Must use absolute unix socket name')
        if os.path.exists(address):
            os.remove(address)
        self.httpd = ForkingLocalHTTPServer(address, LocalHTTPRequestHandler,
                                            config)

    def get_socket(self):
        return (self.httpd.socket, self.httpd.socket_file)

    def serve(self):
        return self.httpd.serve_forever()
