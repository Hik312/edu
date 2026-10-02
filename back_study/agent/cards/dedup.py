# -*- coding: utf-8 -*-
"""出卡去重：同一份资料导了两次、相邻两章内容重叠时，别再生成一张重复卡。

用本地 embedding 算语义相似度（和 qa/retrieval 的向量检索同一个 Ollama 接口），
而不是标题精确匹配 —— 重复卡往往是同一原理换了个说法，字面不等但语义等。

**退化优先**：embedding 模型没拉 / Ollama 没起 / 任何异常 → 返回 None 放行。
去重是增强不是闸门，绝不能因为它把出卡链路弄挂（和 VectorRetriever 同一态度）。
"""
import os
import sys

import db
import importer
import llm
from .. import config as C

#: 判重阈值（余弦）。0.9 ≈ 基本是同一句话才拦；调低会把「同主题不同考点」误杀。
DUP_SIM = float(os.environ.get('AGENT_DUP_SIM') or 0.9)


def _text(c):
    """参与比对的文本：标题 + 一句话 + 前几条原理。场景/追问是编的，不参与。"""
    parts = [c.get('title') or '', c.get('oneLine') or '']
    parts += list(c.get('mechanism') or [])[:4]
    return '\n'.join(p for p in parts if p)


def _embed(texts):
    """批量向量化。不可用返回 None（调用方据此放行）。"""
    try:
        j = llm._post(llm.OLLAMA + '/api/embed',
                      {'model': C.EMBED_MODEL, 'input': texts}, None, timeout=60)
        embs = j.get('embeddings') if isinstance(j, dict) else None
        return embs or None
    except Exception:
        return None


def _cosine(a, b):
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def find_dup(card):
    """这张卡和库里已有内容重复吗？重复返回 {'id','title','sim'}，否则 None。

    比对池 = 已发布卡 + 草稿池（排除自己）—— 「解析报告刚出的几张互相重复」
    和「和一年前的旧卡重复」都得拦。任何异常都当不去重处理。"""
    try:
        pool = [c for c in db.all_cards() + importer.list_drafts()
                if c.get('id') and c.get('id') != card.get('id')]
        q = _text(card)
        if not pool or not q.strip():
            return None
        vecs = _embed([_text(c) for c in pool] + [q])
        if not vecs or len(vecs) != len(pool) + 1:
            return None
        qv = vecs[-1]
        best, best_sc = None, 0.0
        for c, v in zip(pool, vecs[:-1]):
            sc = _cosine(qv, v)
            if sc > best_sc:
                best, best_sc = c, sc
        if best is not None and best_sc >= DUP_SIM:
            return {'id': best.get('id'), 'title': best.get('title') or '',
                    'sim': round(best_sc, 3)}
        return None
    except Exception as e:
        sys.stderr.write('[dedup] 去重检查失败（放行）：%s\n' % e)
        return None
