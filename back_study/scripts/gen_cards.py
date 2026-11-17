# -*- coding: utf-8 -*-
"""大纲批量造卡：按 data/catalog.js 的科目，让本地 Ollama 每个科目批量生成完整卡。

为什么不直接手写
  8 个科目、每科几十条，手写不现实；而卡片契约固定，让本地模型按 schema
  批量产出、人工只做抽查/删改，是「把库变多」最快的路（用户定的方向：大纲铺广度）。

复用（不自己拼 HTTP、不另起模型选择）
  - core/llm.py 的 status / pick_model / _call / _clean_json
  - data/catalog.js 的科目列表（加科目不用改这里）

产出
  data/gen_<subject>.js，格式严格对齐 db.load_source_cards() 的解析要求：
  `var CARDS_<SUBJECT> = [ ...strict JSON... ];`，数组无末尾逗号、键与字符串全双引号。

用法
  python gen_cards.py --all                 # 8 科全跑（慢，建议后台 nohup）
  python gen_cards.py --subject java --per 6
  python gen_cards.py --subject java --dry-run   # 不打文件，只打印模型吐了啥
"""
import argparse
import datetime
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))          # .../back_study/scripts
_BACK = os.path.dirname(_HERE)                              # .../back_study
_ROOT = os.path.dirname(_BACK)                             # .../study（项目根，data 的上级）
_CORE = os.path.join(_BACK, 'core')
for _p in (_CORE, _BACK):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import llm as _llm                                          # noqa: E402

# 与 core/db.py 保持一致：DATA_DIR = 项目根/data（data 是 back_study 的兄弟目录）
DATA_DIR = os.path.join(_ROOT, 'data')

# 每个科目的种子方向，用来引导覆盖（模型自己挑容易泛泛而谈）。
# 只列把握大的工作域；考研域给通用指令，让模型围绕核心考点发挥。
SEEDS = {
    'java': ['JVM 内存模型与运行时数据区', '垃圾回收算法与常见回收器', 'synchronized 与锁升级',
             'volatile 的可见性与有序性', '线程池原理与核心参数', 'HashMap 底层结构与扩容',
             'Spring IoC 容器与依赖注入', 'Spring AOP 与动态代理', '类加载机制与双亲委派',
             '反射与注解处理器'],
    'ai': ['Transformer 自注意力机制', '位置编码的作用', 'LoRA 低秩微调原理', 'RAG 检索增强生成',
           '向量库与 embedding', 'LangGraph 状态图编排', 'Agent 工具调用 Function Calling',
           '模型量化(INT8/FP16)', '少样本/思维链 Prompt', '训练与推理显存估算'],
    'cs': ['TCP 三次握手与四次挥手', 'HTTP 与 HTTPS 区别', '进程/线程/协程区别', '死锁必要条件与避免',
           '缓存击穿/穿透/雪崩', '一致性哈希', 'CAP 定理', 'B+树索引原理',
           '操作系统虚拟内存', '编译链接全过程'],
    'fe': ['浏览器渲染流程', 'Event Loop 与宏微任务', '闭包与作用域链', '原型链与继承',
           'Vue 响应式原理', 'Virtual DOM 与 diff', '跨域 CORS 原理', '防抖与节流',
           'Web 缓存策略', 'CSS 盒模型与 BFC'],
    'python': ['GIL 全局解释器锁与多线程', '垃圾回收与引用计数', '装饰器原理',
               '生成器与迭代器协议', '上下文管理器 with', '异步 asyncio 与协程',
               '可变与不可变对象的坑', 'MRO 多重继承顺序', '深浅拷贝区别',
               '虚拟环境与包管理'],
    'politics': ['马克思主义哲学基本原理', '毛泽东思想活的灵魂', '邓小平理论主要内容',
                 '习近平新时代中国特色社会主义思想', '近代史重要会议与转折', '思想道德与法治核心'],
    'english': ['考研高频长难句结构', '虚拟语气用法', '非谓语动词', '定语从句辨析',
                '阅读例证题解题', '写作图表描写句型'],
    'math': ['极限计算方法', '导数与微分中值定理', '定积分几何应用', '矩阵特征值与对角化',
             '概率随机变量分布', '线性方程组解的结构'],
    'major': ['数据结构复杂度分析', '动态规划状态设计', '图论最短路算法', '操作系统调度算法',
              '数据库范式与事务', '计算机网络分层模型'],
}


# ---------------------------------------------------------------------------
# 提示词
# ---------------------------------------------------------------------------
CARD_SYS = '''你是「原理卡片」知识库的卡片作者。按给定科目，产出若干张「原理卡」。
每张卡必须严格符合下面的 JSON 字段（不要多余字段，不要 markdown，不要解释）：

{
  "id": "java-xxx",                       // 英文短横线，全库唯一，必须带科目前缀
  "domain": "Java后端",                    // 科目展示名
  "category": "work",                      // 固定给的父分类 id
  "subject": "java",                       // 固定给的科目 id
  "topicPath": ["Java后端", "<子主题>"],    // 第 0 项固定为科目名
  "title": "一句问句式标题，说清这条在讲什么",
  "oneLine": "一句话结论（<=40字，说清它是什么、有什么用）",
  "analogy": "生活类比（<=40字，纯日常场景，不许出现技术词）",
  "why": "为什么需要它 / 解决了什么痛点（<=60字）",
  "mechanism": ["① 步骤一（因果链，每步<=35字）", "② 步骤二", "..."],   // 3-7 步，有序
  "diagram": {"kind":"pipeline","stages":["阶段1","阶段2"],"frames":[{"s":0,"note":"..."}]},  // 可选
  "interviewQ": ["面试官会怎么追问这条？", "..."],     // 2-3 条
  "keywords": ["术语1","术语2"],                        // 3-6 个
  "scene": ["真实系统里的具体用法或坑1（>=15字，禁止空话）", "..."],  // 至少 2 条，每条>=15字
  "tags": ["标签1","标签2"],
  "related": []                              // 留空即可
}

硬性要求（违反任意一条整张卡作废，会被程序丢弃）：
- 一张卡只讲一个知识点；mechanism 必须有先后顺序、讲清"它怎么跑"的因果链。
- analogy 必须是排队/图书馆/快递/做饭/开车这类生活场景，禁止数据库/缓存/服务器等技术词。
- scene 写真实工程场景或踩坑，禁止"广泛应用""非常重要"这类空话；不足 2 条作废。
- 只输出 JSON 数组，不要任何解释、不要 ``` 代码块标记。'''


# ---------------------------------------------------------------------------
# catalog
# ---------------------------------------------------------------------------
def load_catalog():
    """读 data/catalog.js 的分类树，摊平成 [(cat_id,cat_name,sub_id,sub_name), ...]。"""
    src = open(os.path.join(DATA_DIR, 'catalog.js'), encoding='utf-8').read()
    m = re.search(r'var\s+CATALOG\s*=\s*', src)
    if not m:
        raise RuntimeError('catalog.js 里找不到 var CATALOG')
    arr, _ = json.JSONDecoder().raw_decode(src, src.index('[', m.end()))
    out = []
    for cat in arr:
        for sub in (cat.get('subjects') or []):
            out.append((cat['id'], cat.get('name', cat['id']),
                        sub['id'], sub.get('name', sub['id'])))
    return out


# ---------------------------------------------------------------------------
# 生成 + 校验
# ---------------------------------------------------------------------------
def gen_batch(cat_id, cat_name, sub_id, sub_name, directions, n, model, temperature):
    """让模型一次吐 n 张卡（批量省开销）。返回解析后的 list（可能为空）。"""
    dirs = '；'.join(directions[:n]) or '该科目的核心原理考点'
    user = ('科目：%s（category=%s, subject=%s）。\n'
            '请产出 %d 张原理卡，优先覆盖这些方向：%s。\n'
            '严格遵守 schema，每张卡带科目前缀 id（如 %s-xxx），只输出 JSON 数组。'
            % (sub_name, cat_id, sub_id, n, dirs, sub_id))
    raw = _llm._call(
        [{'role': 'system', 'content': CARD_SYS},
         {'role': 'user', 'content': user}],
        model, timeout=600, temperature=temperature, max_tokens=6000)
    try:
        out = _llm._clean_json(raw)
    except Exception:
        return []
    if isinstance(out, dict):
        out = out.get('cards') or out.get('items') or []
    return out if isinstance(out, list) else []


def _valid_card(c, sub):
    """就地规整 + 必填校验。合格返回 True（c 已被修正），否则 False。"""
    if not isinstance(c, dict):
        return False
    # 必填：id / title / oneLine / mechanism(>=1) / keywords / scene(>=2 且每条>=10字)
    if not (c.get('id') and c.get('title') and c.get('oneLine')):
        return False
    mech = c.get('mechanism') or []
    if not isinstance(mech, list) or len([m for m in mech if str(m).strip()]) < 1:
        return False
    scene = c.get('scene') or []
    if not isinstance(scene, list) or len([s for s in scene if len(str(s).strip()) >= 10]) < 2:
        return False
    kw = c.get('keywords') or []
    if not isinstance(kw, list) or len(kw) < 1:
        return False

    # 规整：强制对齐 catalog，保证 category+subject 在目录里、domain 有展示名
    c['category'] = sub[0]
    c['subject'] = sub[2]
    c['domain'] = sub[3]
    # id 强制带科目前缀，避免与其它科目撞
    cid = str(c['id']).strip()
    if not cid.startswith(sub[2] + '-'):
        cid = '%s-%s' % (sub[2], re.sub(r'[^A-Za-z0-9]+', '-', cid).strip('-'))
    c['id'] = cid
    # topicPath 第 0 项固定科目名
    tp = c.get('topicPath') or []
    tp = [str(x) for x in tp if str(x).strip()]
    c['topicPath'] = [sub[3]] + tp[1:] if len(tp) > 1 else [sub[3], (c.get('title') or '')[:20]]
    # mechanism 加序号（和手写卡一致：①②③…）。先剥掉模型自带的前导序号/编号，
    # 否则会出现「① ① 堆存储…」这种重复。
    ORD = '①②③④⑤⑥⑦⑧⑨⑩'

    def _strip_ord(s):
        s = str(s).strip()
        s = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', s)
        s = re.sub(r'^[0-9]+[.、)）]\s*', '', s)
        s = re.sub(r'^（[0-9]+）\s*', '', s)
        return s.strip()

    c['mechanism'] = [(ORD[k] + ' ' + _strip_ord(s)) if k < len(ORD)
                      else ('%d. %s' % (k + 1, _strip_ord(s)))
                      for k, s in enumerate(mech) if str(s).strip()]
    c['keywords'] = [str(x).strip() for x in kw if str(x).strip()][:8]
    c['scene'] = [str(s).strip() for s in scene if str(s).strip()][:6]
    c['interviewQ'] = [str(x).strip() for x in (c.get('interviewQ') or []) if str(x).strip()][:4]
    c['tags'] = [str(x).strip() for x in (c.get('tags') or []) if str(x).strip()][:6]
    c['related'] = []
    # diagram 只保留合法 pipeline（其余丢弃，不算错）
    d = c.get('diagram') or {}
    if not (isinstance(d, dict) and d.get('kind') == 'pipeline' and d.get('stages')):
        c.pop('diagram', None)
    return True


def generate_subject(sub, per, batch, model, temperature, dry_run=False):
    cat_id, cat_name, sub_id, sub_name = sub
    seeds = SEEDS.get(sub_id, [])
    cards, seen = [], set()
    tries = 0
    while len(cards) < per and tries < (per // batch + 3):
        tries += 1
        n = min(batch, per - len(cards))
        raw = gen_batch(cat_id, cat_name, sub_id, sub_name, seeds, n, model, temperature)
        for c in raw:
            if not _valid_card(c, sub):
                continue
            if c['id'] in seen:
                continue
            seen.add(c['id'])
            cards.append(c)
        if dry_run:
            break
    return cards


# ---------------------------------------------------------------------------
# 落盘
# ---------------------------------------------------------------------------
def write_file(sub_id, cards):
    fname = 'gen_%s.js' % sub_id
    fqname = 'CARDS_%s' % sub_id.upper()
    path = os.path.join(DATA_DIR, fname)
    stamp = datetime.date.today().isoformat()
    header = ('// 自动生成于 %s by scripts/gen_cards.py（大纲批量造卡）。\n'
              '// 机器产出，人工复核后可保留/删改；此文件由 git 管理，属「内容」不是「状态」。\n'
              % stamp)
    body = 'var %s = %s;\n' % (
        fqname, json.dumps(cards, ensure_ascii=False, indent=2))
    tail = ('\nif (typeof module !== "undefined" && module.exports) {'
            ' module.exports = %s; }\n' % fqname)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(header + body + tail)
    return path


def verify(path):
    """写完后用与 db.load_source_cards() 完全相同的解析逻辑独立校验：
    正则找 `var CARDS_X =`，从首个 `[` 起 raw_decode 严格 JSON。
    不 import db（db 会拽进 security→PyJWT，与数据加载无关，纯属浪费依赖）。"""
    try:
        src = open(path, encoding='utf-8').read()
        m = re.search(r'var\s+(CARDS_[A-Za-z0-9_]+)\s*=', src)
        if not m:
            return -1
        idx = src.find('[', m.end())
        arr, _ = json.JSONDecoder().raw_decode(src, idx)
        return len(arr)
    except Exception:
        return -1


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true', help='跑 catalog 全部科目')
    ap.add_argument('--subject', help='只跑某科目 id（如 java）')
    ap.add_argument('--per', type=int, default=6, help='每科生成多少张（默认 6）')
    ap.add_argument('--batch', type=int, default=3, help='每次让模型吐几张（默认 3）')
    ap.add_argument('--temperature', type=float, default=0.6, help='生成多样性')
    ap.add_argument('--model', help='指定模型，默认走 llm.pick_model()')
    ap.add_argument('--dry-run', action='store_true', help='只打印不落盘')
    args = ap.parse_args()

    st = _llm.status()
    if not st.get('ok'):
        print('[gen_cards] 模型不可用：%s' % (st.get('msg') or ''))
        return 1
    model = args.model or st.get('model')
    print('[gen_cards] 模型=%s  模式=%s' % (model, 'dry-run' if args.dry_run else '写文件'))

    cats = load_catalog()
    if args.subject:
        cats = [c for c in cats if c[2] == args.subject]
        if not cats:
            print('[gen_cards] catalog 里没有科目: %s' % args.subject)
            return 1
    elif not args.all:
        print('[gen_cards] 既不 --all 也不 --subject，默认只跑一个示例科目 java。')
        cats = [c for c in cats if c[2] == 'java'] or cats[:1]

    total = 0
    for sub in cats:
        cat_id, cat_name, sub_id, sub_name = sub
        print('\n=== %s / %s (%s) ===' % (cat_name, sub_name, sub_id))
        cards = generate_subject(sub, args.per, args.batch, model, args.temperature, args.dry_run)
        if args.dry_run:
            print(json.dumps(cards, ensure_ascii=False, indent=2)[:2000])
            total += len(cards)
            continue
        if not cards:
            print('  0 张合格，跳过写文件')
            continue
        path = write_file(sub_id, cards)
        n = verify(path)
        print('  写出 %d 张 -> %s （db 加载确认 %s）' % (len(cards), path, n))
        total += len(cards)
    print('\n[gen_cards] 共 %d 张（含不合格被丢弃的）。' % total)
    return 0


if __name__ == '__main__':
    sys.exit(main())
