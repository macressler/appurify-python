"""
    Copyright 2013 Appurify, Inc
    All rights reserved

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
    License for the specific language governing permissions and limitations
    under the License.
"""
import os
import sys
import signal
import argparse
import paramiko
import select
import socket
import threading
import urlparse
import datetime
import tempfile
import atexit
import time
import logging

from . import constants
from .utils import log, post

SOCKET_TIMEOUT = 5000
ACCEPT_TIMEOUT = 1000
SELECT_TIMEOUT = 1000

MAX_INACTIVITY = 30000
MAX_RECV_BYTES = 8192
MAX_RETRIES = 5

CRLF = '\r\n'
COLON = ':'
SP = ' '

HTTP_REQUEST_PARSER = 1
HTTP_RESPONSE_PARSER = 2

HTTP_PARSER_STATE_INITIALIZED = 1
HTTP_PARSER_STATE_LINE_RCVD = 2
HTTP_PARSER_STATE_RCVING_HEADERS = 3
HTTP_PARSER_STATE_HEADERS_COMPLETE = 4
HTTP_PARSER_STATE_RCVING_BODY = 5
HTTP_PARSER_STATE_COMPLETE = 6

CHUNK_PARSER_STATE_WAITING_FOR_SIZE = 1
CHUNK_PARSER_STATE_WAITING_FOR_DATA = 2
CHUNK_PARSER_STATE_COMPLETE = 3

class ChunkParser(object):

    def __init__(self):
        self.state = CHUNK_PARSER_STATE_WAITING_FOR_SIZE
        self.body = ''
        self.chunk = ''
        self.size = None

    def parse(self, data):
        more = True if len(data) > 0 else False
        while more: more, data = self.process(data)

    def process(self, data):
        if self.state == CHUNK_PARSER_STATE_WAITING_FOR_SIZE:
            line, data = HttpParser.split(data)
            self.size = int(line, 16)
            self.state = CHUNK_PARSER_STATE_WAITING_FOR_DATA
        elif self.state == CHUNK_PARSER_STATE_WAITING_FOR_DATA:
            remaining = self.size - len(self.chunk)
            self.chunk += data[:remaining]
            data = data[remaining:]
            if len(self.chunk) == self.size:
                data = data[len(CRLF):]
                self.body += self.chunk
                if self.size == 0:
                    self.state = CHUNK_PARSER_STATE_COMPLETE
                else:
                    self.state = CHUNK_PARSER_STATE_WAITING_FOR_SIZE
                self.chunk = ''
                self.size = None
        return len(data) > 0, data

class HttpParser(object):

    def __init__(self, type=None):
        self.state = HTTP_PARSER_STATE_INITIALIZED
        self.type = type if type else HTTP_REQUEST_PARSER

        self.raw = ''
        self.buffer = ''

        self.headers = dict()
        self.body = None

        self.method = None
        self.url = None
        self.code = None
        self.reason = None
        self.version = None

        self.chunker = None

    def parse(self, data):
        self.raw += data
        data = self.buffer + data
        self.buffer = ''

        more = True if len(data) > 0 else False
        while more: more, data = self.process(data)
        self.buffer = data

    def process(self, data):
        if self.state >= HTTP_PARSER_STATE_HEADERS_COMPLETE and \
        (self.method == "POST" or self.type == HTTP_RESPONSE_PARSER):
            if not self.body:
                self.body = ''

            if 'content-length' in self.headers:
                self.state = HTTP_PARSER_STATE_RCVING_BODY
                self.body += data
                if len(self.body) >= int(self.headers['content-length'][1]):
                    self.state = HTTP_PARSER_STATE_COMPLETE
            elif 'transfer-encoding' in self.headers and self.headers['transfer-encoding'][1].lower() == 'chunked':
                if not self.chunker:
                    self.chunker = ChunkParser()
                self.chunker.parse(data)
                if self.chunker.state == CHUNK_PARSER_STATE_COMPLETE:
                    self.body = self.chunker.body
                    self.state = HTTP_PARSER_STATE_COMPLETE

            return False, ''

        line, data = HttpParser.split(data)
        if line == False: return line, data

        if self.state < HTTP_PARSER_STATE_LINE_RCVD:
            self.process_line(line)
        elif self.state < HTTP_PARSER_STATE_HEADERS_COMPLETE:
            self.process_header(line)

        if self.state == HTTP_PARSER_STATE_HEADERS_COMPLETE and \
        self.type == HTTP_REQUEST_PARSER and \
        not self.method == "POST" and \
        self.raw.endswith(CRLF*2):
            self.state = HTTP_PARSER_STATE_COMPLETE

        return len(data) > 0, data

    def process_line(self, data):
        line = data.split(SP)
        if self.type == HTTP_REQUEST_PARSER:
            self.method = line[0].upper()
            self.url = urlparse.urlsplit(line[1])
            self.version = line[2]
        else:
            self.version = line[0]
            self.code = line[1]
            self.reason = ' '.join(line[2:])
        self.state = HTTP_PARSER_STATE_LINE_RCVD

    def process_header(self, data):
        if len(data) == 0:
            if self.state == HTTP_PARSER_STATE_RCVING_HEADERS:
                self.state = HTTP_PARSER_STATE_HEADERS_COMPLETE
            elif self.state == HTTP_PARSER_STATE_LINE_RCVD:
                self.state = HTTP_PARSER_STATE_RCVING_HEADERS
        else:
            self.state = HTTP_PARSER_STATE_RCVING_HEADERS
            parts = data.split(COLON)
            key = parts[0].strip()
            value = COLON.join(parts[1:]).strip()
            self.headers[key.lower()] = (key, value)

    def build_url(self):
        if not self.url:
            return '/None'

        url = self.url.path
        if url == '': url = '/'
        if not self.url.query == '': url += '?' + self.url.query
        if not self.url.fragment == '': url += '#' + self.url.fragment
        return url

    def build_header(self, k, v):
        return '%s: %s%s' % (k, v, CRLF)

    def build(self, del_headers=None, add_headers=None):
        req = '%s %s %s' % (self.method, self.build_url(), self.version)
        req += CRLF

        if not del_headers: del_headers = []
        for k in self.headers:
            if not k in del_headers:
                req += self.build_header(self.headers[k][0], self.headers[k][1])

        if not add_headers: add_headers = []
        for k in add_headers:
            req += self.build_header(k[0], k[1])

        req += CRLF
        if self.body:
            req += self.body

        return req

    @staticmethod
    def split(data):
        pos = data.find(CRLF)
        if pos == -1: return False, data
        line = data[:pos]
        data = data[pos+len(CRLF):]
        return line, data

class ProxyConnectFailed(Exception):
    pass

class Proxy(threading.Thread):

    def __init__(self, client):
        super(Proxy, self).__init__()
        self.request = HttpParser()
        self.response = HttpParser(HTTP_RESPONSE_PARSER)

        self.client = client
        self.server = None
        self.buffer = {'client':'', 'server':''}

        self.closed = False
        self.connection_established_pkt = CRLF.join([
            'HTTP/1.1 200 Connection established',
            'Proxy-agent: Appurify Inc. Proxy over Tunnel v%s' % constants.__version__,
            CRLF
        ])

        self.host = None
        self.port = None
        self.last_activity = Tunnel.now()

    def server_host_port(self):
        if not self.host and not self.port:
            if self.request.method == "CONNECT":
                self.host, self.port = self.request.url.path.split(':')
            elif self.request.url:
                self.host, self.port = self.request.url.hostname, self.request.url.port if self.request.url.port else 80
        return self.host, self.port

    def connect_to_server(self):
        host, port = self.server_host_port()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect((host, int(port)))

    def log(self):
        host, port = self.server_host_port()
        if self.request.method == "CONNECT":
            log("%r %s %s:%s (%s secs)" % (self.client.origin_addr, self.request.method, host, port, self.inactive_for()))
        else:
            log("%r %s %s:%s%s %s %s %s bytes (%s secs)" % (self.client.origin_addr, self.request.method, host, port, self.request.build_url(), self.response.code, self.response.reason, len(self.response.raw), self.inactive_for()))

    def process_request(self, data):
        if self.server:
            self.buffer['server'] += data
        else:
            self.request.parse(data)
            if self.request.state == HTTP_PARSER_STATE_COMPLETE:
                try:
                    self.connect_to_server()
                except Exception, e:
                    raise ProxyConnectFailed("%r" % e)

                if self.request.method == "CONNECT":
                    self.buffer['client'] += self.connection_established_pkt
                else:
                    del_headers = ['proxy-connection', 'connection', 'keep-alive']
                    add_headers = [('Connection', 'Close')]
                    self.buffer['server'] += self.request.build(del_headers=del_headers, add_headers=add_headers)

    def process_response(self, data):
        if not self.request.method == "CONNECT":
            self.response.parse(data)
        self.buffer['client'] += data

    def recv_from_server(self):
        try:
            data = self.server.recv(MAX_RECV_BYTES)
            if len(data) == 0: return None
            self.last_activity = Tunnel.now()
            return data
        except Exception, e: # pragma: no cover
            log("unexpected exception while receiving from server socket %r" % e)
            return None

    def recv_from_client(self):
        try:
            data = self.client.recv(MAX_RECV_BYTES)
            if len(data) == 0: return None
            self.last_activity = Tunnel.now()
            return data
        except Exception, e: # pragma: no cover
            log("unexpected exception while receiving from client socket %r" % e)
            return None

    def flush_client_buffer(self):
        sent = self.client.send(self.buffer['client'])
        self.buffer['client'] = self.buffer['client'][sent:]

    def flush_server_buffer(self):
        sent = self.server.send(self.buffer['server'])
        self.buffer['server'] = self.buffer['server'][sent:]

    def close(self):
        self.log()
        if not self.closed:
            if self.server: self.server.close()
            self.server = None
            self.closed = True
        self.client.close()

    def inactive_for(self):
        return (Tunnel.now() - self.last_activity).seconds

    def is_inactive(self):
        return self.inactive_for() > MAX_INACTIVITY/1000

    def process(self):
        while True:
            rlist, wlist, xlist = [self.client], [], []
            if len(self.buffer['client']) > 0: wlist.append(self.client)
            if self.server: rlist.append(self.server)
            if self.server and len(self.buffer['server']) > 0: wlist.append(self.server)
            r, w, x = select.select(rlist, wlist, xlist, SELECT_TIMEOUT/1000)

            if self.client in w:
                self.flush_client_buffer()

            if self.server and self.server in w:
                self.flush_server_buffer()

            if self.client in r:
                data = self.recv_from_client()
                if not data: break
                self.process_request(data)

            if self.server in r:
                data = self.recv_from_server()
                if not data: break
                self.process_response(data)

            # TODO: if we don't recv initial packet from client within a short timeout ~5sec, terminate
            # TODO: make sure client doesn't go in a loop of establishing a connection in advance
            if len(self.buffer['client']) == 0:
                if self.response.state == HTTP_PARSER_STATE_COMPLETE: break
                if self.closed: break
                if self.is_inactive(): break

    def run(self):
        try:
            self.process()
        except ProxyConnectFailed, e:
            self.bad_gateway(e)
        except Exception, e:
            self.bad_gateway(e)
        finally:
            self.close()

    def bad_gateway(self, e):
        log(e, logging.ERROR)
        log(self.request.raw)
        self.client.send("HTTP/1.1 502 Bad Gateway%s%r%s%s" % (CRLF, e, CRLF, CRLF))

class Tunnel(object):

    pidfile = None
    daemon = False
    credentials = None
    config = None
    restart = False
    retry = 0

    @staticmethod
    def now():
        return datetime.datetime.utcnow()

    @staticmethod
    def start():
        Tunnel.retry += 1
        socket.setdefaulttimeout(SOCKET_TIMEOUT/1000)

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        log('Establishing tunnel into Appurify infrastructure ...')

        try:
            client.connect(
                Tunnel.config['ssh_host'],
                port=Tunnel.config['ssh_port'],
                username=Tunnel.config['ssh_user'],
                pkey=Tunnel.config['pkey']
            )
        except Exception, e:
            log('Failed to ssh into %s:%d with reason %r ...' % (Tunnel.config['ssh_host'], Tunnel.config['ssh_port'], e))
            Tunnel.unreserve_proxy_port()
            sys.exit(1)

        try:
            transport = client.get_transport()
            transport.request_port_forward('', Tunnel.config['proxy_port'])
            log('Tunnel established successfully ...')
            while True:
                chan = transport.accept(timeout=ACCEPT_TIMEOUT)
                e = transport.get_exception()
                if e: raise e
                if chan is None: continue
                thr = Proxy(chan)
                thr.setDaemon(True)
                thr.start()
        except KeyboardInterrupt, e:
            log('Stopping Tunnel with reason %r ...' % e)
        except EOFError, e:
            log('Tunnel terminated due to inactivity or because another instance was started (%r) ...' % e)
        except OSError, e:
            log('Underlying OS error, will try to restart tunnel (%r) ...' % e)
            Tunnel.restart = True
        except Exception, e:
            log("Unexpected error, will try to restart tunnel %r ..." % e)
            Tunnel.restart = True

    @staticmethod
    def stop():
        # TODO: better to start a new child proc while letting this parent die
        if Tunnel.restart and Tunnel.retry < MAX_RETRIES:
            try: client.close()
            except: pass
            log("Restarting %sth tunnel instance ..." % Tunnel.retry)
            Tunnel.restart = False
            Tunnel.start()
        else:
            log("Unreserving tunnel resource ...")
            Tunnel.unreserve_proxy_port()
            Tunnel.credentials, Tunnel.config, Tunnel.restart, Tunnel.retry = None, None, False, 0
            log("Shutting down tunnel, start again if required ...")
            sys.exit(0)

    @staticmethod
    def rsa_to_pkey(rsa):
        pkey = paramiko.RSAKey(vals=(rsa['e'], rsa['n']))
        pkey.d = rsa['d']
        pkey.p = rsa['p']
        pkey.q = rsa['q']
        return pkey

    @staticmethod
    def reserve_proxy_port():
        try:
            r = post("tunnel/reserve", Tunnel.credentials)
            if r.status_code == 200:
                return r.json()['response']
            else:
                log('Tunnel setup failed with reason %s ...' % r.text)
                return False
        except Exception, e:
            log('Tunnel setup failed with reason %r ...' % e)
            return False

    @staticmethod
    def unreserve_proxy_port():
        if not Tunnel.config:
            log("No tunnel resource needs to be unreserved ...")
            return

        params = Tunnel.credentials
        params['proxy_port'] = Tunnel.config['proxy_port']

        try:
            r = post("tunnel/unreserve", params)
            if r.status_code == 200:
                log("Successfully unreserved tunnel resource#%s ..." % Tunnel.config['proxy_port'])
            else:
                log("Failed to unreserve resource#%s with reason %s ..." % (Tunnel.config['proxy_port'], r.text))
        except Exception, e:
            log('Failed to unreserve resource#%s with reason %r ...' % (Tunnel.config['proxy_port'], e))

    @staticmethod
    def setup_signal_handlers():
        signal.signal(signal.SIGINT, Tunnel.signal_handler)
        signal.signal(signal.SIGTERM, Tunnel.signal_handler)
        if not sys.platform == 'win32':
            signal.signal(signal.SIGHUP, Tunnel.signal_handler)

    @staticmethod
    def signal_handler(signal, frame):
        log('Rcvd signal %s, stopping tunnel ...' % signal)
        Tunnel.stop()

    @staticmethod
    def pid_file_path():
        if not Tunnel.pidfile:
            (fd, Tunnel.pidfile) = tempfile.mkstemp(suffix='.pid', prefix='appurify-tunnel-%s-' % os.getpid())
            os.close(fd)
        return Tunnel.pidfile

    @staticmethod
    def write_pid_file():
        filepath = Tunnel.pid_file_path()
        pid = os.getpid()
        log('Writing pid %s to file %s ...' % (pid, filepath))
        f = open(filepath, 'wb')
        f.write("%s" % pid)
        f.close()

    @staticmethod
    def delete_pid_file():
        filepath = Tunnel.pid_file_path()
        log('Deleting pid file %s ...' % filepath)
        os.remove(filepath)

    @staticmethod
    def daemonize():
        if sys.platform == 'win32':
            log('Daemon mode not supported for win32 platform')
            return

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            log('Fork#1 failed: %d (%s)' % (e.errno, e.strerror))
            sys.exit(1)

        os.chdir('.')
        os.setsid()
        os.umask(022)

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            log('Fork#2 failed: %d (%s)' % (e.errno, e.strerror))
            sys.exit(1)

        if sys.platform != 'darwin':
            sys.stdout.flush()
            sys.stderr.flush()
            si = file(os.devnull, 'r')
            so = file(os.devnull, 'a+')
            se = file(os.devnull, 'a+', 0)
            os.dup2(si.fileno(), sys.stdin.fileno())
            os.dup2(so.fileno(), sys.stdout.fileno())
            os.dup2(se.fileno(), sys.stderr.fileno())

    @staticmethod
    def run():
        if Tunnel.daemon:
            Tunnel.daemonize()

        atexit.register(Tunnel.delete_pid_file)
        Tunnel.write_pid_file()

        Tunnel.setup_signal_handlers()
        config = Tunnel.reserve_proxy_port()
        if config == False:
            sys.exit(1)

        log("Successfully reserved tunnel resource#%s ..." % config['proxy_port'])
        config['pkey'] = Tunnel.rsa_to_pkey(config['key'])
        config['proxy_port'] = int(config['proxy_port'])

        Tunnel.config = config
        Tunnel.start()
        Tunnel.stop()

    @staticmethod
    def terminate(pid, pidfile):
        if not pid and pidfile:
            try:
                pid = int(open(pidfile, 'rb').read().strip())
            except Exception, e:
                log("Unable to read PID out of file %s with reason %r" % (pidfile, e))

        if pid:
            try:
                os.kill(int(pid), signal.SIGTERM)
            except Exception, e:
                log("Failed to terminate %s with reason %r" % (pid, e))
                return

            time.sleep(1)

            try:
                os.kill(int(pid), 0)
                log("Failed to terminate PID %s, try using SIGKILL or SIGABORT" % pid)
            except:
                log("Successfully terminated PID %s" % pid)
        else:
            log("Neither --pid nor --pid-file point to a PID")

def init():
    parser = argparse.ArgumentParser(
        description='Appurify developer tunnel client v%s' % constants.__version__,
        epilog='Email us at %s for further information' % constants.__contact__
    )

    parser.add_argument('--api-key', help='Appurify developer key')
    parser.add_argument('--api-secret', help='Appurify developer secret')
    parser.add_argument('--username', help='Appurify username')
    parser.add_argument('--password', help='Appurify password')
    parser.add_argument('--pid-file', help='Save pid to file')
    parser.add_argument('--daemon', action='store_true', help='Run in background (supported only on *nix systems)')
    parser.add_argument('--pid', help='Tunnel session pid to terminate')
    parser.add_argument('--terminate', action='store_true', help='Terminate process identified by --pid-file or --pid and shutdown')
    args = parser.parse_args()

    if args.terminate:
        Tunnel.terminate(args.pid, args.pid_file)
        sys.exit(0)

    if (args.api_key == None or args.api_secret == None) and \
    (args.username == None or args.password == None):
        parser.error('--api-key and --api-secret OR --username and --password is required')

    Tunnel.pidfile = args.pid_file
    Tunnel.daemon = args.daemon
    Tunnel.credentials = dict()

    if args.api_key and args.api_secret:
        Tunnel.credentials['key'], Tunnel.credentials['secret'] = args.api_key, args.api_secret
    else:
        Tunnel.credentials['username'], Tunnel.credentials['password'] = args.username, args.password

    Tunnel.run()

if __name__ == '__main__':
    init()
