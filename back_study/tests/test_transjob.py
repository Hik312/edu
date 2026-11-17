# -*- coding: utf-8 -*-
"""transjob 的任务注册表 / 协作式取消 / vlm 过滤 的单元测试。

transjob 顶层 import db / translate（translate 又 import llm）——按
scripts/test_chapter_split.py 的 stub 模式隔离：用可控的假 db +
真 translate，把「注册表语义」从存储细节里剥出来测。
"""
import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(os.path.dirname(_HERE), 'core')
sys.path.insert(0, _HERE)


def _mk_stub_db():
    """可控的假 db：译文存内存 dict，术语表给一条锁定的（让 build_glossary
    不去走 LLM 抽取那条路）。"""
    m = types.ModuleType('_stub_db')
    m._store = {}

    def trans_all(did):
        return dict(m._store.get(str(did), {}))

    def trans_put(did, i, zh, **kw):
        m._store.setdefault(str(did), {})[i] = dict({'zh': zh}, **kw)

    m.trans_all = trans_all
    m.trans_put = trans_put
    m.glossary_all = lambda did: [{'en': 'model', 'zh': '模型', 'locked': True}]
    m.trans_clear = lambda did: m._store.pop(str(did), None)
    return m


for _name in ('db', 'llm', 'docparse', 'security', 'algostore'):
    # ★ 强制覆盖而不是「没有才放」：pytest 按字母序收集，别的测试模块
    #   （或 conftest 链）可能已经把真 db 拉进了 sys.modules —— 那样
    #   `sys.modules['db']._store` 就会 AttributeError。测试套件里没有任何
    #   模块需要真 db（全是纯函数/自带 stub），覆盖是安全的。
    sys.modules[_name] = _mk_stub_db() if _name == 'db' else \
        types.ModuleType('_stub_' + _name)

# 真 translate（分章/切段/占位符都是要测的真逻辑），其内部的 llm 调用
# 落在 stub 上不会真的发请求。
_spec_t = importlib.util.spec_from_file_location(
    '_translate_under_test', os.path.join(_CORE, 'translate.py'))
translate_mod = importlib.util.module_from_spec(_spec_t)
sys.modules['translate'] = translate_mod
_spec_t.loader.exec_module(translate_mod)

_spec = importlib.util.spec_from_file_location(
    '_transjob_under_test', os.path.join(_CORE, 'transjob.py'))
transjob = importlib.util.module_from_spec(_spec)
sys.modules['transjob'] = transjob
_spec.loader.exec_module(transjob)

sys.modules['db']._store.clear()

BLOCKS = [
    {'type': 'heading', 'text': '1. Introduction', 'page': 0},
    {'type': 'body', 'text': 'This paper studies memory systems.', 'page': 0},
    {'type': 'figure', 'text': '![](media:fig1)', 'page': 0,
     'caption': 'Figure 1: Overview.', 'figtext': ['Encoder', 'Retriever']},
    {'type': 'body', 'text': 'We evaluate on three benchmarks.', 'page': 1},
]


def _doc(did='d1'):
    return {'id': did, 'text': 'irrelevant'}


def _stub_docparse_blocks():
    """segments_of 走 docparse.load_blocks —— stub 掉的 docparse 给真块。"""
    sys.modules['docparse'].load_blocks = lambda did: list(BLOCKS)


def test_segments_carry_caption_and_text_unchanged():
    """figure 段带 caption/figtext 附加字段，但 text 一字不改 ——
    srcHash 只按 text 算，旧文档译文不因扩列失效（拆包轮的硬约束）。"""
    _stub_docparse_blocks()
    segs = transjob.segments_of(_doc())
    fig = [s for s in segs if s.get('type') == 'figure'][0]
    assert fig['text'] == '![](media:fig1)'
    assert fig['caption'] == 'Figure 1: Overview.'
    assert fig['figtext'] == ['Encoder', 'Retriever']
    # translate=False 保持不变（normal run 不会碰它）
    assert fig['translate'] is False


def test_registry_lifecycle():
    did = 'reg1'
    assert not transjob.is_running(did)
    assert transjob._acquire(did)
    assert transjob.is_running(did)
    assert not transjob._acquire(did)              # 双跑防线：原子抢占
    transjob._release(did)
    assert not transjob.is_running(did)
    assert not transjob.request_cancel(did)        # 没任务可取消 → False


def test_run_registers_and_releases():
    _stub_docparse_blocks()
    sys.modules['db']._store.clear()
    calls = []

    def fake_translate_one(seg, segs, terms, **kw):
        calls.append(seg['i'])
        return {'zh': '译' + str(seg['i']), 'status': 'ok', 'score': None,
                'missing': [], 'model': 'm'}

    orig = transjob.translate_one
    transjob.translate_one = fake_translate_one
    try:
        res = transjob.run(_doc('reg2'))
        assert res['ok'] is True and res['done'] == len(BLOCKS)
        assert not transjob.is_running('reg2')     # finally 释放
        assert len(calls) == len(BLOCKS)           # 每段都被处理
    finally:
        transjob.translate_one = orig


def test_run_cooperative_cancel():
    """第一段翻完就请求取消 → 第二段开跑前退出，已翻段落已落库。"""
    _stub_docparse_blocks()
    sys.modules['db']._store.clear()
    did = 'cancel1'

    def fake_translate_one(seg, segs, terms, **kw):
        return {'zh': '译', 'status': 'ok', 'score': None,
                'missing': [], 'model': 'm'}

    orig = transjob.translate_one
    transjob.translate_one = fake_translate_one

    def on_progress(i, total, row):
        transjob.request_cancel(did)               # 第一段翻完立刻请求停

    try:
        res = transjob.run(_doc(did), on_progress=on_progress)
        assert res.get('cancelled') is True
        assert res['done'] == 1                    # 只翻了第一段
        assert len(sys.modules['db']._store[did]) == 1
        assert not transjob.is_running(did)
    finally:
        transjob.translate_one = orig


def test_vlm_only_targets_figures():
    """only='vlm'：只处理 figure 段且 model 列无 vlm: 前缀的；
    已解读的（model=vlm:...）自动跳过 —— 断点续译语义。"""
    _stub_docparse_blocks()
    did = 'vlm1'
    store = sys.modules['db']._store
    store.clear()
    segs = transjob.segments_of(_doc(did))
    fig_i = [s['i'] for s in segs if s.get('type') == 'figure'][0]
    body_is = [s['i'] for s in segs if s.get('type') != 'figure']
    # 预置：figure 段一条「已解读」的记录
    store[did] = {fig_i: {'zh': '【图】总览', 'srcHash': transjob.src_hash(
        '![](media:fig1)'), 'status': 'ok', 'model': 'vlm:qwen2.5vl:7b'}}

    calls = []

    def fake_translate_one(seg, segs, terms, **kw):
        calls.append((seg['i'], kw.get('only'), kw.get('did')))
        return {'zh': '【图】解读', 'status': 'ok', 'score': None,
                'missing': [], 'model': 'vlm:qwen2.5vl:7b'}

    orig = transjob.translate_one
    transjob.translate_one = fake_translate_one
    try:
        res = transjob.run(_doc(did), only='vlm')
        assert res.get('only') == 'vlm'
        assert res['done'] == 0                    # 唯一的图已解读 → 没活干
        assert calls == []
        # 清掉已解读标记 → 这一次 figure 段会被处理，且只处理它
        store[did][fig_i]['model'] = ''
        res2 = transjob.run(_doc(did), only='vlm')
        assert res2['done'] == 1
        assert calls and calls[0][0] == fig_i
        assert calls[0][1] == 'vlm' and calls[0][2] == did
    finally:
        transjob.translate_one = orig


def test_translate_one_vlm_row_and_fallback():
    seg = {'i': 0, 'text': '![](media:fig1)', 'translate': False,
           'type': 'figure', 'caption': 'Figure 1: Overview.',
           'figtext': ['Encoder']}
    # _vlm_figure 成功 → 返回解读 row
    orig = transjob._vlm_figure
    transjob._vlm_figure = lambda did, s: {
        'zh': '【图】总览\n解读：系统架构。', 'status': 'ok', 'score': None,
        'missing': [], 'model': 'vlm:x', 'keep': True, 'why': 'VLM 中文解读'}
    try:
        row = transjob.translate_one(seg, [], {}, did='d1', only='vlm')
        assert row['zh'].startswith('【图】')
        assert row['model'] == 'vlm:x'
    finally:
        transjob._vlm_figure = orig
    # _vlm_figure 失败（None）→ 退回原样保留，model 空 → 下次 vlm run 再试
    transjob._vlm_figure = lambda did, s: None
    try:
        row = transjob.translate_one(seg, [], {}, did='d1', only='vlm')
        assert row['zh'] == seg['text']
        assert row['model'] == '' and row['keep'] is True
    finally:
        transjob._vlm_figure = orig
    # normal run（only=None）从不碰 figure 段 —— 行为与拆包前完全一致
    row = transjob.translate_one(seg, [], {})
    assert row['zh'] == seg['text'] and 'why' in row
