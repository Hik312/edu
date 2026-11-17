# -*- coding: utf-8 -*-
"""联网搜索 —— 360 搜索（so.com），免 key、标准库直连。

为什么是 360：本机实测 duckduckgo / searx / yahoo 超时被墙，百度反爬，
ecosia 返回备案页，Bing（HTML 和 RSS）对本机只回**查询不敏感**的结果
（"Spring Boot 4 release date" 和 "spring mvc hello world" 给同一套首页级
链接）—— 只有 360 返回真正按查询变化的结果，中文查询质量最好
（实测"Spring Boot 4 发布时间"直接命中发布文章）。免 key、不要 cookie。

联网是**可选增强**：任何失败（超时、被限流、结构变了）都返回 [] /
说明句，绝不抛异常 —— 调用方拿到空结果就只用卡片资料回答，
问答本身不能被联网打断。

换来源（Tavily / SerpAPI / Bing API v7）时只要保持 web_search() 的返回形状
[{'title', 'url', 'snippet'}]，调用方（nodes.retrieve / runtime._react_ground）
一行不用改。
"""
import html
import re
import urllib.parse
import urllib.request

_SO_URL = 'https://www.so.com/s?q=%s'
# 必须带 UA + Accept-Language：不带的请求 360 直接不给结果
_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
_HEADERS = {'User-Agent': _UA, 'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'}
_TIMEOUT = 8          # 网页是问答的底料之一，不能让慢请求拖垮整个问答
_MAX_ROWS = 6
_SNIP = 300           # 摘要限长：底料每轮都带，不能喂爆上下文窗口


def _strip(s):
    """HTML 片段 → 纯文本（去标签、解实体、压空白）。"""
    t = re.sub(r'<[^>]+>', ' ', s or '')
    t = html.unescape(t)
    return re.sub(r'\s+', ' ', t).strip()


def _snippet(block):
    """结果块里的摘要：优先 res-list-summary，其次 res-comm-con 里的 <p>。

    顺手洗掉 360 塞进摘要的页面噪音（"发贴时间"元信息、结尾的"xx 反馈"）。"""
    sn = ''
    m = re.search(r'class="res-list-summary[^"]*"[^>]*>(.*?)</div>',
                  block, re.S)
    if m:
        sn = _strip(m.group(1))
    if not sn:
        m = re.search(r'class="res-comm-con[^"]*"[^>]*>(.*?)</div>',
                      block, re.S)
        if m:
            ps = re.findall(r'<p[^>]*>(.*?)</p>', m.group(1), re.S)
            sn = _strip(' '.join(ps))
    if not sn:
        m = re.search(r'<p[^>]*>(.*?)</p>', block, re.S)
        sn = _strip(m.group(1)) if m else ''
    sn = re.sub(r'\s*\S*反馈\s*$', '', sn)
    sn = re.sub(r'^\s*\d+个收藏.*?发贴时间：\s*\S+\s*', '', sn)
    return sn[:_SNIP]


def web_search(query, limit=_MAX_ROWS):
    """搜一句，返回 [{'title', 'url', 'snippet'}]；失败返回 []。

    真实地址在 a 标签的 data-mdurl 上（href 是 so.com 的跳转链接，
    给用户/模型看都没意义）；没有 data-mdurl 的是站内导航/广告，跳过。"""
    q = (query or '').strip()[:200]
    if not q:
        return []
    url = _SO_URL % urllib.parse.quote(q)
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            page = resp.read().decode('utf-8', 'ignore')
    except Exception:
        return []
    rows = []
    # 按结果标题切块，每块里有 标题锚点 + 摘要
    for block in re.split(r'(?=<h3\s+class="res-title">)', page)[1:]:
        a = re.search(r'<h3\s+class="res-title">\s*<a\s([^>]*)>(.*?)</a>',
                      block, re.S)
        if not a:
            continue
        real = re.search(r'data-mdurl="([^"]+)"', a.group(1))
        if not real:
            continue
        title = _strip(a.group(2))
        if not title:
            continue
        rows.append({'title': title,
                     'url': html.unescape(real.group(1)),
                     'snippet': _snippet(block)})
        if len(rows) >= limit:
            break
    return rows


def web_context(question):
    """给模型看的网页资料块（【网页】标题 + 链接 + 摘要）。

    没结果时返回**说明句**而不是空串：空串会让模型以为资料就这些、
    把「联网了」和「没搜到」混为一谈；说明句让它明确该以卡片为准。
    """
    rows = web_search(question)
    if not rows:
        return ('【网页】联网搜索这次没有结果（网络不通或被限流），'
                '回答以卡片资料为准。')
    return '\n\n'.join(
        '【网页】%s\n链接：%s\n摘要：%s'
        % (r['title'], r['url'], r['snippet'] or '（无摘要）')
        for r in rows)
