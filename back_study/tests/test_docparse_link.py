# -*- coding: utf-8 -*-
"""图领地-题注/图内文字关联状态机（docparse._link_fig）的单元测试。

关联只加字段不改 text —— 这条契约在 test_transjob.py 里用 srcHash 断言
再锁一层；这里测状态机自身的行为（领地 = 列表，合成图场景：连续 img
同属一个领地，图题挂全体）。
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


def test_caption_attaches_to_whole_territory():
    """单图标准布局：图 → 图内文字 → 图题（下方）→ 正文。"""
    fig = _img()
    t = docparse._link_fig([fig], 'figtext', 'Encoder')
    assert fig.get('figtext') == ['Encoder']
    t = docparse._link_fig(t, 'figtext', 'Retriever')
    assert fig['figtext'] == ['Encoder', 'Retriever']
    t = docparse._link_fig(t, 'caption', 'Figure 2: System overview.')
    assert t is None                              # 一个领地吃一个图题后闭合
    assert fig['caption'] == 'Figure 2: System overview.'


def test_composite_figure_cluster_all_get_caption():
    """合成图（实测 AutoGen 抓到的主场景）：15 张小位图连续 = 一个领地，
    图题挂**全体**成员 —— 每个子图的解读卡都能带上正确图题。"""
    cluster = [_img('sub%d' % i) for i in range(3)]
    t = docparse._link_fig(cluster, 'body', 'Month')          # 短标签：领地活着
    assert t is cluster and cluster[0]['figtext'] == ['Month']
    t = docparse._link_fig(t, 'caption', 'Figure 1: AutoGen overview.')
    assert t is None
    for blk in cluster:
        assert blk['caption'] == 'Figure 1: AutoGen overview.'


def test_table_caption_does_not_attach():
    """Table 题注出现在图下方：闭合领地，但**不挂**（张冠李戴防线）。"""
    fig = _img()
    t = docparse._link_fig([fig], 'caption', 'Table 1: Results on MMLU.')
    assert t is None
    assert 'caption' not in fig


def test_prose_closes_territory():
    """图和题注之间隔了长正文 → 领地结束，远处题注不再误挂。"""
    fig = _img()
    t = docparse._link_fig([fig], 'body',
                           'As shown in Figure 2, the system achieves state of the art results '
                           'on all of the benchmarks that we evaluated in this paper.')
    assert t is None                              # 长句 = 真正文，领地结束
    t2 = docparse._link_fig(None, 'caption', 'Figure 2: ...')
    assert t2 is None                             # 没有开口的领地可挂
    assert 'caption' not in fig


def test_appendix_retyped_caption_still_attaches():
    """附录区的图题被 _mark_refs_and_appendix 重打成 appendix —— 前缀优先，
    照样挂上（实测 AutoGen：附录 Figure 5-10 曾全部漏挂）。"""
    fig = _img()
    t = docparse._link_fig([fig], 'appendix', 'Figure 5: Default system message.')
    assert t is None
    assert fig['caption'] == 'Figure 5: Default system message.'


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
