#!/usr/bin/env python

# Original: https://github.com/ksmith97/GzipSimpleHTTPServer/blob/master/GzipSimpleHTTPServer.py
# This version: https://github.com/britzl/httpserver-python

"""Simple HTTP Server.

This module builds on BaseHTTPServer by implementing the standard GET
and HEAD requests in a fairly straightforward manner.

"""


__version__ = "0.6"

__all__ = ["SimpleHTTPRequestHandler"]

import os
import posixpath
import BaseHTTPServer
import urllib
import cgi
import sys
import mimetypes
import zlib
from optparse import OptionParser

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

SERVER_PORT = 8000
CONTENT_ENCODING = 'gzip'
TRANSFER_ENCODING = None
OVERWRITE_FILES = None

def parse_options():
    # Option parsing logic.
    parser = OptionParser()
    parser.add_option("--ce", "--content-encoding", dest="content_encoding",
                      help="Content encoding type for server to utilize",
                      default='gzip')
    parser.add_option("--te", "--transfer-encoding", dest="transfer_encoding",
                      help="Transfer encoding type for server to utilize",
                      default=None)
    parser.add_option("-p", "--port", dest="port",
                      help="The port to serve the files on",
                      default="8000")
    parser.add_option("--of", "--overwrite-files", dest="overwrite_files", action="store_true",
                      help="If PUT/POST can overwrite existing files or not",
                      default="False")
    (options, args) = parser.parse_args()

    global CONTENT_ENCODING
    global TRANSFER_ENCODING
    global SERVER_PORT
    global OVERWRITE_FILES
    TRANSFER_ENCODING = options.transfer_encoding
    CONTENT_ENCODING = options.content_encoding
    SERVER_PORT = int(options.port)
    OVERWRITE_FILES = options.overwrite_files

    if CONTENT_ENCODING not in ['zlib', 'deflate', 'gzip']:
        sys.stderr.write("Please provide a valid content encoding for the server to utilize.\n")
        sys.stderr.write("Possible values are 'zlib', 'gzip', and 'deflate'\n")
        sys.stderr.write("Usage: python " + os.path.basename(__file__) + " --content-encoding=<CONTENT_ENCODING>\n")
        sys.exit()

    if TRANSFER_ENCODING is not None and TRANSFER_ENCODING not in ['chunked']:
        sys.stderr.write("Please provide a valid transfer encoding for the server to utilize.\n")
        sys.stderr.write("Possible values are 'chunked'\n")
        sys.stderr.write("Usage: python " + os.path.basename(__file__) + " --transfer-encoding\n")
        sys.exit()

def zlib_encode(content):
    zlib_compress = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS)
    data = zlib_compress.compress(content) + zlib_compress.flush()
    return data


def deflate_encode(content):
    deflate_compress = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    data = deflate_compress.compress(content) + deflate_compress.flush()
    return data


def gzip_encode(content):
    gzip_compress = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    data = gzip_compress.compress(content) + gzip_compress.flush()
    return data


class SimpleHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Simple HTTP request handler with GET and HEAD commands.

    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method.

    The GET and HEAD requests are identical except that the HEAD
    request omits the actual contents of the file.

    """

    server_version = "SimpleHTTP/" + __version__

    def write_chunk(chunk):
        tosend = '%X\r\n%s\r\n'%(len(chunk), chunk)
        self.wfile.write(tosend)

    def do_GET(self):
        """Serve a GET request."""
        print(self.headers)
        content = self.send_head()
        if content:
            if TRANSFER_ENCODING == "chunked":
                max_chunk_size = 4096
                for i in range(0, len(content), max_chunk_size):
                    self.wfile.write(content[i:i+max_chunk_size])
            else:
                self.wfile.write(content)

    def do_PUT(self):
        """Save a file following a HTTP PUT request"""
        print(self.headers)
        filename = os.path.basename(self.path)

        # Don't overwrite files
        if os.path.exists(filename):
            if not OVERWRITE_FILES:
                self.send_response(409, 'Conflict')
                self.end_headers()
                reply_body = '"%s" already exists\n' % filename
                self.wfile.write(reply_body.encode('utf-8'))
                return
            else:
                print("Overwriting %s" % filename)

        file_length = int(self.headers['Content-Length'])
        with open(filename, 'wb+') as output_file:
            read = 0
            while read < file_length:
                new_read = self.rfile.read(min(66556, file_length - read))
                read += len(new_read)
                output_file.write(new_read)
        self.send_response(201, 'Created')
        self.end_headers()
        reply_body = 'Saved "%s"\n' % filename
        self.wfile.write(reply_body.encode('utf-8'))

    def do_POST(self):
        self.do_PUT()

    def do_HEAD(self):
        """Serve a HEAD request."""
        print(self.headers)
        content = self.send_head()

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        print("Serving path '%s'" % path)
        f = None
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path).read()
        content_type = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)

        fs = os.fstat(f.fileno())
        raw_content_length = fs[6]
        content = f.read()

        # Encode content based on runtime arg
        if CONTENT_ENCODING == "gzip":
            content = gzip_encode(content)
        elif CONTENT_ENCODING == "deflate":
            content = deflate_encode(content)
        elif CONTENT_ENCODING == "zlib":
            content = zlib_encode(content)

        compressed_content_length = len(content)
        f.close()

        # Send headers
        if TRANSFER_ENCODING:
            self.send_header("Transfer-Encoding", TRANSFER_ENCODING)
        if TRANSFER_ENCODING != "chunked":
            self.send_header("Content-Length", max(raw_content_length, compressed_content_length))
        self.send_header("Content-type", content_type)
        self.send_header("Content-Encoding", CONTENT_ENCODING)
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return content

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = StringIO()
        displaypath = cgi.escape(urllib.unquote(self.path))
        f.write('<!DOCTYPE html>')
        f.write("<html>\n<title>Directory listing for %s</title>\n" % displaypath)
        f.write("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath)
        f.write("<hr>\n<ul>\n")
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write('<li><a href="%s">%s</a>\n'
                    % (urllib.quote(linkname), cgi.escape(displayname)))
        f.write("</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path

    def guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.

        """

        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init() # try to read system mime.types

    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream', # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
        '.wasm': 'application/wasm',
        })


def test(HandlerClass = SimpleHTTPRequestHandler,
         ServerClass = BaseHTTPServer.HTTPServer):
    """Run the HTTP request handler class.

    This runs an HTTP server on port 8000 (or the first command line
    argument).

    """

    parse_options()

    server_address = ('0.0.0.0', SERVER_PORT)

    SimpleHTTPRequestHandler.protocol_version = "HTTP/1.0"
    httpd = BaseHTTPServer.HTTPServer(server_address, SimpleHTTPRequestHandler)

    sa = httpd.socket.getsockname()
    print "Serving HTTP on", sa[0], "port", sa[1], "..."
    httpd.serve_forever()
    BaseHTTPServer.test(HandlerClass, ServerClass)


if __name__ == '__main__':
    test()
