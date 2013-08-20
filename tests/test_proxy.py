import unittest
from appurify.tunnel import Proxy, HttpParser
from appurify.tunnel import (CRLF, HTTP_RESPONSE_PARSER, HTTP_PARSER_STATE_COMPLETE,
                             ProxyConnectFailed, HTTP_PARSER_STATE_HEADERS_COMPLETE)

class Client(object):
    
    origin_addr = ('127.0.0.1', 64000)
    buffer = {'in':'', 'out':''}
    
    def __init__(self):
        pass
    
    def recv(self, bytes):
        data = self.buffer['out'][:bytes]
        self.buffer['out'] = self.buffer['out'][bytes:]
        return data
    
    def send(self, data):
        self.buffer['in'] += data
        return len(data)
    
    def fileno(self):
        pass
    
    def close(self):
        pass

class TestProxy(unittest.TestCase):
    
    def setUp(self):
        self.proxy = Proxy(Client())
    
    def test_http_get(self):
        self.proxy.client.buffer['out'] += "GET http://httpbin.org/get HTTP/1.1%s" % CRLF
        self.proxy.process_request(self.proxy.recv_from_client())
        self.assertEqual(self.proxy.server, None)
        
        self.proxy.client.buffer['out'] += CRLF.join([
            "User-Agent: curl/7.27.0",
            "Host: httpbin.org",
            "Accept: */*",
            "Proxy-Connection: Keep-Alive",
            CRLF
        ])
        self.proxy.process_request(self.proxy.recv_from_client())
        self.assertFalse(self.proxy.server == None)
        self.assertEqual(self.proxy.host, "httpbin.org")
        self.assertEqual(self.proxy.port, 80)
        
        self.proxy.flush_server_buffer()
        self.assertEqual(self.proxy.buffer['server'], '')
        
        data = self.proxy.recv_from_server()
        while data:
            self.proxy.process_response(data)
            if self.proxy.response.state == HTTP_PARSER_STATE_COMPLETE:
                break
            data = self.proxy.recv_from_server()
        
        self.assertEqual(self.proxy.response.state, HTTP_PARSER_STATE_COMPLETE)
        self.assertEqual(int(self.proxy.response.code), 200)
        self.proxy.close()
    
    def test_https_get(self):
        self.proxy.client.buffer['out'] += CRLF.join([
            "CONNECT httpbin.org:80 HTTP/1.1",
            "Host: httpbin.org:80",
            "User-Agent: curl/7.27.0",
            "Proxy-Connection: Keep-Alive",
            CRLF
        ])
        self.proxy.process_request(self.proxy.recv_from_client())
        self.assertFalse(self.proxy.server == None)
        self.assertEqual(self.proxy.buffer['client'], self.proxy.connection_established_pkt)
        
        self.proxy.flush_client_buffer()
        self.assertEqual(self.proxy.buffer['client'], '')
        
        parser = HttpParser(HTTP_RESPONSE_PARSER)
        parser.parse(self.proxy.client.buffer['in'])
        self.assertEqual(parser.state, HTTP_PARSER_STATE_HEADERS_COMPLETE)
        self.assertEqual(int(parser.code), 200)
        
        self.proxy.client.buffer['out'] += CRLF.join([
            "GET /user-agent HTTP/1.1",
            "Host: httpbin.org",
            "User-Agent: curl/7.27.0",
            CRLF
        ])
        self.proxy.process_request(self.proxy.recv_from_client())
        self.proxy.flush_server_buffer()
        self.assertEqual(self.proxy.buffer['server'], '')
        
        parser = HttpParser(HTTP_RESPONSE_PARSER)
        data = self.proxy.recv_from_server()
        while data:
            parser.parse(data)
            if parser.state == HTTP_PARSER_STATE_COMPLETE:
                break
            data = self.proxy.recv_from_server()
        
        self.assertEqual(parser.state, HTTP_PARSER_STATE_COMPLETE)
        self.assertEqual(int(parser.code), 200)
        self.proxy.close()
    
    def test_proxy_connection_failed(self):
        with self.assertRaises(ProxyConnectFailed):
            self.proxy.process_request(CRLF.join([
                "GET http://unknown.domain HTTP/1.1",
                "Host: unknown.domain",
                CRLF
            ]))
