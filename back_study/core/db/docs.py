# -*- coding: utf-8 -*-
"""数据层 · 文档域 —— 整份导入的章节化资料、论文译文/术语表、草稿缓冲区。

译文/术语表这层是**薄转发**，不写业务逻辑。理由：
  译文读写是纯存取，但「要不要复用已有译文」这种判断会随功能演进，
  放在 db 层里能保证 web 路由和将来的脚本/小程序端**用同一套规则**。
  路由层直接调 backend() 就等于把这个判断复制两份 ——
  而两份判断不一致时症状是「web 端显示已译、小程序端显示未译」，
  极难定位。
"""
import sys

from .base import _next_daily_id, backend, today_str
from .cards import load_custom, save_custom


def load_docs():
    return backend().docs_all()


def load_docs_brief():
    """文档列表用：只要轻字段，**不含 chapters / text**。

    ★ 为什么不直接用 load_docs()：`documents` 表的 chapters(JSON) 与
      doc_text(MEDIUMTEXT，装整篇论文) 是两个大字段，列表页一个都用不到，
      读出来是纯浪费。MySQL 下差别是 `SELECT *` vs 指定 17 个轻列。
      路由层凡是「只要列表」的地方都该走这个，别图省事写 load_docs()。
    """
    try:
        return backend().docs_brief()
    except NotImplementedError:
        # 老后端没实现就退回全量读：功能不缺（字段照样有），只是慢。
        # ★ 用 stderr 而不是静默 fallback —— 降级要看得见。
        sys.stderr.write('[db] 该后端未实现 docs_brief，回退全量读（列表会变慢）\n')
        return backend().docs_all()


def get_doc(did):
    """按 id 取**单篇完整文档**；找不到返回 None。

    ★ 别写 `next((x for x in load_docs() if x.get('id')==did), None)`：
      那是把全部文档（含每篇论文全文）读回来在应用层线性扫。
      这个门面底层是 `WHERE id=%s`，走主键索引。
    """
    try:
        return backend().doc_get(did)
    except NotImplementedError:
        for d in backend().docs_all():
            if d.get('id') == did:
                return d
        return None


def upsert_doc(doc):
    """有 id 就覆盖，没有就新建。chapters 一并存，不做增量合并
    （一份文档要么整存要么整删）。"""
    lst = load_docs()
    did = doc.get('id')
    now = today_str()
    if did:
        for d in lst:
            if d.get('id') == did:
                merged = dict(d)
                merged.update(doc)
                merged['updatedAt'] = now
                backend().doc_put(merged)
                return merged
    did = did or _next_daily_id('doc', lst, now)
    doc = dict(doc)
    doc['id'] = did
    doc.setdefault('createdAt', now)
    doc['updatedAt'] = now
    backend().doc_put(doc)
    return doc


def delete_doc(did):
    st = backend()
    if any(d.get('id') == did for d in st.docs_all()):
        st.doc_del(did)
        return True
    return False


# ★ 2026-11-15 删掉一个重复定义：db.py 时代这里还有第二个 `get_doc(did)`
#   （线性扫版），Python 同名 def 后者覆盖前者，走主键索引的快版本从写下
#   那天起就没执行过 —— pyflakes 的 redefinition 提示把它揪了出来。


# ---------------- 论文译文 / 术语表 ----------------
def trans_all(did):
    return backend().trans_all(did)


def trans_put(did, seg_i, zh, src_hash='', status='', score=None,
              missing=None, model=''):
    backend().trans_put(did, seg_i, zh, src_hash=src_hash, status=status,
                        score=score, missing=missing, model=model)


def trans_clear(did):
    backend().trans_clear(did)


def glossary_all(did):
    return backend().glossary_all(did)


def glossary_put(did, en, zh, locked=False):
    backend().glossary_put(did, en, zh, locked=locked)


def glossary_del(did, en):
    backend().glossary_del(did, en)


def set_doc_ai(did, items, meta=None):
    """把 LLM 精读结果写回章节。items: [{'index': 章节下标, 'ai': {...}}]

    逐章写、逐章存，所以「精读一章看一章」是安全的——中途打断也不会丢已完成的。
    顺带更新 aiDone/aiTotal，前端据此画进度。

    只 put 这一份文档（不是 load 全量再 save 全量）：一份几十章的 PDF
    正文加上 AI 结果能到几百 KB，章节级写操作要是每次都把整个 documents
    表重写一遍，精读十章的代价是重复落盘十倍数据。
    """
    d = get_doc(did)
    if d is None:
        return None
    chs = d.get('chapters') or []
    for it in items:
        k = it.get('index')
        if isinstance(k, int) and 0 <= k < len(chs):
            chs[k]['ai'] = it.get('ai')
    d['chapters'] = chs
    d['aiDone'] = sum(1 for c in chs if c.get('ai'))
    d['aiTotal'] = len(chs)
    if meta:
        d['aiModel'] = meta.get('model')
        d['aiProvider'] = meta.get('provider')
    d['updatedAt'] = today_str()
    backend().doc_put(d)
    return d


def rename_deck(did, title):
    """改卡片组（deck）的名字。

    组名的真相源是**文档标题**；卡和草稿里的 deck 是生成时抄的冗余字符串
    （没有独立的组表，MySQL 里连 deck 列都没有）。所以只改文档不行 ——
    已生成的卡还挂着旧名，下次从这份文档出卡又会按新标题抄一遍，
    同一组会分裂成两个 chips。三处必须一起改：

      1. documents.title（真相源，下次出卡按它抄）
      2. 自定义卡 payload 里的 deck
      3. 草稿里的 deck

    topicPath[1] 也是生成时按标题截的（title[:20]），对得上旧名才跟着改 ——
    手工改过目录路径的卡不动。返回 None 表示文档不存在；{'ok': False} 表示
    参数不合法（空名），由上层转成 HTTP 错误。"""
    doc = get_doc(did)
    if doc is None:
        return None
    new = (title or '').strip()[:60]
    if not new:
        return {'ok': False, 'msg': '组名不能为空'}
    old = str(doc.get('title') or '')
    if new == old:
        return {'ok': True, 'title': new, 'cards': 0, 'drafts': 0}
    upsert_doc({'id': did, 'title': new})

    def fix(c):
        if c.get('deckId') != did:
            return False
        c['deck'] = new
        tp = c.get('topicPath')
        if isinstance(tp, list) and len(tp) >= 2 and tp[1] == old[:20]:
            tp[1] = new[:20]
        return True

    n_cards = n_drafts = 0
    custom = load_custom()
    for c in custom:
        if fix(c):
            n_cards += 1
    if n_cards:
        save_custom(custom)
    drafts = load_drafts()
    for d in drafts:
        if fix(d):
            n_drafts += 1
    if n_drafts:
        save_drafts(drafts)
    return {'ok': True, 'title': new, 'cards': n_cards, 'drafts': n_drafts}


# ---------- 草稿（导入缓冲区） ----------
def load_drafts():
    return backend().drafts_all()


def save_drafts(lst):
    backend().draft_replace(lst)
