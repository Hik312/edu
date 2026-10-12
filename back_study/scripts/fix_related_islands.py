"""补语义孤岛的 related —— 让图谱里点得到「相关内容」。

背景：图谱的 belong 边（卡片→主题→科目→领域）来自 topicPath，任何卡都有。
     但**语义边**（prereq/extends/compare）只来自卡片自己写的 `related[]`。
     所以一张卡如果 related 为空，在图谱上就只能靠目录树位置找到，
     点不出「前置是什么 / 谁扩展了它 / 和谁容易混」。

实测（2026-10-09）：全库里有 12 张 related 为空，其中：
  - 4 张是成对的孪生卡（同一个问题的两种问法），互连即可
  - 其余挂到明确的主题邻居上
这不是「美化」，是让 Pagerank / personalized_pagerank 有信号可用：
孤岛节点在图算法里权重只取决于度数，推荐永远推不出来。

★ 卡有两个来源，本脚本必须分别处理（第一版只改文件，结果这两张被漏掉）：
  1. 内置卡 → data/*.js（文件级读写）
  2. 自定义卡 → MySQL/cards 表（走 db.load_custom / db.save_custom）
     `ag-*` 那批是走 Agent 导入工作流生成的，只在存储层，data/ 里没有文件。

幂等：已存在的 id 不重复添加；重跑是 0 改动。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, 'data')
sys.path.insert(0, os.path.join(ROOT, 'back_study'))
sys.path.insert(0, os.path.join(ROOT, 'back_study', 'core'))

SKIP = ('catalog.js', 'roles.js', 'directions.js')

# card_id -> [(target_id, kind, note), ...]
# kind 用图谱已有的三种：prereq（前置）/ extends（扩展）/ compare（易混）
LINKS = {
    # ---- 前端：4 张原有卡，与后补的 fe 卡同主题但没连 ----
    'fe-browser-rendering': [
        ('fe-reflow-repaint', 'extends', '渲染流程走到重排重绘那一步就会分叉'),
        ('fe-vdom-diff', 'compare', '两者都在回答「DOM 什么时候被改」'),
        ('fe-cors', 'compare', '同属浏览器机制，一个管渲染一个管跨域'),
    ],
    'fe-event-loop': [
        ('fe-promise', 'extends', '微任务队列是宏微任务模型的一部分'),
        ('fe-long-task', 'compare', '都关系到主线程什么时候被占住'),
    ],
    # 孪生卡：同一知识点的两种问法
    'fe-closure-scope': [
        ('fe-closure-scope-chain', 'compare', '同一知识点的两种问法，建议连着看'),
        ('fe-closure-memory-leak', 'extends', '作用域链的代价是闭包会把外层变量留住'),
    ],
    'fe-closure-scope-chain': [
        ('fe-closure-scope', 'compare', '同一知识点的两种问法，建议连着看'),
        ('fe-prototype', 'compare', '作用域链与原型链都是「查找链」，最容易混的一对'),
    ],
    # ---- cs：网络旧卡 ----
    'cs-netq13': [
        ('fe-storage-cookie', 'extends', 'HTTP 无状态，所以要靠 Cookie/Token 记状态'),
        ('cs-http-vs-https', 'extends', 'Cookie 的 Secure 属性依赖 HTTPS'),
    ],
    'cs-netq19': [
        ('sse-websocket', 'compare', '两个都解决「服务端主动推」，选型常被问'),
        ('cs-netq20', 'extends', '与轮询/长轮询的对比是同一考题'),
    ],
    # ---- java ----
    'java-basicq29': [
        ('java-generics-and-wildcards', 'extends',
         '可变长参数底层是数组，与泛型擦除配合时容易踩坑'),
        ('java-why-there-only-value-passing-in-java', 'extends',
         '参数传递方式决定可变长参数的行为'),
    ],
    'java-cold-hot-separation': [
        ('java-rw-split-sharding', 'extends', '都是「按访问量把数据分开」的思路'),
        ('java-deep-pagination', 'compare', '都出现在大表访问优化的同一场景里'),
    ],
    'java-jvm-memory-model': [
        ('java-jmm', 'extends', 'JMM 是内存模型的规范，这张讲的是它的结构'),
        ('java-memory-area', 'prereq', '先分清运行时数据区，才谈并发可见性'),
    ],
    'java-jvm-memory': [
        ('java-memory-area', 'extends', '同一块知识的详版'),
        ('java-jvm-memory-model', 'compare',
         '「内存区域」与「内存模型」是两个概念，最常被混'),
    ],
    # ---- Agent 导入的 Spring 两张（只在存储层）----
    'ag-1d03b562': [
        ('ag-37f0f429', 'extends', 'Core+Beans 正是 IoC/DI 的实现载体'),
    ],
    'ag-37f0f429': [
        ('ag-1d03b562', 'prereq', '先理解 Core/Beans 模块，再看 IoC/DI 特性'),
    ],
}


def read_cards(path):
    """从 js 文件里提取卡片数组。返回 (prefix, cards, suffix) 以便原样写回。

    ★ 正则必须用宽松的 `(\\[.*\\])\\s*;`：
      写成 `(\\[\\s*\\{.*\\}\\s*\\])` 会要求数组首字符后紧跟 `{`，
      而实际文件是 `var X =\n[\n  {...`，一个文件都匹配不到，
      **结果是 0 张却不报错** —— 这个坑踩过一次。
    """
    src = open(path, encoding='utf-8').read()
    m = re.search(r'(\[.*\])\s*;', src, re.S)
    if not m:
        return None
    return src[:m.start(1)], json.loads(m.group(1)), src[m.end(1):]


def add_links(card, extras):
    """往一张卡的 related 追加边，已连过的 id 跳过。返回新增条数。"""
    have = {r.get('id') for r in (card.get('related') or [])}
    n = 0
    for tid, kind, note in extras:
        if tid in have:
            continue
        card.setdefault('related', []).append({'id': tid, 'kind': kind, 'note': note})
        have.add(tid)
        n += 1
    return n


def main():
    dry = '--dry-run' in sys.argv
    if not os.path.isdir(DATA):
        raise SystemExit('数据目录不存在：%s' % DATA)

    import db
    every = db.all_cards()
    all_ids = {c.get('id') for c in every}
    custom_ids = {c.get('id') for c in db.load_custom()}

    # ---- 护栏：所有引用必须存在，否则宁可崩 ----
    bad = set()
    for cid, links in LINKS.items():
        if cid not in all_ids:
            raise SystemExit('卡片不存在：%s' % cid)
        for tid, _, _ in links:
            if tid not in all_ids:
                bad.add((cid, tid))
    if bad:
        raise SystemExit('目标卡不存在（悬空引用）：%s' % sorted(bad))

    # 反向表：给 X 补边 L 的同时，X 的卡片也要挂回 L，
    # 否则补了「A→B」却没补「B→A」，B 就成了新的孤岛。
    reverse = {}
    for cid, links in LINKS.items():
        for tid, kind, note in links:
            # 反向用 compare：语义方向（谁扩展谁）未知，保守表述
            reverse.setdefault(tid, []).append((cid, 'compare', '相关：%s' % cid))

    # ---- 1) 内置卡：data/*.js ----
    files = [f for f in sorted(os.listdir(DATA))
             if f.endswith('.js') and f not in SKIP]
    touched = {}
    for name in files:
        got = read_cards(os.path.join(DATA, name))
        if not got:
            continue
        pre, cards, suf = got
        dirty = False
        for c in cards:
            cid = c.get('id')
            extras = list(LINKS.get(cid) or []) + list(reverse.get(cid) or [])
            if not extras:
                continue
            n = add_links(c, extras)
            if n:
                touched[name] = pre, cards, suf
                dirty = True
                print('  [文件] %-30s +%d 条| %s' % (cid, n, c.get('title', '')[:24]))
        if dirty and not dry:
            pre, cards, suf = touched[name]
            open(os.path.join(DATA, name), 'w', encoding='utf-8').write(
                pre + json.dumps(cards, ensure_ascii=False, indent=2) + suf)

    # ---- 2) 自定义卡：MySQL/cards 表 ----
    custom = db.load_custom()
    custom_dirty = False
    for c in custom:
        cid = c.get('id')
        if cid not in custom_ids:      # 保险：只改自定义表里的
            continue
        extras = list(LINKS.get(cid) or []) + list(reverse.get(cid) or [])
        if not extras:
            continue
        n = add_links(c, extras)
        if n:
            custom_dirty = True
            print('  [自定义] %-28s +%d 条 | %s' % (cid, n, c.get('title', '')[:24]))
    if custom_dirty and not dry:
        db.save_custom(custom)

    print('%s内置卡改动 %d 个文件，自定义卡改动 %s' % (
        '[dry-run] ' if dry else '', len(touched), '是' if custom_dirty else '否'))


if __name__ == '__main__':
    main()