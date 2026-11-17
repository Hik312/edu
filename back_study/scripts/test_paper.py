# -*- coding: utf-8 -*-
"""论文识别的回归测试。

跑法：cd back_study; python scripts/test_paper.py
"""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
for _n in ('db', 'llm', 'algostore', 'security', 'docparse', 'importer',
           'classifier', 'pdfmarkup'):
    if _n not in sys.modules:
        m = type(sys)('_stub_' + _n)
        m.__getattr__ = lambda n: (lambda *a, **k: None)
        sys.modules[_n] = m

# 只取论文识别那几段（纯函数，不依赖 FastAPI）
src = open(os.path.join(os.path.dirname(_HERE), 'app', 'routers', 'web', 'docs.py'),
           encoding='utf-8').read()
ns = {}
start = src.index('_PAPER_HINTS')
end = src.index('def _save_original_only')
exec(src[start:end], ns)
_looks_like_paper = ns['_looks_like_paper']

# 词表必须真的被加载进来了（之前切片边界算错时这里会是空的）
assert ns.get('_looks_like_paper'), '没取到 _looks_like_paper'
assert len(ns.get('_PAPER_HINTS', ())) > 0, '词表没加载进来'


def test_paper_by_filename():
    for f in ('arxiv-2308.08155.pdf', 'ACL2024-longpaper.pdf',
              '某会议论文.pdf', 'IEEE-transaction.pdf',
              'springer-chapter.pdf', 'Elsevier-2024.pdf'):
        assert _looks_like_paper(f, ''), '没认出来是论文: %s' % f


def test_unclue_filename_needs_body():
    """★ 文件名没线索时**不能**判成论文 —— 否则所有 PDF 都变论文。
    真实案例 AutoGen.pdf 靠的是首页版面标志（见 test_paper_by_structure）。"""
    assert not _looks_like_paper('AutoGen.pdf', '')


def test_paper_by_content():
    """文件名也没线索，只靠首页正文判断。"""
    body = ('AutoGen: Enabling Next-Gen LLM Applications '
            'Abstract: multi-agent conversation framework. '
            '1 Introduction  Keywords: LLM  DOI: 10.1000/autogen')
    assert _looks_like_paper('doc.pdf', body), '首页特征够明显却没判成论文'


def test_paper_by_structure():
    """★ 回归：文件名没线索时靠首页版面标志识别。

    真实案例：论文叫 `AutoGen.pdf` —— 词表里没有「autogen」，
    只看文件名必然漏判。
    """
    body = ('Abstract In this work we present AutoGen, a framework. '
            'Keywords: LLM, agents  1 Introduction Related work has been '
            'studied. DOI: 10.1000/xyz')
    assert _looks_like_paper('AutoGen.pdf', body), '靠正文特征也没认出来'


def test_single_structure_word_not_enough():
    """单个版面标志不足以判定 —— 技术博客也写 Introduction。"""
    body = '本文介绍一个框架。 Introduction 这里先讲背景。'
    assert not _looks_like_paper('某个教程.pdf', body), '单个标志就判成论文了'


def test_tech_doc_not_paper():
    """★ 回归：技术文档不能被误判成论文。

    误判的代价很高 —— 论文路线只存原件不分章，一份正经技术讲义
    被判成论文就失去了全文搜索和转卡能力。
    """
    for f, t in (
        ('MySQL八股.md', ''),
        ('TypeScript装饰器.pdf', '本文介绍装饰器的语法和使用方法'),
        ('面试题汇总.pdf', '常见面试题整理'),
        ('算法笔记.pdf', '动态规划专题'),
    ):
        assert not _looks_like_paper(f, t), '技术文档被误判成论文: %s' % f


def test_plain_pdf_not_paper():
    """没���线索的 PDF 按普通文档处理（走原有文本路线）。"""
    assert not _looks_like_paper('未命名.pdf', '')


if __name__ == '__main__':
    fails = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith('test_') or not callable(fn):
            continue
        try:
            fn()
            print('  PASS %s' % name)
        except AssertionError as e:
            fails += 1
            print('  FAIL %s: %s' % (name, e))
        except Exception as e:
            fails += 1
            print('  ERROR %s: %s: %s' % (name, type(e).__name__, e))
    print('OK' if not fails else 'FAILED: %d' % fails)
    sys.exit(1 if fails else 0)