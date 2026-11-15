# -*- coding: utf-8 -*-
"""题库导入解析器的测试 —— 三个格式适配器 + 截断 + 确定性。

这是「上传 → 解析**正确** → 背」这条主链路的守门测试：
解析器是纯函数、确定性，改规则时这里的 golden 全都得是想清楚的。
"""
import pytest

import importer


# ---------- md-qa（JavaGuide / CS-Notes 形态） ----------
MD_FIXTURE = """---
title: 操作系统基础
---
## 一、操作系统基础

### 什么是操作系统？
操作系统是管理计算机硬件与软件资源的程序。

### 功能题？
- 进程管理
- 内存管理

### 空题

## 参考资料
- 略
"""


def test_md_qa_extracts_questions_and_skips_structure():
    r = importer.parse_qa(MD_FIXTURE, 'md-qa', {'domain': 'work'})
    titles = [c['title'] for c in r['cards']]
    assert titles == ['什么是操作系统？', '功能题？']
    # ## 章节（结构）与「参考资料」都不该变成卡
    assert '一、操作系统基础' not in titles and '参考资料' not in titles
    assert [s['title'] for s in r['skipped']] == ['空题']


def test_md_qa_answer_lines_and_fields():
    r = importer.parse_qa(MD_FIXTURE, 'md-qa', {'domain': 'work', 'source': 'JavaGuide'})
    c = r['cards'][0]
    assert c['mechanism'][0].startswith('①')          # 编号与 parse_local 同一套
    assert '管理计算机硬件' in c['mechanism'][0]
    assert c['_draft'] is True and c['_from'] == 'qa'
    assert c['source'] == 'JavaGuide'                  # 溯源字段
    assert c['domain'] == 'work'
    assert len(c['id'].split('-')) == 3                # qa-<指纹>-<序号>


def test_md_qa_code_fence_not_split():
    """代码块里的 `## 注释` 不是标题 —— fence_mask 挡住，块内容进答案。"""
    md = ('### 什么是 keep-alive？\n一条连接传多个请求。\n\n'
          '```python\n## 这不是标题，是注释\ndef f(): pass\n```\n完了。')
    r = importer.parse_qa(md, 'md-qa')
    assert len(r['cards']) == 1
    mech = '\n'.join(r['cards'][0]['mechanism'])
    assert '## 这不是标题，是注释' in mech and 'def f(): pass' in mech


def test_md_qa_qlevel_2():
    """qLevel=2：## 算题面（CS-Notes 的某些文件直接 ## 问答）。"""
    md = '## 什么是 A？\nA 的定义。\n\n## 背景\n一些背景'
    r = importer.parse_qa(md, 'md-qa', {'qLevel': 2})
    assert [c['title'] for c in r['cards']] == ['什么是 A？', '背景']


def test_md_qa_yaml_front_matter_stripped():
    assert 'title: 操作系统基础' not in str(MD_FIXTURE in r for r in [importer.parse_qa(MD_FIXTURE, 'md-qa')])


# ---------- anki-txt ----------
def test_anki_txt_tab_separated_and_html_clean():
    txt = ('#separator:tab\n#html:true\n'
           '什么是进程\t进程是资源分配的基本单位\n'
           '线程?\t<b>线程</b>是调度的基本单位<br>共享地址空间\n'
           '没有tab的行')
    r = importer.parse_qa(txt, 'anki-txt')
    assert len(r['cards']) == 2
    assert r['cards'][0]['title'] == '什么是进程'
    assert r['cards'][1]['mechanism'][0].startswith('①')       # <br> 还原成换行
    assert '<b>' not in r['cards'][1]['mechanism'][0]
    assert [s['title'] for s in r['skipped']] == ['没有tab的行']


# ---------- obsidian-sr ----------
def test_obsidian_sr_single_and_multiline():
    obs = ('#flashcards\n\n'
           'TCP 和 UDP 的区别？::TCP 可靠，UDP 不可靠\n\n'
           '什么是三次握手？\n?\nSYN → SYN+ACK → ACK\n::: 细节是半连接队列')
    r = importer.parse_qa(obs, 'obsidian-sr')
    assert len(r['cards']) == 2
    assert r['cards'][0]['title'] == 'TCP 和 UDP 的区别？'
    # 多行卡的 ::: 是答案的一部分（Obsidian SR 的嵌套约定）
    assert any('半连接队列' in m for m in r['cards'][1]['mechanism'])


# ---------- 截断与确定性 ----------
def test_long_answer_truncated_with_flag():
    md = '### 超长题？\n' + '\n'.join(['很长的一行。' * 20] * 60)
    r = importer.parse_qa(md, 'md-qa')
    assert r['cards'][0]['_truncated'] is True
    assert len(r['cards'][0]['mechanism']) < 60


def test_deterministic_ids_upsert_safe():
    """同一份文本两次解析 → 同一批 id（save_drafts 的 upsert 才能覆盖不翻倍）。"""
    a = importer.parse_qa(MD_FIXTURE, 'md-qa')
    b = importer.parse_qa(MD_FIXTURE, 'md-qa')
    assert [c['id'] for c in a['cards']] == [c['id'] for c in b['cards']]


def test_unknown_format_raises():
    with pytest.raises(ValueError):
        importer.parse_qa('x' * 20, 'pdf')
