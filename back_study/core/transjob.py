# -*- coding: utf-8 -*-
"""译文编排：术语表维护 + 断点续译 + 流式产出。

## 为什么要单独一层，而不是在路由里直接循环调 translate
三件事必须**在所有调用方保持一致**，放路由里就意味着web 端、小程序端、
将来的脚本各写一份，而其中任何一份漏掉都会产生「两边显示不一致」：

1. **指纹比对**：原文改了，旧译文必须作废。这靠 `src_hash` 判断，
   逻辑写在路由里的话，改一次原文要改一个地方 —— 而漏改的后果是
   用户看着「译文对应的是旧版原文」，且没有任何提示。
2. **锁定术语优先**：用户手动改过的术语不能被重新抽取覆盖。
3. **逐段落库**：每段翻完立刻写，断电只丢最后一段。
"""
import hashlib
import sys
import re
import threading
import time

import db
import translate as T

#: 一篇论文最多存多少条译文。理论上段数由 segment() 决定，
#: 这个上限是防「文本异常导致段数爆炸」把库撑爆的最后一道闸。
MAX_SEGMENTS = 4000


# ---------- 任务注册表（2026-11-15） ----------
# ★ 以前「翻译在不在跑」这件事**无状态**：SSE 的 worker 是 daemon 线程，
#   断开连接（刷新页面）它照跑，但前端无从得知 —— 于是用户点「继续翻译」
#   就起了第二个并行线程（逐段 upsert 不会脏数据，但两线程抢同一段
#   = 白烧一倍算力，进度条还互相干扰）。注册表让三件事成为可能：
#   run 防重（409）、GET status 报 running、POST stop 协作式停止。
#   进程内状态：服务重启自然清空 —— 此时也确实没有线程在跑，语义自洽。
_RUNS = {}                                       # did -> {'started': ts, 'cancel': bool}
_RUNS_LOCK = threading.Lock()


def is_running(did):
    with _RUNS_LOCK:
        return bool(_RUNS.get(str(did)))


def running_info(did):
    with _RUNS_LOCK:
        r = _RUNS.get(str(did))
        if not r:
            return {'running': False, 'startedAt': None,
                    'seconds': 0, 'cancelRequested': False}
        return {'running': True,
                'startedAt': time.strftime('%Y-%m-%d %H:%M:%S',
                                           time.localtime(r['started'])),
                'seconds': int(time.time() - r['started']),
                'cancelRequested': bool(r['cancel'])}


def request_cancel(did):
    """请求停止。协作式：当前段翻完就断（单段 3~8s 内响应），已翻段落已落库。"""
    with _RUNS_LOCK:
        r = _RUNS.get(str(did))
        if not r:
            return False
        r['cancel'] = True
        return True


def _cancelled(did):
    with _RUNS_LOCK:
        r = _RUNS.get(str(did))
        return bool(r and r['cancel'])


def _acquire(did):
    """抢任务槽。原子检查+注册 —— 端点的 is_running 检查与线程真正起跑
    之间有窗口，这里才是防双跑的最终防线。"""
    with _RUNS_LOCK:
        if str(did) in _RUNS:
            return False
        _RUNS[str(did)] = {'started': time.time(), 'cancel': False}
        return True


def _release(did):
    with _RUNS_LOCK:
        _RUNS.pop(str(did), None)


def _vlm_pending_rows(doc):
    """figure 段里还没做过 VLM 解读的（model 列没有 vlm: 前缀）。"""
    rows = db.trans_all(doc.get('id'))
    return rows


def src_hash(text):
    """原文指纹。取 md5 前 16 位 —— 只用来判「变了没有」，
    不是安全用途，16 位足够且索引短。"""
    return hashlib.md5((text or '').encode('utf-8')).hexdigest()[:16]


def segments_of(doc):
    """切段 + 补指纹。

    ★ 优先用结构化块（docparse 抽出来的 heading/body/caption/equation/
      bibliography/figure/figtext/table/appendix）：公式/参考文献/图片/图内文字/
      表格/附录段标记 translate=False，翻译时原样保留、不送模型。块侧车不存在
      （老文档 / docx）则退回纯文本分段（全部可译），行为向后兼容。"""
    text = T.doc_text(doc) if hasattr(T, 'doc_text') else (doc.get('text') or '')
    if not text.strip():
        return []
    segs = None
    did = doc.get('id')
    if did:
        try:
            import docparse
            blocks = docparse.load_blocks(did)
            if blocks:
                segs = T.segments_from_blocks(blocks)
        except Exception:
            segs = None
    if segs is None:
        segs = T.segment(text)
    return segs[:MAX_SEGMENTS]


def pending(doc, segs, existing=None, redo=False):
    """要翻哪些段。返回 [{i, text, srcHash}]。

    ★ 复用条件：指纹相同 **且** 译文非空 **且** 占位符没缺。
      少最后一个条件会出这种怪事：某段因为模型漏抄占位符被判 bad，
      用户重跑却因为「这行已经存在」被跳过 —— 永远修不好。
    """
    if existing is None:
        existing = db.trans_all(doc.get('id'))
    out = []
    for s in segs:
        h = src_hash(s['text'])
        row = existing.get(s['i'])
        if not redo and row:
            if (row.get('srcHash') == h and (row.get('zh') or '').strip()
                    and not row.get('missing')):
                continue
        # ★ 必须把 translate/type（以及 figure 段的 caption/figtext）带出去：
        #   run() 把这里的 item 传给 translate_one，而「公式/参考文献/图片段
        #   原样保留」的判断读的是 seg['translate'] —— 以前只带 i/text/srcHash，
        #   判断永远落空，**公式和参考文献一直被白送进文本 LLM**（zh 恰好
        #   ≈ 原文，因为 protect 保住了内容，浪费一次调用还可能被改坏）。
        #   2026-11-15 评测 vlm 链路时暴露。
        out.append({'i': s['i'], 'text': s['text'], 'srcHash': h,
                    'translate': s.get('translate', True),
                    'type': s.get('type', 'body'),
                    'caption': s.get('caption') or '',
                    'figtext': s.get('figtext') or []})
    return out


def build_glossary(doc, force=False):
    """取术语表；库里没有或 force 时重新抽取。

    ★ 用户锁定（locked=1）的条目**永远不被覆盖**：论文里作者自己的
      译法偏好很常见（同一个词不同译者译法不同），
      而自动抽取每次措辞都可能变，一变就把用户改过的东西冲掉。
      症状是「我改的译法刷新一下就没了」—— 那种功能没人会用第二次。

    ★★★ 「有锁定项就直接返回锁定项」是错的 —— 那样会丢掉**所有**自动
      抽出的术语。之前的写法是：
          if locked and not force: return locked
      副作用是用户手动加了一条 few-shot 之后，术语表从 39 条变成 1 条，
      而接口照样 200、翻译照样跑，只是悄悄失去了术语一致性保障。
      正确做法：库里有数据就用库里的（不再重复抽），
      force=True 才重抽，且重抽后把锁定项覆盖回去。
    """
    did = doc.get('id')
    cur = db.glossary_all(did)
    locked = {g['en'].lower(): g for g in cur if g.get('locked')}
    if cur and not force:
        # 库里已有 → 直接用**全部**条目（含自动抽的），锁定项只在译文中优先
        out = {g['en']: {'en': g['en'], 'zh': g.get('zh') or ''} for g in cur
               if (g.get('en') or '').strip() and (g.get('zh') or '').strip()}
        # 同名条目让锁定的赢（build_glossary 返回 dict 便于覆盖）
        for g in locked.values():
            if (g.get('zh') or '').strip():
                out[g['en']] = {'en': g['en'], 'zh': g['zh']}
        return out

    fresh = T.extract_terms(T.doc_text(doc))
    out = {}
    for t in fresh:
        en = (t.get('en') or '').strip()
        if en:
            out[en] = {'en': en, 'zh': t.get('zh') or ''}
    # 锁定的覆盖自动抽的
    for k, g in locked.items():
        if (g.get('zh') or '').strip():
            out[g['en']] = {'en': g['en'], 'zh': g['zh']}
    for v in out.values():
        db.glossary_put(did, v['en'], v['zh'],
                        locked=bool(locked.get(v['en'].lower())))
    return out


def translate_one(seg, segs, terms, model=None, verify=True, timeout=300,
                  did=None, only=None):
    """翻一段。返回可直接入库的 dict。

    流程：保护 → 翻译 → **回填前**校验占位符 → 回填 →（可选）回译校验。
    ★ 顺序不能改：占位符校验必须在 restore 之前，
      回填之后 ⟦Pn⟧ 已经不存在于字符串里，校验必然报「全缺」。

    `only='vlm'`：只处理 figure 段的 VLM 中文解读（mode=vlm 专用），
    其余段落原样返回不送任何模型 —— normal run 与 vlm run 互不越界。
    """
    # ★ 公式 / 参考文献 / 图片 / 图内文字 / 表格 / 附录段：原样保留，不送模型。
    #   zh=src 既省一次 LLM 调用，又彻底避开「公式被翻坏 / 参考文献被胡乱中文化 /
    #   图片 token 被模型吃掉 / 表格数字被改写 / 架构图标签被当句子重写」几类失败。
    if seg.get('translate') is False:
        typ = seg.get('type') or 'keep'
        # ---- figure 段的 VLM 中文解读（mode=vlm，2026-11-15 加）----
        # ★ 解读结果直接进译文表（zh 列），model 列写 'vlm:<模型名>' 做
        #   「已解读」标记 —— 于是它天然享有断点续译：刷新不丢、重跑跳过。
        #   VLM 失败/没装：zh 保持原文、model 留空 → 下次 vlm run 会再试，
        #   不影响 normal run（normal run 从不碰 figure 段）。
        if typ == 'figure' and only == 'vlm' and did:
            row = _vlm_figure(did, seg)
            if row:
                return row
        label = {'equation': '公式', 'bibliography': '参考文献',
                 'figure': '图片', 'figtext': '图内文字',
                 'table': '表格', 'appendix': '附录'}.get(typ, '原文')
        return {'zh': seg['text'], 'status': 'ok', 'score': 1.0,
                'missing': [], 'model': '', 'keep': True,
                'why': '%s原样保留，不翻译' % label}

    protected, vals = T.protect(seg['text'])
    msgs = T.build_segment_messages({**seg, 'text': protected}, segs, terms)
    # ★ temperature 0.15 → 0.1：本地只有 qwen3:8b，温度越高越爱「即兴发挥」
    #   （补句子、并句子、改限定词），而这正是学术翻译最致命的失忠实。
    #   压到 0.1 让它更贴着原文走；术语表 + 占位符已锁定关键内容，
    #   低温度不会让译文变生硬，只会更准。
    raw = T.llm_call(msgs, model, timeout, temperature=0.1, max_tokens=1400)

    # ---- 占位符完整性（针对模型原始返回）----
    ok, missing = T.placeholders_ok(raw, len(vals))
    zh = T.restore(raw, vals)

    status = 'ok' if ok else 'bad'
    score = None
    if not ok:
        # ★ 占位符缺了要**重试一次**，不是直接接受。
        #   8B 漏抄占位符多见于长段落被截断，重试通常能好。
        #   还不行就标 bad —— 让用户看见「这一段需要人工看」，
        #   而不是给一段悄悄少了个数字的译文。
        #   重试温度 0.05：同样是为了「原样照抄占位符」这一件事更稳。
        raw2 = T.llm_call(msgs, model, timeout, temperature=0.05, max_tokens=1600)
        ok2, missing2 = T.placeholders_ok(raw2, len(vals))
        if ok2:
            raw, ok, missing = raw2, True, []
            zh = T.restore(raw, vals)
            status = 'ok'

    if ok and verify:
        passed, score, _back = T.back_verify(seg['text'], zh, model=model)
        # 占位符过了但回译偏了 → warn 不是 bad：
        # 回译距离对「意译」「拆分句子」这类合法译法会偏低，
        # 判成 bad 会把大量好译文误伤，用户就不信这个标记了。
        status = 'ok' if passed else 'warn'

    return {'zh': zh, 'status': status, 'score': score,
            'missing': missing, 'model': model or ''}


def _vlm_figure(did, seg):
    """对一张图跑 VLM 中文解读。成功返回可入库的 row，失败返回 None。

    media token 从段文本里解析，图片按 docparse.media_path 落地读 ——
    段文本就是 `![](media:name)`，token 不会错位。
    """
    import base64

    import docparse
    import llm as core_llm
    if core_llm.AI_OFF:
        return None
    vm = core_llm.vlm_model()
    if not vm:
        return None
    m = re.search(r'!\[\]\(media:([^)]+)\)', seg.get('text') or '')
    if not m:
        return None                       # 图都丢了（media 被清）：按保留处理
    path = docparse.media_path(did, m.group(1))
    if not path:
        return None
    try:
        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('ascii')
    except OSError:
        return None
    out = core_llm.figure_interpret(b64, seg.get('caption') or '',
                                    seg.get('figtext') or [])
    if not out:
        return None
    return {'zh': out, 'status': 'ok', 'score': None, 'missing': [],
            'model': 'vlm:%s' % vm, 'keep': True, 'why': 'VLM 中文解读'}


def run(doc, on_progress=None, model=None, verify=True, limit=0,
        redo=False, start=0, only=None):
    """把一份文档整篇翻完。逐段落库，可中断续跑。

    on_progress(seg_index, n_total, payload) 回调给路由做 SSE 推送。

    only='vlm'（2026-11-15）：只处理 figure 段的中文解读 ——
    normal run（only=None）**从不碰** figure 段，两条通道互不越界；
    解读结果进译文表（zh 列），断点续译天然生效。

    ★ 任务注册表：进入即抢占 did 槽（原子），重复起跑返回 busy；
      每段边界检查 cancel —— 「停止」是协作式的，当前段翻完就断，
      已翻段落已落库，绝不丢成果。
    """
    did = doc.get('id')
    if not _acquire(did):
        return {'ok': False, 'busy': True, 'msg': '已有翻译在跑',
                'total': 0}
    try:
        segs = segments_of(doc)
        if not segs:
            return {'ok': False, 'msg': '这份文档没有可翻译的正文', 'total': 0}
        terms = build_glossary(doc)
        if only == 'vlm':
            # 只挑「figure 段且尚未解读（model 列无 vlm: 前缀）」的段。
            # ★ 单次上限：一篇论文 177 张图 × 每张 5~15s = 一个多小时，
            #   一口气跑完既占死模型又让前端等太久。断点续译兜底：
            #   每次跑 20 张，点「图注解读」继续下一批。
            rows = db.trans_all(did)
            todo = [{'i': s['i'], 'text': s['text'],
                     'srcHash': src_hash(s['text']),
                     'translate': s.get('translate', True),
                     'type': s.get('type', 'body'),
                     'caption': s.get('caption') or '',
                     'figtext': s.get('figtext') or []}
                    for s in segs if s.get('type') == 'figure'
                    and not (rows.get(s['i']) or {}).get('model', '').startswith('vlm:')]
            todo = todo[:20]
        else:
            todo = pending(doc, segs, redo=redo)
        if start:
            todo = [t for t in todo if t['i'] >= start]
        if limit:
            todo = todo[:limit]

        done = 0
        cancelled = False
        for item in todo:
            if _cancelled(did):
                # 协作式停止：当前段翻完、下一段开跑前退出。
                # 已翻段落都已落库，remaining 会让前端显示「还剩 N 段」。
                cancelled = True
                break
            try:
                row = translate_one(item, segs, terms, model=model,
                                    verify=verify, did=did, only=only)
            except Exception as e:
                # ★ 单段失败不能让整篇停下：261 段翻到第 200 段断了，
                #   前 200 段已经落库是实打实的成果，不能因为一段网络抖动全丢。
                row = {'zh': '', 'status': 'bad', 'score': None,
                       'missing': [], 'model': model or '',
                       'error': str(e)[:200]}
                # ★★ 必须**同时打到 stderr**。只在返回值里带 error 是不够的：
                #   SSE 帧有error 字段但前端通常不显示它，于是表现是
                #   「翻译全部标红、一条错误信息都没有、0 秒就结束」。
                #   而真因（模型连接失败 / 提示词超长）在这里被 except 吞掉了，
                #   排查时完全无从下手 —— 「静默的批量失败」比崩溃更难查。
                sys.stderr.write('[translate] 段 %d 失败：%s\n'
                                 % (item['i'], str(e)[:200]))
            db.trans_put(did, item['i'], row['zh'], src_hash=item['srcHash'],
                         status=row['status'], score=row['score'],
                         missing=row.get('missing'), model=row.get('model') or '')
            done += 1
            if on_progress:
                on_progress(item['i'], len(segs), row)
        res = {'ok': True, 'total': len(segs), 'done': done,
               'remaining': len(pending(doc, segs))}
        if cancelled:
            res['cancelled'] = True
        if only == 'vlm':
            res['only'] = 'vlm'
        return res
    finally:
        _release(did)


def status_of(doc):
    """进度概览：给前端画进度条。

    ★ 口径必须与 pending() 一致：「已译」= 有译文 + 指纹对 + 占位符齐。
      如果这里只数「有多少行」，那么 bad 段（占位符缺）也会被算成完成，
      进度条显示 100% 而实际还有段要重翻。
    """
    did = doc.get('id')
    segs = segments_of(doc)
    rows = db.trans_all(did)
    ok = warn = bad = 0
    for s in segs:
        r = rows.get(s['i'])
        if not r or not (r.get('zh') or '').strip():
            continue
        if r.get('srcHash') != src_hash(s['text']) or r.get('missing'):
            continue                      # 该翻的还没翻
        st = r.get('status')
        if st == 'bad':
            bad += 1
        elif st == 'warn':
            warn += 1
        else:
            ok += 1
    return {'total': len(segs), 'ok': ok, 'warn': warn, 'bad': bad,
            'done': ok + warn, 'pending': max(0, len(segs) - ok - warn - bad)}


_CJK = re.compile(r'[一-鿿]')


def looks_translatable(doc):
    """这份文档值不值得翻。

    判据是「有没有大量英文句子」而不是「是不是 paper」：
    已经译成中文的资料再翻一遍是纯浪费（一次 261 段要跑几十分钟）。
    用中文字符占比判断：中文技术文档里汉字占比通常 >15%，
    而英文论文正文几乎为 0。
    """
    text = doc.get('text') or ''
    if len(text) < 500:
        return False
    sample = text[:20000]
    zh = len(_CJK.findall(sample))
    # 汉字占比 3% 以下视为外文。留这么低的门槛是因为
    # 「英文论文 + 中文图注」混合的样本里汉字可能只有 2%。
    return (zh / max(len(sample), 1)) < 0.03