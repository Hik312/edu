# -*- coding: utf-8 -*-
"""云端通道（OpenAI 兼容接口）白盒测试：起一个本地 mock 服务，不碰真实云。

覆盖 chat / 流式 / embeddings / vision 四条分支，以及两条容易回归的差异：
  - 云端 embedding **不加** nomic 的 search_document:/search_query: 前缀
  - 请求带 Bearer key，路径带 /v1
llm 的云端常量在 import 时读环境变量，所以 fixture 里 reload 一次，
测完再 reload 回本地通道，避免污染同会话的其他测试。
"""
import importlib.util
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class _Mock(BaseHTTPRequestHandler):
    last = {}

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        body = json.loads(self.rfile.read(n) or b'{}')
        _Mock.last = {'path': self.path, 'body': body,
                      'auth': self.headers.get('Authorization')}
        if self.path.endswith('/embeddings'):
            out = {'object': 'list', 'model': 'mock-embed',
                   'data': [{'index': i, 'embedding': [0.1 * (i + 1), 0.2]}
                            for i in range(len(body.get('input') or []))]}
        else:
            out = {'id': 'x', 'object': 'chat.completion', 'created': 0,
                   'model': 'mock',
                   'choices': [{'index': 0, 'finish_reason': 'stop',
                                'message': {'role': 'assistant',
                                            'content': 'mock-answer'}}]}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture()
def cloud(monkeypatch):
    srv = ThreadingHTTPServer(('127.0.0.1', 0), _Mock)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv('LLM_PROVIDER', 'cloud')
    monkeypatch.setenv('LLM_API_KEY', 'test-key')
    monkeypatch.setenv('LLM_BASE_URL', 'http://127.0.0.1:%d' % srv.server_address[1])
    # test_transjob 在收集阶段会把 sys.modules['llm'] 换成空 stub（全量跑时
    # 这里拿到的就是它）。临时按文件路径装真 llm，测完原样还回去，
    # 不打断依赖 stub 的后续测试。
    saved = sys.modules.get('llm')
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'core', 'llm.py')
    spec = importlib.util.spec_from_file_location('llm', path)
    real = importlib.util.module_from_spec(spec)
    sys.modules['llm'] = real
    spec.loader.exec_module(real)
    yield real
    srv.shutdown()
    monkeypatch.undo()
    if saved is None:
        sys.modules.pop('llm', None)
    else:
        sys.modules['llm'] = saved


def test_cloud_embed_no_prefix(cloud):
    assert cloud.embed(['a', 'b']) == [[0.1, 0.2], [0.2, 0.2]]
    assert _Mock.last['path'] == '/v1/embeddings'
    assert _Mock.last['body']['input'] == ['a', 'b']
    assert _Mock.last['auth'] == 'Bearer test-key'


def test_cloud_embed_off_returns_none(cloud, monkeypatch):
    # AI_OFF 是 import 时读的环境变量，改 env 不够，直接patch 模块常量
    monkeypatch.setattr(cloud, 'AI_OFF', True)
    assert cloud.embed(['a']) is None


def test_cloud_chat(cloud):
    out = cloud._call([{'role': 'user', 'content': 'hi'}], None, 10)
    assert out == 'mock-answer'
    assert _Mock.last['path'] == '/v1/chat/completions'


def test_cloud_stream_chat(cloud):
    got = []
    out = cloud.stream_chat([{'role': 'user', 'content': 'hi'}], got.append)
    assert out == 'mock-answer'
    assert got == ['mock-answer']


def test_cloud_vlm(cloud):
    assert cloud.vlm_caption('aGVsbG8=') == 'mock-answer'
    assert cloud.figure_interpret('aGVsbG8=', caption='x') == 'mock-answer'
    content = _Mock.last['body']['messages'][0]['content']
    assert content[1]['type'] == 'image_url'
    assert content[1]['image_url']['url'].startswith('data:image/png;base64,')


def test_cloud_agent_model(cloud):
    from agent import model
    m = model.chat()
    assert m.invoke('hi').content == 'mock-answer'