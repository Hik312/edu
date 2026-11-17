# -*- coding: utf-8 -*-
"""整理三份面试卡素材清单 → manifest_{agent,redis,java}.json

素材来源（只读，不动）：
  agent : C:\\...\\interview_src\\Agent-Interview-100   （100题仓库，已克隆）
  redis : 小林 coding《Redis 常见面试题》页（opencode tool-output 存档）+ JavaGuide 4 篇单主题
  java  : JavaGuide docs\\java 下 43 篇单主题文章

查重：清单 id 与 data/*.js 里所有真卡片（含 mechanism 字段的文件）逐一对撞，
      冲突自动加后缀并打印 —— 保证 check.js 的「cards 数量一致」不出红。
"""
import glob
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC = r'C:\Users\wangh\AppData\Local\Temp\opencode\interview_src'
XLS_PAGE = r'C:\Users\wangh\.local\share\opencode\tool-output\tool_0f81d3c66001K6Yz3j2PoGWc54'
OUT = os.path.join(ROOT, 'back_study', 'scripts', '_interview')

# ---------------------------------------------------------------- 基础工具
def existing_card_ids():
    ids = set()
    for f in glob.glob(os.path.join(ROOT, 'data', '*.js')):
        txt = open(f, encoding='utf-8').read()
        if '"mechanism"' not in txt:          # 只有真卡片文件才有 mechanism
            continue
        ids.update(re.findall(r'"id"\s*:\s*"([^"]+)"', txt))
    return ids


def read_md(path):
    t = open(path, encoding='utf-8').read()
    return re.sub(r'^---\n.*?\n---\n', '', t, flags=re.S)   # YAML front matter


def fm_title(t):
    """JavaGuide 文件标题常在 front matter 里（h1 未必有）。"""
    m = re.match(r'---\n(.*?)\n---\n', t, re.S)
    if not m:
        return ''
    m2 = re.search(r'^title:\s*(.+)$', m.group(1), re.M)
    if not m2:
        return ''
    return m2.group(1).strip().strip('"\'')


def file_hint(path, fallback):
    full = open(path, encoding='utf-8').read()
    return first_heading(full) or fm_title(full) or fallback


def first_heading(t):
    m = re.search(r'^#\s+(.+)$', t, re.M)
    if not m:
        return ''
    return re.sub(r'[*\[\]()`]', '', m.group(1)).strip()


def clean_body(t):
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', t)              # 图片
    t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', t)           # 链接留文字
    t = re.sub(r'<[^>]+>', '', t)                            # html/vue 标签
    keep = []
    for line in t.split('\n'):
        s = line.strip()
        if s in ('TIP', '<TIP>') or s.startswith('想深入了解') \
           or s.startswith('想更详细了解') or '可以看这篇' in s \
           or s.startswith('![]'):
            continue
        keep.append(line)
    t = '\n'.join(keep)
    return re.sub(r'\n{3,}', '\n\n', t).strip()


def norm(s):
    return re.sub(r'\s+', '', s or '').rstrip('？?')


def take_id(cid, taken):
    if cid not in taken:
        taken.add(cid)
        return cid
    n = 2
    while '%s-%d' % (cid, n) in taken:
        n += 1
    cid = '%s-%d' % (cid, n)
    taken.add(cid)
    print('  !! id 冲突已加后缀：%s' % cid)
    return cid


def entry(cid, subject, domain, topic, tags, hint, path):
    return {'id': cid, 'subject': subject, 'domain': domain,
            'topicPath': [domain, topic], 'tags': tags,
            'title_hint': hint, 'src_path': path}


# ---------------------------------------------------------------- agent
AG_MOD_CN = {
    '01-agent-architecture': 'Agent 架构',
    '02-rag': 'RAG 检索增强',
    '03-tool-use': '工具调用',
    '04-multi-agent': '多智能体',
    '05-memory-and-state': '记忆与状态',
    '06-planning-and-reasoning': '规划与推理',
    '07-prompt-engineering': '提示工程',
    '08-evaluation': '智能体评测',
    '09-safety-and-alignment': '安全与对齐',
    '10-production-and-deployment': '生产部署',
    '11-frameworks': 'Agent 框架',
}
# 与库内已有卡内容近似（ai-agent/ai-rag/ai-toolcall/ai-mcp/ai-multiagent/ai-memory/
# ai-eval/ai-langgraph + 我们上一批 ai-reflection/ai-a2a/ai-context-engineering）
AG_SKIP = {6, 9, 11, 21, 27, 31, 40, 69, 97, 101, 102}


def build_agent(taken):
    items = []
    base = os.path.join(SRC, 'Agent-Interview-100')
    for path in sorted(glob.glob(os.path.join(base, '*', '*.md'))):
        name = os.path.basename(path)
        m = re.match(r'(\d+)-(.+)\.md$', name)
        if not m:
            continue
        num, slug = int(m.group(1)), m.group(2)
        if num in AG_SKIP:
            continue
        mod = os.path.basename(os.path.dirname(path))
        topic = AG_MOD_CN.get(mod)
        if not topic:
            continue
        raw = read_md(path)
        body = clean_body(raw)
        if len(re.sub(r'\s+', '', body)) < 600:
            print('  跳过（素材过短）: %s' % name)
            continue
        cid = take_id('ai-' + slug, taken)
        items.append(entry(cid, 'ai', 'AI工程', topic, ['Agent', topic],
                           first_heading(raw) or slug, path))
    return items


# ---------------------------------------------------------------- redis
SEC_TOPIC = {
    '认识Redis': 'Redis 入门',
    'Redis数据结构': 'Redis 数据结构',
    'Redis线程模型': 'Redis 线程模型',
    'Redis持久化': 'Redis 持久化',
    'Redis集群': 'Redis 高可用',
    'Redis过期删除与内存淘汰': 'Redis 过期与淘汰',
    'Redis缓存设计': 'Redis 缓存设计',
    'Redis实战': 'Redis 实战',
}
Q_SLUG = {
    '什么是Redis？': 'what-is-redis',
    'Redis和Memcached有什么区别？': 'redis-vs-memcached',
    '为什么用Redis作为MySQL的缓存？': 'why-redis-cache-for-mysql',
    'Redis数据类型以及使用场景分别是什么？': 'redis-data-types-scenarios',
    '五种常见的Redis数据类型是怎么实现？': 'redis-data-types-internals',
    'Redis是单线程吗？': 'is-redis-single-thread',
    'Redis单线程模式是怎样的？': 'redis-single-thread-model',
    'Redis采用单线程为什么还这么快？': 'redis-single-thread-fast',
    'Redis6.0之前为什么使用单线程？': 'redis-single-thread-before-6',
    'Redis6.0之后为什么引入了多线程？': 'redis-multithread-after-6',
    'Redis如何实现数据不丢失？': 'redis-persistence-overview',
    'AOF日志是如何实现的？': 'redis-aof-internals',
    'RDB快照是如何实现的呢？': 'redis-rdb-internals',
    '为什么会有混合持久化？': 'redis-hybrid-persistence',
    'Redis如何实现服务高可用？': 'redis-high-availability',
    '集群脑裂导致数据丢失怎么办？': 'redis-cluster-split-brain',
    'Redis使用的过期删除策略是什么？': 'redis-expire-delete-strategy',
    'Redis持久化时，对过期键会如何处理的？': 'redis-expire-keys-persistence',
    'Redis主从模式中，对过期键会如何处理的？': 'redis-expire-keys-replication',
    'Redis内存满了，会发生什么？': 'redis-maxmemory',
    'Redis内存淘汰策略有哪些？': 'redis-eviction-strategies',
    'LRU算法和LFU算法有什么区别？': 'redis-lru-vs-lfu',
    '如何避免缓存雪崩、缓存击穿、缓存穿透？': 'redis-cache-three-problems',
    '如何设计一个缓存策略，可以动态缓存热点数据呢？': 'redis-dynamic-hot-cache',
    '说说常见的缓存更新策略？': 'redis-cache-update-strategies',
    '如何保证缓存和数据库数据的一致性？': 'redis-cache-db-consistency',
    'Redis如何实现延迟队列？': 'redis-delayed-queue',
    'Redis的大key如何处理？': 'redis-big-key',
    'Redis管道有什么用？': 'redis-pipeline',
    'Redis事务支持回滚吗？': 'redis-transaction-rollback',
    '如何用Redis实现分布式锁的？': 'redis-distributed-lock',
}
# JavaGuide 单主题补充（小林页没覆盖/被判定素材过短的角度）
RG_EXTRAS = [
    ('redis-skiplist.md', 'redis-skiplist', 'Redis 数据结构',
     'Redis 为什么用跳表而不用红黑树做 ZSet？'),
    ('redis-stream-mq.md', 'redis-stream-mq', 'Redis 实战',
     'Redis Stream 怎么当消息队列用？'),
    ('redis-memory-fragmentation.md', 'redis-memory-fragmentation', 'Redis 运维',
     'Redis 内存碎片率怎么看、怎么处理？'),
    ('redis-common-blocking-problems-summary.md', 'redis-blocking-problems', 'Redis 实战',
     'Redis 常见的阻塞问题有哪些？'),
    ('redis-persistence.md', 'redis-persistence', 'Redis 持久化',
     'Redis 有哪几种持久化方式？RDB 和 AOF 怎么选？'),
    ('redis-delayed-task.md', 'redis-delayed-task', 'Redis 实战',
     'Redis 怎么实现延迟队列？'),
]
# 小林专文（整页一题，PowerShell 已下载为 HTML，构建时抽正文）
XL_PAGES = [
    ('consistency', 'java-redis-cache-db-consistency', 'Redis 缓存设计',
     '如何保证缓存和数据库数据的一致性？'),
    ('sentinel', 'java-redis-sentinel', 'Redis 高可用',
     '哨兵（Sentinel）是怎么实现主从故障转移的？'),
    ('master_slave', 'java-redis-master-slave-replication', 'Redis 高可用',
     '主从复制是怎么实现的？'),
    ('cluster', 'java-redis-cluster', 'Redis 高可用',
     'Redis Cluster 集群是怎么分片的？'),
]


def xiaolin_text(path):
    """小林页（VuePress）：取 content__default 到 page-edit 之间的正文。"""
    t = open(path, encoding='utf-8').read()
    i = t.find('content__default')
    j = t.find('class="page-edit"', i)
    seg = t[i:j] if i >= 0 and j > i else t
    seg = re.sub(r'(?s)<a[^>]*class="header-anchor"[^>]*></a>', '', seg)
    seg = re.sub(r'(?s)</(p|div|li|h[1-6]|tr|pre|blockquote|ul|ol)>', '\n', seg)
    seg = re.sub(r'(?s)<li[^>]*>', '- ', seg)
    seg = re.sub(r'(?s)<img[^>]*>', '', seg)
    seg = re.sub(r'(?s)<[^>]+>', '', seg)
    seg = re.sub(r'&nbsp;', ' ', seg)
    seg = re.sub(r'&lt;', '<', seg)
    seg = re.sub(r'&gt;', '>', seg)
    seg = re.sub(r'&amp;', '&', seg)
    return seg


def build_redis(taken):
    items = []
    txt = open(XLS_PAGE, encoding='utf-8').read()
    m = re.search(r'^# \[#\]\([^)]*\) Redis 常见面试题', txt, re.M)
    if not m:
        raise SystemExit('小林页面正文没找到（存档格式变了？）')
    body = txt[m.start():]
    q_idx = 0
    for sec in re.split(r'(?m)^## ', body)[1:]:
        head = re.sub(r'^\[#\]\([^)]*\)\s*', '', sec.split('\n', 1)[0]).strip()
        topic = SEC_TOPIC.get(norm(head))
        if not topic:
            print('  未知节，跳过: %s' % head)
            continue
        for part in re.split(r'(?m)^### ', sec)[1:]:
            q = re.sub(r'^\[#\]\([^)]*\)\s*', '', part.split('\n', 1)[0]).strip()
            content = clean_body(part.split('\n', 1)[1] if '\n' in part else '')
            if len(re.sub(r'\s+', '', content)) < 400:
                print('  跳过（素材过短）: %s' % q)
                continue
            q_idx += 1
            slug = Q_SLUG.get(norm(q) + '？') or Q_SLUG.get(norm(q))
            if not slug:
                slug = 'redis-q%02d' % q_idx
                print('  !! 题目缺 slug 映射，已用序号: %s' % q)
            cid = take_id('java-' + slug, taken)
            items.append(entry(cid, 'java', 'Java后端', topic,
                               ['Redis', topic], q, XLS_PAGE))
            items[-1]['src_inline'] = content        # 小林页是一页多题，正文内联
    for fname, slug, topic, hint in RG_EXTRAS:
        path = os.path.join(SRC, 'JavaGuide', 'docs', 'database', 'redis', fname)
        body_txt = clean_body(read_md(path))
        if len(re.sub(r'\s+', '', body_txt)) < 600:
            print('  跳过（素材过短）: %s' % fname)
            continue
        cid = take_id('java-' + slug, taken)
        items.append(entry(cid, 'java', 'Java后端', topic, ['Redis', topic],
                           hint, path))
    for name, slug, topic, hint in XL_PAGES:
        html_path = os.path.join(SRC, 'xiaolin', '%s.html' % name)
        if not os.path.exists(html_path):
            print('  !! 小林页不存在: %s' % html_path)
            continue
        body_txt = clean_body(xiaolin_text(html_path))
        if len(re.sub(r'\s+', '', body_txt)) < 800:
            print('  跳过（素材过短）: xiaolin/%s' % name)
            continue
        txt_path = os.path.join(SRC, 'xiaolin', '%s.clean.txt' % name)
        with open(txt_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(body_txt)
        cid = take_id(slug, taken)
        items.append(entry(cid, 'java', 'Java后端', topic, ['Redis', topic],
                           hint, txt_path))
    return items


# ---------------------------------------------------------------- java
JAVA_FILES = [
    ('basis\\bigdecimal.md', 'Java 基础'),
    ('basis\\generics-and-wildcards.md', 'Java 基础'),
    ('basis\\proxy.md', 'Java 基础'),
    ('basis\\reflection.md', 'Java 基础'),
    ('basis\\serialization.md', 'Java 基础'),
    ('basis\\spi.md', 'Java 基础'),
    ('basis\\syntactic-sugar.md', 'Java 基础'),
    ('basis\\why-there-only-value-passing-in-java.md', 'Java 基础'),
    ('collection\\arraylist-source-code.md', '集合'),
    ('collection\\concurrent-hash-map-source-code.md', '集合'),
    ('collection\\copyonwritearraylist-source-code.md', '集合'),
    ('collection\\delayqueue-source-code.md', '集合'),
    ('collection\\hashmap-source-code.md', '集合'),
    ('collection\\java-collection-precautions-for-use.md', '集合'),
    ('collection\\linkedhashmap-source-code.md', '集合'),
    ('collection\\linkedlist-source-code.md', '集合'),
    ('collection\\priorityqueue-source-code.md', '集合'),
    ('collection\\arrayblockingqueue-source-code.md', '集合'),
    ('concurrent\\aqs.md', '并发'),
    ('concurrent\\atomic-classes.md', '并发'),
    ('concurrent\\cas.md', '并发'),
    ('concurrent\\completablefuture-intro.md', '并发'),
    ('concurrent\\java-concurrent-collections.md', '并发'),
    ('concurrent\\java-lock.md', '并发'),
    ('concurrent\\java-thread-pool-best-practices.md', '并发'),
    ('concurrent\\java-thread-pool-summary.md', '并发'),
    ('concurrent\\jmm.md', '并发'),
    ('concurrent\\optimistic-lock-and-pessimistic-lock.md', '并发'),
    ('concurrent\\reentrantlock.md', '并发'),
    ('concurrent\\threadlocal.md', '并发'),
    ('io\\io-basis.md', 'Java IO'),
    ('io\\io-design-patterns.md', 'Java IO'),
    ('io\\io-model.md', 'Java IO'),
    ('io\\nio-basis.md', 'Java IO'),
    ('jvm\\class-file-structure.md', 'JVM'),
    ('jvm\\class-loading-process.md', 'JVM'),
    ('jvm\\classloader.md', 'JVM'),
    ('jvm\\jdk-monitoring-and-troubleshooting-tools.md', 'JVM'),
    ('jvm\\jvm-garbage-collection.md', 'JVM'),
    ('jvm\\jvm-intro.md', 'JVM'),
    ('jvm\\jvm-parameters-intro.md', 'JVM'),
    ('jvm\\memory-area.md', 'JVM'),
    ('new-features\\java8-common-new-features.md', 'Java 新特性'),
]


def build_java(taken):
    items = []
    base = os.path.join(SRC, 'JavaGuide', 'docs', 'java')
    for rel, topic in JAVA_FILES:
        path = os.path.join(base, rel)
        if not os.path.exists(path):
            print('  !! 素材不存在: %s' % rel)
            continue
        raw = read_md(path)
        body = clean_body(raw)
        if len(re.sub(r'\s+', '', body)) < 600:
            print('  跳过（素材过短）: %s' % rel)
            continue
        stem = os.path.splitext(os.path.basename(rel))[0]
        slug = re.sub(r'[^a-z0-9]+', '-', stem.lower()).strip('-')
        cid = take_id('java-' + slug, taken)
        items.append(entry(cid, 'java', 'Java后端', topic, ['Java', topic],
                           file_hint(path, stem), path))
    return items


# ---------------------------------------------------------------- 增量扩容
# 三份 questions 合集按题拆分（### 为题界，序号 = 过滤后顺序，人工白名单剔除
# 与库内已有卡重复的和素材 <400 字的）
Q_PICKS = [
    # java/basic-questions-01：剔 Java和C++(8) 标识符(10) 超long(21) 静态变量(23)
    # 静态调用(26) 浮点精度(19,20 与 java-bigdecimal 卡重)
    (r'java\basis\java-basic-questions-01.md', 'java', 'Java 基础',
     'basicq', [1, 2, 3, 4, 5, 6, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 22,
                24, 25, 27, 28, 29]),
    # collection-01：只留素材够长的 9 题
    (r'java\collection\java-collection-questions-01.md', 'java', '集合',
     'collq', [3, 6, 10, 13, 15, 16, 19, 21, 24]),
    # redis-01：剔与小林 31 题重复的（什么是Redis/为什么快/Memcached对比/单线程/
    # 过期删除/淘汰/跳表/分布式锁/延时任务 等 22 题）
    (r'database\redis\redis-questions-01.md', 'java', 'Redis 面试',
     'redisq', [3, 5, 8, 9, 15, 16, 22, 23, 25, 27, 29, 30]),
    # Agent 项目面试：剔 30秒版本(1,短) 模型怎么选(7,短) 网关(8,短) 退出边界(12,短)
    # Workflow对比(3,与 ai-workflow-vs-agent 重) 框架vs自研(9,与 ai-framework-vs-custom 重)
    (r'ai\interview-questions\agent-project-interview-guide.md', 'ai', 'Agent 项目面试',
     'projq', [2, 4, 5, 6, 10, 11, 13, 14, 15]),
    # ---- 第二批（mysql / 操作系统 / 计算机网络）----
    # mysql-questions-01 50 题：剔索引(18-27，与 mysql-index/-invalidation 单篇重)
    # 和事务隔离(28-35、41，与 transaction-isolation-level 单篇重)、SQL优化(45-50，
    # 与 sql-optimization 等单篇重)，留存储引擎/行锁/存储细节
    (r'database\mysql\mysql-questions-01.md', 'java', 'MySQL',
     'mysqlq', [14, 16, 36, 38, 39, 40, 42, 43, 44]),
    # os-01 22 题：剔进程线程(6,7 与 process-and-thread 单篇重)、死锁(19-22 与
    # dead-lock 单篇重)，留用户态/线程同步/状态/IPC/调度
    (r'cs-basics\operating-system\operating-system-basic-questions-01.md', 'cs', '操作系统',
     'osq1', [4, 5, 8, 9, 12, 13, 15, 16, 18]),
    # os-02 29 题：剔虚拟内存/分页分段(4-7,11,12,14 与 memory/virtual 单篇重)、
    # IO多路复用与零拷贝(16-19 与 io-multiplexing/zero-copy 单篇重)，留内存实测
    # + 文件系统全组
    (r'cs-basics\operating-system\operating-system-basic-questions-02.md', 'cs', '操作系统',
     'osq2', [2, 3, 8, 9, 10, 13, 15, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]),
    # other-network-questions 28 题：剔分层/URL全流程/HTTP对比HTTPS/1.0-1.1/
    # Ping/DNS基础（与单篇重），留 1.1↔2.0↔3.0、状态保持、WebSocket、DNS劫持
    (r'cs-basics\network\other-network-questions.md', 'cs', '计算机网络',
     'netq', [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 28]),
]
# docs/ai 单篇（挑与已有 93 张 agent 卡不重复的角度）
AI_FILES = [
    (r'ai\agent\skills.md', 'ai-agent-skills', 'Agent 架构',
     'Agent Skills 是什么？和 MCP 工具怎么配合？'),
    (r'ai\agent\workflow-graph-loop.md', 'ai-workflow-graph-loop', 'Agent 架构',
     'Workflow、Graph 和 Loop 三种执行模型怎么选？'),
    (r'ai\llm-basis\llm-api-engineering.md', 'ai-llm-api-engineering', 'LLM 基础',
     'LLM API 调用工程：流式、重试与限流怎么做？'),
    (r'ai\llm-basis\llm-operation-mechanism.md', 'ai-llm-operation-mechanism', 'LLM 基础',
     'LLM 从输入到输出的运行机制是什么？'),
    (r'ai\rag\graphrag.md', 'ai-graphrag', 'RAG 检索增强',
     'GraphRAG 是什么？什么时候比普通 RAG 好？'),
    (r'ai\rag\rag-knowledge-update.md', 'ai-rag-knowledge-update', 'RAG 检索增强',
     'RAG 知识库怎么持续更新？'),
    (r'ai\rag\rag-optimization.md', 'ai-rag-optimization', 'RAG 检索增强',
     'RAG 效果不好，从哪些环节优化？'),
    (r'ai\system-design\ai-application-architecture.md', 'ai-application-architecture',
     'AI 系统设计', '一个生产级 AI 应用的整体架构长什么样？'),
    (r'ai\system-design\llm-gateway.md', 'ai-llm-gateway', 'AI 系统设计',
     'LLM 网关解决什么问题？核心能力有哪些？'),
    (r'ai\system-design\llm-security.md', 'ai-llm-security', 'AI 系统设计',
     'LLM 应用有哪些安全风险？怎么防？'),
    (r'ai\system-design\ai-observability.md', 'ai-observability', 'AI 系统设计',
     'AI 应用怎么做好可观测性（Tracing/评测）？'),
    (r'ai\system-design\ai-voice.md', 'ai-voice', 'AI 系统设计',
     '实时语音 Agent 的架构与延迟优化怎么做？'),
]


# 第二批单篇：MySQL / 分布式 / MQ / 高可用性能 / Spring系统设计（java 组）
# 与 (rel, id slug, subject, domain, topic)；title_hint 取文件首个一级标题
ART_JAVA = [
    # MySQL
    (r'database\mysql\how-sql-executed-in-mysql.md', 'java-mysql-sql-executed', 'MySQL'),
    (r'database\mysql\innodb-implementation-of-mvcc.md', 'java-mysql-mvcc', 'MySQL'),
    (r'database\mysql\transaction-isolation-level.md', 'java-mysql-tx-isolation', 'MySQL'),
    (r'database\mysql\mysql-index.md', 'java-mysql-index-bplus', 'MySQL'),
    (r'database\mysql\mysql-index-invalidation.md', 'java-mysql-index-invalid', 'MySQL'),
    (r'database\mysql\mysql-query-execution-plan.md', 'java-mysql-explain', 'MySQL'),
    (r'database\mysql\mysql-logs.md', 'java-mysql-logs', 'MySQL'),
    (r'database\mysql\mysql-high-performance-optimization-specification-recommendations.md',
     'java-mysql-perf-spec', 'MySQL'),
    # 分布式
    (r'distributed-system\protocol\cap-and-base-theorem.md', 'java-cap-base', '分布式'),
    (r'distributed-system\protocol\consistent-hashing.md', 'java-consistent-hashing', '分布式'),
    (r'distributed-system\protocol\raft-algorithm.md', 'java-raft', '分布式'),
    (r'distributed-system\distributed-lock.md', 'java-distributed-lock2', '分布式'),
    (r'distributed-system\distributed-transaction.md', 'java-distributed-transaction', '分布式'),
    (r'distributed-system\distributed-id-design.md', 'java-distributed-id-design', '分布式'),
    (r'distributed-system\api-gateway.md', 'java-api-gateway', '分布式'),
    (r'distributed-system\rpc\rpc-intro.md', 'java-rpc-intro', '分布式'),
    (r'distributed-system\distributed-process-coordination\zookeeper\zookeeper-intro.md',
     'java-zookeeper-intro', '分布式'),
    # 消息队列
    (r'high-performance\message-queue\message-queue.md', 'java-mq-basics', '消息队列'),
    (r'high-performance\message-queue\kafka-questions-01.md', 'java-kafka', '消息队列'),
    (r'high-performance\message-queue\rabbitmq-questions.md', 'java-rabbitmq', '消息队列'),
    (r'high-performance\message-queue\rocketmq-questions.md', 'java-rocketmq', '消息队列'),
    # 高可用 / 性能优化
    (r'high-availability\limit-request.md', 'java-rate-limit', '高可用'),
    (r'high-availability\idempotency.md', 'java-idempotency', '高可用'),
    (r'high-availability\timeout-and-retry.md', 'java-timeout-retry', '高可用'),
    (r'high-availability\fallback-and-circuit-breaker.md', 'java-circuit-breaker', '高可用'),
    (r'high-performance\load-balancing.md', 'java-load-balancing', '性能优化'),
    (r'high-performance\read-and-write-separation-and-library-subtable.md',
     'java-rw-split-sharding', '性能优化'),
    (r'high-performance\deep-pagination-optimization.md', 'java-deep-pagination', '性能优化'),
    (r'high-performance\sql-optimization.md', 'java-sql-optimization', '性能优化'),
    (r'high-performance\data-cold-hot-separation.md', 'java-cold-hot-separation', '性能优化'),
    # Spring / 系统设计
    (r'system-design\framework\spring\ioc-and-aop.md', 'java-spring-ioc-aop', 'Spring'),
    (r'system-design\framework\spring\spring-transaction.md', 'java-spring-transaction', 'Spring'),
    (r'system-design\framework\spring\spring-boot-auto-assembly-principles.md',
     'java-spring-autoconfig', 'Spring'),
    (r'system-design\design-pattern.md', 'java-design-patterns', '系统设计'),
    (r'system-design\basis\RESTfulAPI.md', 'java-restful-api', '系统设计'),
    (r'system-design\security\jwt-intro.md', 'java-jwt', '系统设计'),
    (r'system-design\web-real-time-message-push.md', 'java-realtime-push', '系统设计'),
    (r'system-design\state-machine-and-workflow.md', 'java-state-machine-workflow', '系统设计'),
]
# 第二批单篇：操作系统 / 网络 / 数据结构 / 算法（cs 组，计算机基础科目）
ART_CS = [
    (r'cs-basics\operating-system\process-and-thread.md', 'cs-process-thread', '操作系统'),
    (r'cs-basics\operating-system\dead-lock.md', 'cs-deadlock', '操作系统'),
    (r'cs-basics\operating-system\memory-management.md', 'cs-memory-management', '操作系统'),
    (r'cs-basics\operating-system\virtual-memory.md', 'cs-virtual-memory', '操作系统'),
    (r'cs-basics\operating-system\io-multiplexing.md', 'cs-io-multiplexing', '操作系统'),
    (r'cs-basics\operating-system\zero-copy.md', 'cs-zero-copy', '操作系统'),
    (r'cs-basics\operating-system\os-lock-and-sync.md', 'cs-os-lock-sync', '操作系统'),
    (r'cs-basics\network\osi-and-tcp-ip-model.md', 'cs-tcpip-model', '计算机网络'),
    (r'cs-basics\network\tcp-connection-and-disconnection.md', 'cs-tcp-handshake', '计算机网络'),
    (r'cs-basics\network\tcp-time-wait.md', 'cs-tcp-timewait', '计算机网络'),
    (r'cs-basics\network\tcp-reliability-guarantee.md', 'cs-tcp-reliability', '计算机网络'),
    (r'cs-basics\network\http1.0-vs-http1.1.md', 'cs-http-versions', '计算机网络'),
    (r'cs-basics\network\http-vs-https.md', 'cs-http-https', '计算机网络'),
    (r'cs-basics\network\dns.md', 'cs-dns', '计算机网络'),
    (r'cs-basics\network\the-whole-process-of-accessing-web-pages.md',
     'cs-url-to-page', '计算机网络'),
    (r'cs-basics\network\http-vs-rpc.md', 'cs-http-vs-rpc', '计算机网络'),
    (r'cs-basics\data-structure\lru-cache.md', 'cs-lru-cache', '数据结构'),
    (r'cs-basics\data-structure\bloom-filter.md', 'cs-bloom-filter', '数据结构'),
    (r'cs-basics\data-structure\heap.md', 'cs-heap', '数据结构'),
    (r'cs-basics\data-structure\red-black-tree.md', 'cs-red-black-tree', '数据结构'),
    (r'cs-basics\data-structure\trie.md', 'cs-trie', '数据结构'),
    (r'cs-basics\data-structure\hash-table.md', 'cs-hash-table', '数据结构'),
    (r'cs-basics\data-structure\skip-list.md', 'cs-skip-list-generic', '数据结构'),
    (r'cs-basics\algorithms\10-classical-sorting-algorithms.md', 'cs-sorting', '算法'),
    (r'cs-basics\algorithms\dynamic-programming.md', 'cs-dynamic-programming', '算法'),
    (r'cs-basics\algorithms\binary-search.md', 'cs-binary-search', '算法'),
    (r'cs-basics\algorithms\two-pointers-and-sliding-window.md', 'cs-two-pointers', '算法'),
    (r'cs-basics\algorithms\top-k.md', 'cs-top-k', '算法'),
    (r'cs-basics\algorithms\dfs-bfs.md', 'cs-dfs-bfs', '算法'),
    (r'cs-basics\algorithms\complexity-analysis.md', 'cs-complexity', '算法'),
]


def first_heading(path):
    """取文件第一个一级标题做 title_hint，没有就退回文件名。"""
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                m = re.match(r'^#\s+(.+)$', line.strip())
                if m:
                    return re.sub(r'[⭐️⭐]', '', m.group(1)).strip()
    except OSError:
        pass
    return os.path.splitext(os.path.basename(path))[0]


def build_articles(taken):
    """第二批单篇 → {'java': [...], 'cs': [...]}"""
    out = {'java': [], 'cs': []}
    base = os.path.join(SRC, 'JavaGuide', 'docs')
    for group, arts, domain in (('java', ART_JAVA, 'Java后端'),
                                ('cs', ART_CS, '计算机基础')):
        subject = 'cs' if group == 'cs' else 'java'
        for rel, slug, topic in arts:
            path = os.path.join(base, rel)
            if not os.path.exists(path):
                print('  !! 文章不存在: %s' % rel)
                continue
            body = clean_body(read_md(path))
            if len(re.sub(r'\s+', '', body)) < 600:
                print('  跳过（素材过短）: %s' % rel)
                continue
            cid = take_id(slug, taken)
            e = entry(cid, subject, domain, topic, ['面试', topic],
                      first_heading(path), path)
            out[group].append(e)
    return out


def split_questions(path, picks):
    """按 ### 切题，返回 {题序: (题干, 正文)} —— 序号与白名单同口径。"""
    t = open(path, encoding='utf-8').read()
    t = re.sub(r'^---\n.*?\n---\n', '', t, flags=re.S)
    out, idx = {}, 0
    for pt in re.split(r'(?m)^###\s+', t)[1:]:
        title = pt.split('\n', 1)[0].strip()
        body = pt.split('\n', 1)[1] if '\n' in pt else ''
        if '？' in title or '?' in title or len(title) < 50:
            idx += 1
            out[idx] = (title, body)
    return {k: out[k] for k in picks if k in out}


def slug_or_seq(title, seq_prefix, seq_no, taken):
    t = re.sub(r'[⭐️⭐\s]+', '', title)
    s = re.sub(r'[^A-Za-z0-9]+', '-', t).strip('-').lower()
    s = re.sub(r'-+', '-', s)
    return take_id(s if len(s) >= 10 else '%s%02d' % (seq_prefix, seq_no), taken)


def build_questions(taken):
    """questions 合集拆题 → {group: [entries]}"""
    out = {'java': [], 'redis': [], 'agent': [], 'cs': []}
    for rel, subject, topic, seq_prefix, picks in Q_PICKS:
        path = os.path.join(SRC, 'JavaGuide', 'docs', rel)
        if not os.path.exists(path):
            print('  !! 合集不存在: %s' % rel)
            continue
        qs = split_questions(path, picks)
        for n in picks:
            if n not in qs:
                print('  !! 白名单题号缺失: %s #%d' % (rel, n))
                continue
            title, body = qs[n]
            clean = clean_body(body)
            if len(re.sub(r'\s+', '', clean)) < 400:
                print('  跳过（素材过短）: %s #%d %s' % (rel, n, title[:30]))
                continue
            hint = title.replace('⭐️', '').replace('⭐', '').strip()
            if subject == 'java':
                group = 'redis' if topic == 'Redis 面试' else 'java'
                domain = 'Java后端'
            elif subject == 'cs':
                group, domain = 'cs', '计算机基础'
            else:
                group, domain = 'agent', 'AI工程'
            slug_pre = {'java': 'java-', 'cs': 'cs-', 'ai': 'ai-'}[subject] \
                + seq_prefix
            cid = slug_or_seq(hint, slug_pre, n, taken)
            e = entry(cid, subject, domain, topic,
                      ['面试', topic], hint, path)
            e['src_inline'] = clean
            out[group].append(e)
    return out


def build_ai_files(taken):
    items = []
    base = os.path.join(SRC, 'JavaGuide', 'docs')
    for rel, slug, topic, hint in AI_FILES:
        path = os.path.join(base, rel)
        if not os.path.exists(path):
            print('  !! 文章不存在: %s' % rel)
            continue
        body = clean_body(read_md(path))
        if len(re.sub(r'\s+', '', body)) < 600:
            print('  跳过（素材过短）: %s' % rel)
            continue
        cid = take_id(slug, taken)
        items.append(entry(cid, 'ai', 'AI工程', topic, ['AI', topic], hint, path))
    return items


# ---------------------------------------------------------------- main
def load_manifest(group):
    path = os.path.join(OUT, 'manifest_%s.json' % group)
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    if group == 'cs':                      # cs 是第二批新建的组
        return []
    raise SystemExit('缺 manifest_%s.json —— 先跑一次全量 build' % group)


GROUPS = ('agent', 'redis', 'java', 'cs')

# 人工剔除的源文件：与库内已有卡同主题（gen_cs 的握手/HTTPS/进程线程、
# springboot.js 的自动装配），新条目和重跑都不许再进来
SKIP_SRC = {'tcp-connection-and-disconnection.md', 'http-vs-https.md',
            'process-and-thread.md', 'spring-boot-auto-assembly-principles.md'}


def main():
    taken = existing_card_ids()
    print('库内已有卡片 id: %d' % len(taken))
    manifests = {g: load_manifest(g) for g in GROUPS}
    for g in GROUPS:                                 # 先清掉历史遗留的剔除项
        n = len(manifests[g])
        manifests[g] = [e for e in manifests[g]
                        if os.path.basename(e.get('src_path', '')) not in SKIP_SRC]
        if len(manifests[g]) != n:
            print('%s: 清掉与已有卡重复的 %d 条' % (g, n - len(manifests[g])))
    for g, items in manifests.items():                 # 旧 id 进撞车池，绝不重建
        for e in items:
            taken.add(e['id'])
    added = dict.fromkeys(GROUPS, 0)
    # 幂等保护：(src_path, title_hint) 已在清单里的不再生成 —— 否则重跑一遍
    # 会把第一批条目以 -2 后缀重复追加（take_id 防的是 id 撞，防不了内容撞）
    seen_keys = {(e.get('src_path'), e.get('title_hint'))
                 for items in manifests.values() for e in items}
    keep = lambda items: [
        e for e in items
        if (e.get('src_path'), e.get('title_hint')) not in seen_keys
        and os.path.basename(e.get('src_path', '')) not in SKIP_SRC]
    for g, items in build_questions(taken).items():
        items = keep(items)
        manifests[g].extend(items)
        seen_keys.update((e['src_path'], e['title_hint']) for e in items)
        added[g] += len(items)
    ai_items = keep(build_ai_files(taken))
    manifests['agent'].extend(ai_items)
    seen_keys.update((e['src_path'], e['title_hint']) for e in ai_items)
    added['agent'] += len(ai_items)
    for g, items in build_articles(taken).items():
        items = keep(items)
        manifests[g].extend(items)
        seen_keys.update((e['src_path'], e['title_hint']) for e in items)
        added[g] += len(items)
    for g in GROUPS:
        items = manifests[g]
        path = os.path.join(OUT, 'manifest_%s.json' % g)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print('%-6s 共 %3d 张（本次 +%d）→ %s'
              % (g, len(items), added[g], path))


if __name__ == '__main__':
    main()
