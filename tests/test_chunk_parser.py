import unittest
from appurify.tunnel import ChunkParser
from appurify.tunnel import CHUNK_PARSER_STATE_COMPLETE

class TestChunkParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = ChunkParser()
    
    def test_chunk_parse(self):
        self.parser.parse(''.join([
            '4\r\n',
            'Wiki\r\n',
            '5\r\n',
            'pedia\r\n',
            'E\r\n',
            ' in\r\n\r\nchunks.\r\n',
            '0\r\n',
            '\r\n'
        ]))
        self.assertEqual(self.parser.chunk, '')
        self.assertEqual(self.parser.size, None)
        self.assertEqual(self.parser.body, 'Wikipedia in\r\n\r\nchunks.')
        self.assertEqual(self.parser.state, CHUNK_PARSER_STATE_COMPLETE)