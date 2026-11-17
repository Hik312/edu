# -*- coding: utf-8 -*-
"""图领地-题注/图内文字关联状态机（docparse._link_fig）的单元测试。

关联只加字段不改 text —— 这条契约在 test_transjob.py 里用 srcHash 断言
再锁一层；这里测状态机自身的行为（领地 = 列表，合成图场景：连续 img
同属一个领地，图题挂全体；图内文字/短标签返回消费动作，调用方据此
**不把它们独立成段**——2026-11-15 用户反馈的正文碎片污染修复）。
"""
import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

# docparse 顶层 import fitz（pymupdf）；没装也能测 —— stub 掉。
for _name in ('fitz', 'pypdf', 'PyPDF2'):
    if _name not in sys.modules:
        try:
            __import__(_name)
        except ImportError:
            sys.modules[_name] = types.ModuleType('_stub_' + _name)

_spec = importlib.util.spec_from_file_location(
    '_docparse_under_test', os.path.join(os.path.dirname(_HERE), 'core', 'docparse.py'))
docparse = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(docparse)


def _img(name='fig1'):
    return {'type': 'figure', 'text': '![](media:%s)' % name, 'page': 0}


def test_figure_caption_below_attaches():
    """标准布局：图 → 图内文字 → 图题（下方）→ 正文。题注挂上后闭合。"""
    fig = _img()
    of, act = docparse._link_fig(None, 'body', '正文')  # 图没开时不吃块
    assert of is None and act == 'pass'
    # 开图由页内循环做（img 分支），这里直接拿领地起步
    t, act = docparse._link_fig([fig], 'figtext', 'Encoder')
    assert act == 'figtext' and fig.get('figtext') == ['Encoder']
    t, act = docparse._link_fig(t, 'figtext', 'Retriever')
    assert fig['figtext'] == ['Encoder', 'Retriever']
    t, act = docparse._link_fig(t, 'caption', 'Figure 2: System overview.')
    assert t is None and act == 'caption'         # 一张图吃一个题注后闭合
    assert fig['caption'] == 'Figure 2: System overview.'


def test_table_caption_does_not_attach():
    """Table 题注出现在图下方：闭合图的领地，但**不挂**（张冠李戴防线）。"""
    fig = _img()
    t, act = docparse._link_fig([fig], 'caption', 'Table 1: Results on MMLU.')
    assert t is None and act == 'tab'
    assert 'caption' not in fig


def test_prose_closes_territory():
    """图和题注之间隔了长正文 → 领地结束，远处题注不再误挂。"""
    fig = _img()
    t, act = docparse._link_fig([fig], 'body', 'As shown in Figure 2, ...')
    assert t is None and act == 'pass'
    t2, act2 = docparse._link_fig(None, 'caption', 'Figure 2: ...')
    assert t2 is None and act2 == 'pass'          # 没有开口的图可挂
    assert 'caption' not in fig


def test_appendix_retyped_caption_still_attaches():
    """附录区的图题被 _mark_refs_and_appendix 重打成 appendix —— 前缀优先，
    照样挂上（实测 AutoGen：附录 Figure 5-10 曾全部漏挂）。"""
    fig = _img()
    t, act = docparse._link_fig([fig], 'appendix', 'Figure 5: Default system message.')
    assert t is None and act == 'caption'
    assert fig['caption'] == 'Figure 5: Default system message.'


def test_composite_figure_cluster_all_get_caption():
    """合成图：连续 img = 一个领地，图题挂全体（AutoGen 实测主场景）。"""
    cluster = [_img('sub%d' % i) for i in range(3)]
    t, act = docparse._link_fig(cluster, 'body', 'Month')     # 短标签：领地活着
    assert act == 'label' and t is cluster
    assert all(blk['figtext'] == ['Month'] for blk in cluster)  # 挂领地全体
    t, act = docparse._link_fig(t, 'caption', 'Figure 1: AutoGen overview.')
    assert t is None
    for blk in cluster:
        assert blk['caption'] == 'Figure 1: AutoGen overview.'


def test_label_action():
    """短标签返回 'label' 动作（调用方据此不独立成段）。"""
    fig = _img()
    t, act = docparse._link_fig([fig], 'body', 'Example Agent Chat')
    assert act == 'label' and fig['figtext'] == ['Example Agent Chat']


def test_caption_prefix_regexes():
    assert docparse._FIG_CAPTION_RE.match('Figure 2: Overview')
    assert docparse._FIG_CAPTION_RE.match('Fig. 3  Architecture')
    assert docparse._FIG_CAPTION_RE.match('图 2 系统结构')
    assert not docparse._FIG_CAPTION_RE.match('Table 2: Results')
    assert docparse._TAB_CAPTION_RE.match('Table 1: Results')
    assert docparse._TAB_CAPTION_RE.match('表 3 对比')
    assert not docparse._TAB_CAPTION_RE.match('Figure 1: Overview')


def test_label_heuristic():
    """短标签容忍的边界：标签收、真句子收不进。"""
    assert docparse._looks_like_label('Month')
    assert docparse._looks_like_label('Hierarchical chat Joint chat')
    assert docparse._looks_like_label('Sorry! Please first pip install')
    assert not docparse._looks_like_label(
        'We evaluate on three benchmarks.')       # 句号结尾 = 真句子
    assert not docparse._looks_like_label('x' * 80)   # 超长
    assert not docparse._looks_like_label('[12] Smith et al.')  # 引文
    assert not docparse._looks_like_label('')


def test_classify_filters_noise():
    """新增的噪声过滤：arXiv 水印 / 首页脚注 / 作者行不再进正文流。"""
    assert docparse._classify_block('arXiv:2308.08155v2  [cs.AI]  3 Oct 2023') == 'skip'
    assert docparse._classify_block(
        '1Corresponding author. Email: auto-gen@outlook.com') == 'skip'
    assert docparse._classify_block('2https://github.com/microsoft/autogen') == 'skip'
    # 作者行（含 ±/†）字母密度高 → body，不再误判公式
    assert docparse._classify_block(
        'Qingyun Wu†, Gagan Bansal∗, Jieyu Zhang±, Yiran Wu†') == 'body'
    # 真公式行字母密度低 → equation
    assert docparse._classify_block('x = ∫σ(t)dt ± βλ') == 'equation'


def test_mark_paper_title():
    """页 0 第一个 body 块 + 窗口内作者特征 → title 类型（保留原文不译）。"""
    blocks = [
        {'type': 'body', 'text': 'AutoGen: Enabling Next-Gen LLM Applications',
         'page': 0},
        {'type': 'body', 'text': 'Qingyun Wu†, Gagan Bansal∗ (Microsoft Research)',
         'page': 0},
        {'type': 'figure', 'text': '![](media:fig)', 'page': 0},
    ]
    docparse._mark_paper_title(blocks)
    assert blocks[0]['type'] == 'title'
    assert blocks[1]['type'] == 'body'            # 作者行不受影响
    # 正文在后的 body 块不被误标（窗口内无作者特征则不动）
    blocks2 = [
        {'type': 'body', 'text': 'A completely ordinary paragraph of text.',
         'page': 0},
        {'type': 'body', 'text': 'Another paragraph with more content here.',
         'page': 0},
    ]
    docparse._mark_paper_title(blocks2)
    assert blocks2[0]['type'] == 'body'
