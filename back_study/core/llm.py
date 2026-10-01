# -*- coding: utf-8 -*-
"""本地大模型精读：把导入资料的一章，整理成「一句话 / 类比 / 重点 / 原理拆解」

两条通道，都只用标准库 urllib（不为这点功能引 SDK）：
  1) Ollama（默认）—— 本机 127.0.0.1:11434，离线、免费、不需要 key
  2) OpenAI 兼容云端接口 —— 设了 LLM_API_KEY 且 LLM_PROVIDER=cloud 才走

为什么不用 LangChain / LangGraph：
  这里要的只是「一次结构化抽取 + 解析失败重试 + 类比不合格重问」，
  三个函数就写完了。引框架会给后端塞进几十 MB 依赖，而收益是负的
  —— 单次 LLM 调用不需要编排，编排的价值在「多步、有分支、要状态」的场景。
  真要跑多步 agent（抽取 → 自检 → 修补 → 合并），那应该是一个独立的、
  可选的脚本，而不是塞进平台主链路。见 README 的说明。
"""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request

OLLAMA = (os.environ.get('OLLAMA_HOST') or 'http://127.0.0.1:11434').rstrip('/')
CLOUD_BASE = (os.environ.get('LLM_BASE_URL') or 'https://api.deepseek.com').rstrip('/')
CLOUD_KEY = os.environ.get('LLM_API_KEY') or ''
CLOUD_MODEL = os.environ.get('LLM_MODEL') or 'deepseek-chat'

# 服务器上根本不想跑 AI（没显卡 / 没装 Ollama / 不想付云上的钱）时设 AI=off。
# 关掉的只是「AI 精读」这一块：背卡、复习、导入分章、文档阅读全都不受影响 ——
# 平台没有任何一处核心功能依赖大模型，AI 是最后一道可选工序。
AI_OFF = (os.environ.get('AI') or '').lower() in ('off', '0', 'false', 'no')

_models_cache = {'at': 0.0, 'list': []}
_MODELS_TTL = 20          # 秒。Ollama 不在时每次探测要等满 4 秒超时，缓存一下别让页面反复卡

# 本机装了多个模型时的优先顺序：指令跟随好、不吐思考链的排前面。
# deepseek-r1 是推理模型，就算关掉 think 出字也慢一些，所以放后面。
PREFER = ['qwen2.5:7b-instruct', 'qwen2.5:7b', 'qwen2.5:3b', 'qwen3:8b',
          'llama3.1:8b', 'glm4:9b', 'deepseek-r1:7b']

# 类比里出现这些词 = 没写成生活场景，要重问
TECH_WORDS = ['数据库', '索引', '缓存', '服务器', '接口', '线程', '进程', '协议',
              '系统', '数据', '代码', '算法', '架构', '请求', '网络', '内存', '框架']

SYS = '''你是技术考点精读助手。把用户给的一段技术内容整理成 JSON：

{
  "oneLine": "一句话结论（<=40字，说清它是什么、有什么用）",
  "analogy": "生活类比（<=40字）",
  "points": ["重点，3-5条，每条<=30字，必须带原文里的具体名词或数字"],
  "mechanism": ["原理拆解，3-5步，每步<=35字，讲清'它怎么跑'的因果链"]
}

硬性要求：
- analogy 必须是日常生活场景（排队 / 图书馆 / 快递 / 做饭 / 开车之类），
  不许出现任何技术词，不许说"就像优化xx"。
- mechanism 要一步一步推进、每步回答"为什么"，不许把 points 换个说法抄一遍。
- points 要保留原文的具体名词和数字，不许泛化成"效率高""很重要"。
- 只输出 JSON，不要 markdown 代码块，不要任何解释。

示例（输入是「HTTP 的 keep-alive」）：
{"oneLine":"keep-alive 让一条 TCP 连接连续传多个请求，省掉反复握手","analogy":"像打电话一次把几件事说完，而不是每句话都挂掉重拨","points":["HTTP/1.0 默认关闭，1.1 默认开启","省掉三次握手和慢启动","由 Connection 头控制","空闲超时后服务端才关"],"mechanism":["建连一次后连接不立刻关闭，socket 留在池里","下一个请求复用同一个 socket，省掉三次握手","复用连接不再从零慢启动，拥塞窗口还在","空闲超过 keepalive_timeout 才被服务端回收"]}'''

REPAIR = ('上一次给的 analogy 里出现了技术词（或者太像说明书）。'
          '重给一个：必须是纯日常生活场景，一个技术词都不许有。'
          '仍然只输出同样的 JSON，不要解释。')


# ---------- 底层 HTTP ----------
def _post(url, payload, headers=None, timeout=300):
    data = json.dumps(payload).encode('utf-8')
    h = {'Content-Type': 'application/json'}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def _get(url, timeout=8):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


# ---------- 通道探测 ----------
def provider():
    if AI_OFF:
        return 'off'
    if CLOUD_KEY and (os.environ.get('LLM_PROVIDER') or '').lower() == 'cloud':
        return 'cloud'
    return 'ollama'


def list_models():
    """本机 Ollama 装了哪些模型。Ollama 没起来就返回空列表，不抛异常。
    带 20 秒缓存：服务器上没 Ollama 时每次探测都要等满 4 秒连接超时，
    一个页面上多问几次就会明显卡顿。"""
    if AI_OFF:
        return []
    now = time.time()
    if now - _models_cache['at'] < _MODELS_TTL:
        return _models_cache['list']
    try:
        j = _get(OLLAMA + '/api/tags', timeout=4)
        out = [m.get('name') for m in (j.get('models') or []) if m.get('name')]
    except Exception:
        out = []
    _models_cache['at'] = now
    _models_cache['list'] = out
    return out


def pick_model(models=None):
    """选一个模型：环境变量 LLM_MODEL 优先，其次按 PREFER 顺序找，最后拿第一个。"""
    env = (os.environ.get('LLM_MODEL') or '').strip()
    models = list_models() if models is None else models
    if env and env in models:
        return env
    for p in PREFER:
        if p in models:
            return p
    return models[0] if models else (env or '')


def status():
    """给前端看的状态：能不能用、用的哪个模型、为什么不能用。
    注意 ok=False 是**正常状态**不是错误 —— 前端据此把 AI 那一块换成提示文字，
    其余功能照常。任何一个分支都不该让前端炸掉。"""
    p = provider()
    if p == 'off':
        return {'ok': False, 'provider': 'off', 'base': '', 'model': '', 'models': [],
                'msg': 'AI 精读已关闭（服务端设了 AI=off）—— 不影响背卡、复习、导入分章'}
    if p == 'cloud':
        if not CLOUD_KEY:
            return {'ok': False, 'provider': 'cloud', 'base': CLOUD_BASE, 'model': '',
                    'models': [], 'msg': '云端模式要设 LLM_API_KEY'}
        return {'ok': True, 'provider': 'cloud', 'base': CLOUD_BASE,
                'model': CLOUD_MODEL, 'models': [],
                'msg': '云端接口 %s · %s' % (CLOUD_BASE, CLOUD_MODEL)}
    models = list_models()
    if not models:
        return {'ok': False, 'provider': 'ollama', 'base': OLLAMA, 'model': '',
                'models': [],
                'msg': ('这台机器上没连上 Ollama（%s）。三选一：① 装 Ollama 并 `ollama pull qwen2.5:7b-instruct`；'
                        '② 设 LLM_PROVIDER=cloud + LLM_API_KEY 走云端；③ 设 AI=off 直接关掉精读。'
                        '关掉不影响背卡、复习、导入分章') % OLLAMA}
    m = pick_model(models)
    st = {'ok': True, 'provider': 'ollama', 'base': OLLAMA, 'model': m,
          'models': models, 'msg': '本地模型 %s（离线、免费）' % m}
    # 视觉模型单列一个字段：cards Agent 看图要用，前端据此提示
    # 「图注生成不可用」而不是等转卡时才发现
    st['vlm'] = vlm_model()
    return st


# ---------- 视觉模型（图片 → 图注） ----------
_tags_cache = {'at': 0.0, 'list': []}
_TAGS_TTL = 20


def _tags():
    """GET /api/tags 的原始模型列表（带 capabilities），20 秒缓存。
    list_models 只要名字；挑视觉模型要 capabilities，所以单独缓存一份。"""
    now = time.time()
    if now - _tags_cache['at'] < _TAGS_TTL:
        return _tags_cache['list']
    try:
        j = _get(OLLAMA + '/api/tags', timeout=4)
        out = [m for m in (j.get('models') or []) if isinstance(m, dict)]
    except Exception:
        out = []
    _tags_cache['at'] = now
    _tags_cache['list'] = out
    return out


def vlm_model():
    """本机可用的视觉模型名；没装返回空串。

    顺序：LLM_VLM_MODEL 环境变量（指定了就用，装没装让调用方报错去）
    → 按 tags 里 capabilities 含 vision 的挑第一个。
    Ollama 的视觉模型叫 qwen2.5vl（没有中间横杠），拉的时候别打错。"""
    env = (os.environ.get('LLM_VLM_MODEL') or '').strip()
    if env:
        return env
    for m in _tags():
        if 'vision' in (m.get('capabilities') or []):
            return m.get('name') or ''
    return ''


def vlm_caption(img_b64, context='', model=None, timeout=300):
    """看图说一句：返回 <=60 字的中文图注。失败抛 RuntimeError。

    只做「看图写一句」这一件事 —— 图注要落到卡片的 images[].caption 上，
    让人扫一眼卡片就知道图在讲什么。OCR 级别的精细识别不是这个链路的活。"""
    if AI_OFF:
        raise RuntimeError('ai_off')
    model = model or vlm_model()
    if not model:
        raise RuntimeError('no_vlm')
    prompt = '用一句中文说明这张图在讲什么'
    if context:
        prompt += '（它出现在「%s」的正文里）' % str(context)[:60]
    prompt += '，60 字以内，只输出这一句，不要任何解释、不要标点开头。'
    payload = {'model': model, 'prompt': prompt, 'images': [img_b64],
               'stream': False,
               'options': {'temperature': 0.2, 'num_predict': 200}}
    try:
        j = _post(OLLAMA + '/api/generate', payload, None, timeout)
    except urllib.error.HTTPError as e:
        # 模型名指定了但没 pull、或 Ollama 版本太老不支持 images
        if e.code == 404:
            raise RuntimeError('no_vlm')
        raise RuntimeError('llm_http:%s' % e.code)
    cap = (j.get('response') or '').strip()
    cap = re.sub(r'^["\'「」]|["\'「」]$', '', cap).strip()
    return cap[:80]


# ---------- 调用 + 解析 ----------
def _clean_json(raw):
    """模型爱把 JSON 包在 ```json 里，还爱在前后加一句话。逐层剥。"""
    s = (raw or '').strip()
    s = re.sub(r'^```(?:json)?\s*', '', s)
    s = re.sub(r'\s*```$', '', s)
    try:
        return json.loads(s)
    except ValueError:
        pass
    m = re.search(r'\{[\s\S]*\}', s)          # 退一步：抓最外层的花括号
    if not m:
        raise RuntimeError('llm_not_json')
    try:
        return json.loads(m.group(0))
    except ValueError:
        # ★ 必须在这里把 ValueError 翻成 RuntimeError。
        # 调用方的契约是「失败抛 RuntimeError，上层转成人话」——见 enrich 的
        # docstring，以及 routers/ai.py 只 `except RuntimeError`。从前这一步
        # 漏出原始 ValueError → /api/llm/enrich 直接 500，用户在页面上看到的
        # 是「服务器错误」，而不是「模型这次没吐对 JSON，重试一下」。
        # 触发条件很常见：模型在 JSON 后面又补一段带花括号的说明，
        # 正则 `\{[\s\S]*\}` 会一路吃到最后一个 `}`，json.loads 必然失败。
        # 旁证：importer.parse_llm 里明确写了 except ValueError ——
        # 说明这个异常类型是已知的，只是 enrich 那条链没接住。
        raise RuntimeError('llm_not_json')


def _drop_think(raw):
    return re.sub(r'<think(?:ing)?>[\s\S]*?</think(?:ing)?>', '', raw or '').strip()


def _call(messages, model, timeout, temperature=0.15, max_tokens=900):
    p = provider()
    if p == 'cloud':
        payload = {'model': model or CLOUD_MODEL, 'messages': messages,
                   'temperature': temperature, 'max_tokens': max_tokens}
        j = _post(CLOUD_BASE + '/v1/chat/completions', payload,
                  {'Authorization': 'Bearer ' + CLOUD_KEY}, timeout)
        return _drop_think(j['choices'][0]['message']['content'])
    payload = {'model': model, 'messages': messages, 'stream': False,
               'options': {'temperature': temperature, 'num_predict': max_tokens}}
    # 关掉思考链：deepseek-r1 这类模型不关掉会把 token 全烧在思考上，
    # 80 个 token 出来是空的。不支持 think 字段的老版本会报错，降级重试一次。
    payload['think'] = False
    try:
        j = _post(OLLAMA + '/api/chat', payload, None, timeout)
    except urllib.error.HTTPError:
        payload.pop('think', None)
        j = _post(OLLAMA + '/api/chat', payload, None, timeout)
    return _drop_think(j.get('message', {}).get('content') or '')


def _norm(o):
    """把模型吐的东西收拾干净：类型、长度、空值。模型不听话是常态，不收拾前端会崩。"""
    def s(v, n):
        return ('' if v is None else str(v)).strip()[:n]

    def arr(v, n, each):
        if not isinstance(v, list):
            v = [v] if v else []
        out = []
        for x in v:
            t = s(x, each)
            if t:
                out.append(t)
        return out[:n]

    return {
        'oneLine': s(o.get('oneLine') or o.get('oneliner') or o.get('一句话'), 90),
        'analogy': s(o.get('analogy') or o.get('类比'), 90),
        'points': arr(o.get('points') or o.get('重点'), 6, 70),
        'mechanism': arr(o.get('mechanism') or o.get('原理拆解'), 6, 80),
    }


def _bad_analogy(a):
    if not a or len(a) < 6:
        return True
    return any(w in a for w in TECH_WORDS)


def enrich(title, body, model=None, timeout=300, self_check=True):
    """把一章正文整理成结构化精读。返回 dict（含 _meta）。
    失败抛 RuntimeError，上层转成人话提示，不要让它变 500。"""
    if AI_OFF:
        raise RuntimeError('ai_off')
    text = (body or '').strip()
    if len(text) < 20:
        raise RuntimeError('too_short')
    p = provider()
    model = model or (CLOUD_MODEL if p == 'cloud' else pick_model())
    if not model:
        raise RuntimeError('no_model')

    user = ('标题：%s\n\n正文：\n%s' % (title or '（无标题）', text[:6000]))
    msgs = [{'role': 'system', 'content': SYS}, {'role': 'user', 'content': user}]
    t0 = time.time()
    raw = _call(msgs, model, timeout)
    out = _norm(_clean_json(raw))
    tries = 1

    # 自检：类比写成说明书了就重问一次。这一步就是「质检」——
    # 一个带条件的重试而已，不需要为此上 LangGraph。
    if self_check and _bad_analogy(out['analogy']) and tries < 2:
        tries += 1
        msgs2 = msgs + [{'role': 'assistant', 'content': json.dumps(out, ensure_ascii=False)},
                        {'role': 'user', 'content': REPAIR}]
        try:
            out2 = _norm(_clean_json(_call(msgs2, model, timeout)))
            if not _bad_analogy(out2['analogy']):
                out = out2
        except Exception:
            pass                                  # 重问失败就用第一版，别把好结果丢了
    out['_meta'] = {'provider': p, 'model': model, 'ms': int((time.time() - t0) * 1000),
                    'tries': tries}
    return out


BATCH_SYS = '''你是技术考点精读助手。用户会给你多段技术内容（带编号），
逐段整理成 JSON 数组输出：

{"items":[{"i":0,"oneLine":"...","analogy":"...","points":["..."],"mechanism":["..."]},
          {"i":1,...}]}

每个字段的要求：
- oneLine：一句话结论（<=40字），说清它是什么、有什么用
- analogy：生活类比（<=40字），必须是日常生活场景（排队/图书馆/快递/做饭/开车），不许出现任何技术词
- points：重点 3-5 条（<=30字），必须带原文里的具体名词或数字
- mechanism：原理拆解 3-5 步（<=35字），讲清"它怎么跑"的因果链，不许把 points 抄一遍
- i 必须和输入的编号一一对应，不许漏、不许改
只输出 JSON，不要 markdown 代码块，不要解释。'''


def _norm_many(raw, n):
    out = _clean_json(raw)
    if isinstance(out, dict):
        out = out.get('items') or out.get('cards') or []
    got = {}
    for k, o in enumerate(out if isinstance(out, list) else []):
        if not isinstance(o, dict):
            continue
        i = o.get('i')
        i = k if not isinstance(i, int) else i
        if 0 <= i < n:
            got[i] = _norm(o)
    return got


def _bigrams(s):
    s = re.sub(r'\s+', '', s or '')
    return {s[i:i + 2] for i in range(len(s) - 1)}


def align_score(src, ai):
    """批量精读的真实风险：章节又短又相邻，模型会把 A 章的内容安到 B 章头上。
    用「返回值与原文的字符二元组重合度」做质检 —— 对不上就单章重跑。
    类比不参与打分：它本来就该是另一个领域的生活场景，重合度天然为 0。"""
    a = _bigrams(src)
    if not a:
        return 1.0
    txt = ' '.join([ai.get('oneLine') or ''] + (ai.get('points') or [])
                   + (ai.get('mechanism') or []))
    b = _bigrams(txt)
    if not b:
        return 0.0
    return len(a & b) / float(len(b))


def enrich_many(items, model=None, timeout=600, batch=4, min_align=0.10):
    """一次送多章，让模型返回数组——15 章逐章调要 90 秒，批量能压到 1/3。
    某一批解析失败就退化成逐章调，不因为一批坏了整篇没结果。
    items: [{'title','body'}]，返回 [{...}] 与输入等长，失败的位是 None。"""
    if AI_OFF:
        raise RuntimeError('ai_off')
    p = provider()
    model = model or (CLOUD_MODEL if p == 'cloud' else pick_model())
    if not model:
        raise RuntimeError('no_model')
    results = [None] * len(items)
    t0 = time.time()

    for start in range(0, len(items), batch):
        chunk = list(range(start, min(start + batch, len(items))))
        parts = []
        for k, i in enumerate(chunk):
            t = (items[i].get('title') or '').strip()
            b = (items[i].get('body') or '').strip()[:2500]
            parts.append('[%d] 标题：%s\n%s' % (k, t or '（无标题）', b))
        msgs = [{'role': 'system', 'content': BATCH_SYS},
                {'role': 'user', 'content': '\n\n---\n\n'.join(parts)}]
        try:
            raw = _call(msgs, model, timeout, max_tokens=min(3000, 700 * len(chunk) + 300))
            got = _norm_many(raw, len(chunk))
        except Exception:
            got = {}
        # 质检：按 i 对上了不代表内容对上了。串味的、类比写成说明书的，都退回单章重跑。
        for k, i in enumerate(chunk):
            if k not in got:
                continue
            r = got[k]
            body = items[i].get('body') or ''
            if align_score(body, r) >= min_align and not _bad_analogy(r['analogy']):
                results[i] = r
        # 缺谁补谁：单章调（enrich 内部还会再修一次类比）
        for k, i in enumerate(chunk):
            if results[i] is not None:
                continue
            if len((items[i].get('body') or '').strip()) < 20:
                continue
            try:
                results[i] = enrich(items[i].get('title'), items[i].get('body'),
                                    model=model, timeout=timeout)
            except Exception:
                results[i] = None

    for r in results:
        if isinstance(r, dict):
            r.pop('_meta', None)
    meta = {'provider': p, 'model': model, 'ms': int((time.time() - t0) * 1000)}
    return results, meta


def to_card(chapter, ai, opts=None):
    """把一章 + 它的精读结果，转成一张卡的草稿（走现有草稿→入库流程）。
    这样「导入的资料」也能变成和手写卡一样带类比/重点/原理拆解的卡片。"""
    opts = opts or {}
    title = (chapter.get('title') or '').strip() or '未命名'
    mech = ai.get('mechanism') or []
    ords = '①②③④⑤⑥⑦⑧⑨⑩'
    mech = [(ords[k] + ' ' + s) if k < len(ords) else ('%d. %s' % (k + 1, s))
            for k, s in enumerate(mech)]
    body = (chapter.get('body') or '').strip()
    # id 用标题的哈希：标题基本是中文，slug 化会把中文全滤掉，
    # 多章都退化成同一个 id，入库时会互相覆盖
    cid = opts.get('id') or ('ai-' + hashlib.md5(title.encode('utf-8')).hexdigest()[:8])
    card = {
        'id': cid,
        'domain': opts.get('domain') or '待归类',
        'category': opts.get('category') or '',
        'subject': opts.get('subject') or '',
        'topicPath': list(opts.get('topicPath') or ['导入', title[:20]]),
        'title': title[:60],
        'oneLine': ai.get('oneLine') or body[:60],
        'analogy': ai.get('analogy') or '',
        'why': ai.get('oneLine') or '',
        'mechanism': mech or [l for l in body.split('\n') if l.strip()][:5],
        'keywords': opts.get('keywords') or [],
        'scene': ['（待补充：在你做过的项目里这条用在哪）'],
        'interviewQ': ['（待补充：面试官会怎么追问这条）'],
        '_draft': True,
        '_from': 'llm-doc',
    }
    # 卡片组（文件夹）：这张卡出自哪份文档。手写卡没有这个概念，不加键 ——
    # 空字符串会让卡片墙的「组」chips 里冒出一堆无名组。
    if opts.get('deck'):
        card['deck'] = str(opts['deck'])[:60]
        card['deckId'] = opts.get('deckId') or ''
    return card


# ---------- 文档结构精修（cards Agent 的 structure 阶段） ----------
# 为什么要有这一步：规则分章（importer.parse_document 的五级降级）对排版
# 花哨的大文档经常切错 —— 漏标题、层级错、碎块没合并。用户反馈的
# 「不能准确弄成卡片」一半出在这里。修法不是再堆正则，而是把规则切出来的
# **候选清单**交给模型定夺：输入只有标题+字数+开头几十字，不塞全文，
# 所以几千字的文档也不会爆上下文。
STRUCT_SYS = '''你是文档结构专家。用户给的是「规则初切」的章节清单（编号 | 层级 | 标题 | 字数 | 正文开头）。
规则切分的常见错误：漏标题（该是章节的行被当成正文）、层级错、该合并的碎块没合并、不该切的被切开。

输出严格 JSON：
{"docTitle":"文档总标题（<=30字）","chapters":[{"idx":[0],"title":"小节标题","level":1}, ...]}

硬性要求：
- chapters 是对 0..N-1 的**顺序划分**：每个下标恰好出现一次、组内升序、组间按顺序衔接；
  不许漏下标、不许重复、不许乱序（违反整份作废）。
- 相邻且同属一节的碎块合并成一章；正文太长的块不要拆（拆分是后面按章出卡的事）。
- title 给准确的中文标题（<=30字）：原本有标题就修顺，无标题的块要起一个能看懂内容的标题。
- level 只用 1（大章）/ 2（小节）/ 3（子节）。
- 原结构大部分是对的：只修明显的错，不要为改而改。
- 只输出 JSON，不要 markdown 代码块，不要解释。'''


def refine_structure(items, doc_title='', model=None, timeout=300):
    """规则初切的章节摘要 → LLM 结构方案。

    items: [{'title','level','chars','head'}]（parse_document 的结果，不带正文）
    返回 plan：{'docTitle': str, 'chapters': [{'idx':[..],'title','level'}]}
    结构是否真的成立由 importer.apply_structure 校验 —— 模型抽风时那一步
    会拒绝执行并保留原结构，所以这里只管拿回 JSON。失败抛 RuntimeError。"""
    if AI_OFF:
        raise RuntimeError('ai_off')
    p = provider()
    model = model or (CLOUD_MODEL if p == 'cloud' else pick_model())
    if not model:
        raise RuntimeError('no_model')
    if not items:
        raise RuntimeError('too_short')

    lines = []
    for i, it in enumerate(items):
        lines.append('[%d] 层级%s | %s | %d字 | 开头：%s' % (
            i, it.get('level'), (it.get('title') or '（无标题）')[:40],
            int(it.get('chars') or 0), (it.get('head') or '')[:60]))
    user = '文档标题：%s\n\n规则初切的章节清单（共%d块）：\n%s' % (
        (doc_title or '（未知）')[:60], len(items), '\n'.join(lines))

    msgs = [{'role': 'system', 'content': STRUCT_SYS},
            {'role': 'user', 'content': user}]
    raw = _call(msgs, model, timeout, temperature=0.1, max_tokens=2500)
    out = _clean_json(raw)
    if not isinstance(out, dict) or not isinstance(out.get('chapters'), list) \
            or not out['chapters']:
        raise RuntimeError('llm_not_json')
    return {'docTitle': str(out.get('docTitle') or '')[:60],
            'chapters': out['chapters']}


# ---------- 内容解析（cards Agent 的 parse 阶段） ----------
# 为什么要有这一步：「导入 → 直接出卡」会把目录、封面、参考文献一起出成卡。
# 用户要的是**先读一遍内容、剔掉没用的、给他过目**，确认后才出卡。
# 判定和结构精修一样只喂清单（标题+字数+开头）不塞全文 —— 同一个理由：
# 几千字的文档也不会爆上下文；而且「这章有没有用」看标题+开头基本够了。
PARSE_SYS = '''你是文档内容审查员。用户给的是学习资料的章节清单（编号 | 标题 | 字数 | 正文开头），判断每一章对备考学习有没有用。

该判 keep:false（剔除）的典型：
- 目录、页眉页脚、页码、封面、扉页、版权页；
- 前言、序言、致谢、免责声明这类非正文；
- 参考文献、引用列表、广告、过期通知；
- 与学习无关的大段闲文（编者闲聊、与考点无关的插科打诨）。

有知识点的正文一律 keep:true —— 拿不准的宁可保留，剔错了用户就再也出不了这章的卡。

输出严格 JSON：
{"chapters":[{"idx":0,"keep":false,"reason":"目录，非正文"}, ...]}

硬性要求：
- 每个下标 0..N-1 恰好出现一次：不许漏、不许重复、不许编造下标（违反作废）；
- keep 只用 true / false；剔除时 reason 给一句话（<=20字），保留时 reason 留空；
- 只输出 JSON，不要 markdown 代码块，不要解释。'''


def parse_content(items, doc_title='', model=None, timeout=300):
    """章节清单 → LLM 的有用/没用判定。

    items 同 refine_structure（{'title','level','chars','head'}，不带正文）。
    返回 {'chapters': [{'idx','keep','reason'}]}（覆盖全部下标）。
    校验在这里做：越界/重复的下标丢掉（模型幻觉），模型漏判的下标按
    keep=True 补齐 —— 漏判只是多出一张卡，误剔是丢内容，不对称。"""
    if AI_OFF:
        raise RuntimeError('ai_off')
    p = provider()
    model = model or (CLOUD_MODEL if p == 'cloud' else pick_model())
    if not model:
        raise RuntimeError('no_model')
    if not items:
        raise RuntimeError('too_short')

    lines = []
    for i, it in enumerate(items):
        lines.append('[%d] %s | %d字 | 开头：%s' % (
            i, (it.get('title') or '（无标题）')[:40],
            int(it.get('chars') or 0), (it.get('head') or '')[:60]))
    user = '文档标题：%s\n\n章节清单（共%d块）：\n%s' % (
        (doc_title or '（未知）')[:60], len(items), '\n'.join(lines))

    msgs = [{'role': 'system', 'content': PARSE_SYS},
            {'role': 'user', 'content': user}]
    raw = _call(msgs, model, timeout, temperature=0.1, max_tokens=2500)
    out = _clean_json(raw)
    if not isinstance(out, dict) or not isinstance(out.get('chapters'), list) \
            or not out['chapters']:
        raise RuntimeError('llm_not_json')

    n = len(items)
    got = {}
    for row in out['chapters']:
        if not isinstance(row, dict):
            continue
        idx = row.get('idx')
        if not isinstance(idx, int) or not (0 <= idx < n) or idx in got:
            continue                      # 越界 / 重复 = 模型幻觉，丢掉
        got[idx] = {'idx': idx,
                    'keep': bool(row.get('keep')),
                    'reason': str(row.get('reason') or '')[:40]}
    return {'chapters': [got.get(i, {'idx': i, 'keep': True, 'reason': ''})
                         for i in range(n)]}
