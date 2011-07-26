#!/usr/bin/env python

"""
Dummy server used for unit testing
"""

import gzip
import logging
import sys
import time
import zlib

from cgi import FieldStorage
from StringIO import StringIO
from webob import Request, Response, exc
from wsgiref import simple_server


class TestingApp(object):
    """
    Simple app that performs various operations, useful for testing an HTTP
    library.

    Given any path, it will attempt to convert it will load a corresponding
    local method if it exists. Status code 200 indicates success, 400 indicates
    failure. Each method has its own conditions for success/failure.
    """
    def __call__(self, environ, start_response):
        req = Request(environ)
        target = req.path_info[1:].replace('/', '_')
        method = getattr(self, target, self.index)
        resp = method(req)
        return resp(environ, start_response)

    def index(self, _request):
        "Render simple message"
        return Response("Dummy server!")

    def specific_method(self, request):
        "Confirm that the request matches the desired method type"
        method = request.params.get('method')
        if request.method != method:
            return Response("Wrong method: %s != %s" %
                            (method, request.method), status='400')
        return Response()

    def upload(self, request):
        "Confirm that the uploaded file conforms to specification"
        param = request.params.get('upload_param', 'myfile')
        filename = request.params.get('upload_filename', '')
        size = int(request.params.get('upload_size', '0'))
        file_ = request.params.get(param)

        if not isinstance(file_, FieldStorage):
            return Response("'%s' is not a file: %r" %
                            (param, file_), status='400')

        data = file_.value
        if int(size) != len(data):
            return Response("Wrong size: %d != %d" %
                            (size, len(data)), status='400')

        if filename != file_.filename:
            return Response("Wrong filename: %s != %s" %
                            (filename, file_.filename), status='400')

        return Response()

    def redirect(self, request):
        "Perform a redirect to ``target``"
        target = request.params.get('target', '/')
        return exc.HTTPSeeOther(location=target)

    def keepalive(self, request):
        if request.params.get('close', '0') == '1':
            response = Response('Closing')
            response.headers['Connection'] = 'close'
        else:
            response = Response('Keeping alive')
            response.headers['Connection'] = 'keep-alive'
        return response

    def sleep(self, request):
        "Sleep for a specified amount of ``seconds``"
        seconds = float(request.params.get('seconds', '1'))
        time.sleep(seconds)
        return Response()

    def echo(self, request):
        """Echo back the params"""
        return Response("%s" % request.body)

    def encodingrequest(self, request):
        "Check for UA accepting gzip/defkate encoding"
        data = "hello, world!"
        encoding = request.headers.get('Accept-Encoding', '')
        headers = {}
        if 'gzip' in encoding:
            headers = {'Content-Encoding': 'gzip'}
            file_ = StringIO()
            gzip.GzipFile('', mode='w', fileobj=file_).write(data)
            data = file_.getvalue()
        elif 'deflate' in encoding:
            headers = {'Content-Encoding': 'deflate'}
            data = zlib.compress(data)
        return Response(data, headers=headers)


def make_server(HOST="localhost", PORT=8081):
    app = TestingApp()

    log.info('Creating server on http://%s:%s' % (HOST, PORT))
    return simple_server.make_server(HOST, PORT, app)


if __name__ == '__main__':

    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    log.addHandler(logging.StreamHandler(sys.stderr))

    if __debug__:
        # BaseHTTPServer raises an assertion error with __debug__
        # enabled when responding with a "Connection" header
        log.warning("The Keep-alive test will fail because"
                    " __debug__ is active!")
        log.warning("To properly test keep-alive, re-run in optimized mode:\n")
        log.warning("  $ python -O %s" % sys.argv[0])

    httpd = make_server()
    httpd.serve_forever()
