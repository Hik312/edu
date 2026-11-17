# -*- coding: utf-8 -*-
"""文档自动分类：规则优先 + LLM 兜底。

返回 {category, domain, tags}，三者都可能为空字符串/空列表。
分类失败不阻断导入 —— 分类是增强，不是门槛。
"""
import re

import llm

DOMAIN_KEYWORDS = {
    '后端·数据库': ['mysql', 'redis', '数据库', '索引', 'sql', 'b+树', '事务', 'mvcc'],
    '后端·Java': ['java', 'jvm', 'spring', '多线程', 'gc', '并发'],
    '后端·架构': ['分布式', '微服务', 'kafka', '消息队列', '架构', '高并发', '负载均衡'],
    '前端': ['javascript', 'vue', 'react', 'css', '浏览器', '前端', 'dom', 'webpack'],
    '算法与数据结构': ['算法', '数据结构', '链表', '二叉树', '动态规划', 'leetcod', '排序'],
    '操作系统': ['操作系统', '进程', '线程', '内存管理', '文件系统', 'linux', '内核'],
    '计算机网络': ['tcp', 'udp', 'http', '网络', '三次握手', 'https', 'dns', 'ip'],
    '人工智能': ['机器学习', '深度学习', '神经网络', 'transformer', 'bert', 'gpt', 'embedding', '模型'],
    '论文': ['arxiv', '论文', 'paper', 'abstract', '引言', '实验', '参考文献'],
}

CATEGORY_RULES = [
    ('论文', ['论文', 'paper', 'arxiv', '期刊', '会议']),
    ('面试资料', ['面试', '八股', '面经', '题库', '问答']),
    ('课程笔记', ['笔记', '课程', '课件', '讲义', '复习资料']),
    ('技术文档', ['文档', 'api', '手册', '指南', 'tutorial', '说明书']),
    ('书籍', ['书', '教材', '第一章', '第二章']),
]


def _classify_rule(title, text, filename):
    """规则层：文件名/标题关键词 → category/domain。总是运行，零依赖。"""
    name = (filename or '').lower()
    title_l = (title or '').lower()
    hay = title_l + ' ' + name

    category = ''
    for cat, kws in CATEGORY_RULES:
        if any(k in hay for k in kws):
            category = cat
            break
    if not category:
        if name.endswith('.pdf'):
            category = '资料'
        elif name.endswith(('.md', '.txt')):
            category = '笔记'
        elif name.endswith('.docx'):
            category = '资料'

    domain = ''
    head = (text or '')[:3000].lower()
    best_score = 0
    for dom, kws in DOMAIN_KEYWORDS.items():
        score = sum(1 for k in kws if k in head or k in hay)
        if score > best_score:
            best_score = score
            domain = dom

    tags = _extract_tags(title, text)
    return {'category': category, 'domain': domain, 'tags': tags}


def _extract_tags(title, text):
    """从标题+正文前 2000 字提取标签：英文术语 + 高频中文词。"""
    hay = (title or '') + ' ' + (text or '')[:2000]
    en = list(dict.fromkeys(re.findall(r'[A-Za-z][A-Za-z0-9_]{3,}', hay)))[:5]
    cnt = {}
    for run in re.findall(r'[\u4e00-\u9fa5]{4,}', hay):
        for n in (2, 3):
            for i in range(len(run) - n + 1):
                g = run[i:i + n]
                cnt[g] = cnt.get(g, 0) + 1
    cn = sorted([g for g, c in cnt.items() if c >= 2], key=lambda g: -cnt[g])[:3]
    return list(dict.fromkeys(en + cn))[:8]


def _classify_llm(title, text):
    """LLM 层：让模型输出 {category, domain, tags}。失败返回空 dict。"""
    try:
        st = llm.status()
        if not st.get('ok'):
            return {}
        prompt = (
            '根据以下文档标题和内容开头，判断它的分类。输出严格 JSON，不要解释：\n'
            '{"category": "论文|面试资料|课程笔记|技术文档|资料|笔记|其他", '
            '"domain": "后端·数据库|后端·Java|后端·架构|前端|算法与数据结构|'
            '操作系统|计算机网络|人工智能|其他", '
            '"tags": ["标签1", "标签2"]}\n\n'
            '标题：%s\n\n内容开头：\n%s' % (title or '', (text or '')[:2000])
        )
        raw = llm._call(
            [{'role': 'user', 'content': prompt}],
            st.get('model'), timeout=60, max_tokens=300,
        )
        out = llm._clean_json(raw)
        if not isinstance(out, dict):
            return {}
        return {
            'category': str(out.get('category') or ''),
            'domain': str(out.get('domain') or ''),
            'tags': out.get('tags') if isinstance(out.get('tags'), list) else [],
        }
    except Exception:
        return {}


def classify_doc(title, text, filename):
    """规则 + LLM 结合分类。规则先跑，LLM 结果覆盖规则。

    任何一步失败都不抛异常 —— 分类是导入的附属产物，不能阻断主流程。"""
    result = _classify_rule(title, text, filename)
    llm_result = _classify_llm(title, text)
    for key in ('category', 'domain'):
        if llm_result.get(key):
            result[key] = llm_result[key]
    if llm_result.get('tags'):
        merged = list(dict.fromkeys(llm_result['tags'] + result.get('tags', [])))
        result['tags'] = merged[:8]
    return result
