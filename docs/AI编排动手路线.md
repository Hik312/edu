# AI 模块：LangGraph 编排 · 动手路线

> 这份文档是**给你照着写的**，不是给你读的。
> `back_study/agent/` 里有一份已经跑通的参考答案 —— 建议**先别看**，
> 按下面的顺序自己写一遍，卡住了再去对应文件里对答案（每步都标了参考文件）。
>
> 自己写的放 `back_study/agent/planner/`。`agent/` 已经**按业务分开**了：
> 公共的（config / model）在根目录，**每个 Agent 一个子目录**。
> 所以你写 planner 不会碰到问答那条链路，参考答案 `agent/qa/` 就在隔壁。

## 开工前：搞清一件事

**你的流程里有箭头吗？** LangGraph 解决的是「多步 + 有分支 + 要回头」的问题。
如果只是一问一答（比如"把这段文档抽成 JSON"），用 `core/llm.py` 三个函数写完就对了，
套 LangGraph 是纯负担 —— 多写三倍代码，还慢。

你这个 AI 助手有箭头：提问 → 检索 → 回答 → **觉得答得不好？回去重检索**。
所以值得上。

---

## 先定：本项目编排哪个模块

> 这条是 2026-09-29 补的。如果你已经按下面的 Step 练过手、只是不知道
> 「这些节点该拼成项目里的什么东西」，看这一节就够了。

### 三个候选

| 候选 | 长在项目哪里 | 编排含量 | 建议 |
|---|---|---|---|
| **A 今日路径规划** | `/path` 页 + `app/routers/learning.py` | 中：1 个 LLM 节点 + 1 个自检循环 | **先做** |
| B 文档 → 卡片流水线 | `/generate` 页 + `imports.py` + `core/importer.py` | 高：并行 + 重试 + 门禁 + 人工确认 | 第二个做 |
| C 卡片质量审核 | `/cards` 页 | 低：基本是单节点批处理 | 不必上编排 |

### 为什么是 A

1. **BKT 上周刚落地，到现在没有任何地方"看见"它** —— 只在本轮写的
   `bkt_e2e.py` 里跑过。这是让它第一次产生用户可见价值的最短路径。
2. **前端已经把接口留好了。** `web/src/views/path/PathView.vue` 顶部注释原文：
   > 后期 BKT 接进来以后，替换的是**分段的依据**（现在是三档标记，
   > 以后是掌握度概率 + 前置依赖），这一页的结构不用动。
3. **数据现成。** 不用准备文档、不用等人标数据，`due_list` 现在就有队列。
4. **只有一个节点调模型。** 本地 8B 跑一次 10–20 秒，调试节奏能接受。
   B 那条线每章 20–30 秒，跑一遍整篇文档要好几分钟，不适合边写边试。

### 节点怎么切（函数都是现成的，别自己造）

| 节点 | 调什么 | 拿到的东西 |
|---|---|---|
| 取候选 | `db.due_list(include_all=True)` | `x['card']['id']`、`x['level']`、`x['overdue']` |
| 算掌握度 | `db.mastery_of(user_id, cid, refresh=True)` | `p ∈ [0,1]`，走 Redis 缓存 |
| 排序 · 追前置 | `db.neighbors(cid, depth=1)` | 找 `related` 里 `kind=prereq` 的卡 |
| 写理由（唯一调 LLM 的） | `agent/model.py` 造的模型 | 「为什么先学这几张」的自然语言 |
| 自检 | 纯 Python | 模型返回的 id 必须 ⊆ 候选集 |

**自检是整个编排的价值所在** —— 8B 模型在"给你列 5 张卡的 id"这种任务上
编造率不低。它会返回听起来很像真的 `spring-aop` 之类，而库里根本没有。
不校验就直接往下走，用户会点到一个 404 的卡片。

### 三个一定要知道的字段细节

1. `due_list()` 的每一项是**嵌套结构**：卡片在 `x['card']` 里，进度在 `x['progress']` 里。
   只按顶层取 `id` 会拿到一堆 `null`。（早期文件后端和 MySQL 快路径结构不一致，
   现在**已经统一**成这种嵌套；`app/routers/learning.py:71` 是标准取值写法。）
2. `x['overdue'] == 999` 是哨兵值，意思是**这张卡从没复习过**，不是"逾期 999 天"。
   没复习过的卡掌握度就是 `p_init`（`algo/bkt.py` 里默认 **0.25**），
   不要拿 999 去算什么。（实测 `--dump` 打出来全是 0.25 就说明取数对了。）
3. `mastery_of()` 默认读缓存。刚调完 `set_level()` 要传 `refresh=True`，
   否则拿到的是上一次的值。

### 写在哪个目录：先沙盒，跑通再合并

先说清一件事：**`agent/` 现在装的是「一个」问答 Agent，不是「Agent 框架」。**
它里面的 `QAState` / `retrieve` / `answer` / `grade` / `route` 都是为问答服务的。
所以 planner 是它的**第二个 Agent**，不是它的替代品。

**现在写 `back_study/agent/planner/`**：

- `agent/qa/` 已经接了 `/api/agent/ask` 在跑 —— 它在**自己的子目录**里，
  你动 planner 不会打断它（这就是按业务分目录的好处，不需要另开沙盒）
- 第一次写图会来回推翻重来，`agent/qa/` 那份实现就在隔壁，随时对照

> **骨架已经建好了**，不用从空文件开始：
>
> ```
> back_study/agent/
> ├── config.py        【公共】参数集中
> ├── model.py         【公共】模型工厂
> ├── qa/              【已跑通】问答 —— 你的参考答案
> └── planner/         【你要写】路径规划
>     ├── planner.py   ★ 你要动手的文件
>     └── run.py       命令行入口
> ```
>
> `planner.py` 里 **`collect` / `score` / `verify` / `route` 已经写好并验证过**，
> 只有 `write`（唯一调模型的那个）留了 3 处 `TODO(你)`。
>
> ```bash
> .venv/Scripts/python.exe back_study/agent/planner/run.py --status   # 环境探活
> .venv/Scripts/python.exe back_study/agent/planner/run.py --dump     # 只跑取数，几秒出结果
> .venv/Scripts/python.exe back_study/agent/planner/run.py --top 5    # 跑全图（write 填完才跑得通）
> ```
>
> **先跑 `--dump`。** 它会打出候选卡 / 掌握度 / 前置 / 优先分四列，
> 你逐列核对一遍再动 `write` —— 数据错了，模型写得再漂亮也是错的。

| | 处理 | 原因 |
|---|---|---|
| `agent/config.py` | **import，不复制** | 温度 / 重试上限 / 检索条数，两份就会漂移 |
| `agent/model.py` | **import，不复制** | 它建在 `core/llm.pick_model()` 之上。复制一份就会出现「网页精读用 qwen3、planner 用另一个」，然后你以为是模型不行 |
| State 字段 | 自己写 | planner 的状态是「候选卡 + 掌握度 + 理由」，和问答完全不同 |
| 节点和图 | 自己写 | |
| 取数 | **直接调 `db.*`，别绕 `agent/qa/tools.py`** | 那是问答的工具，返回 str 给模型看；planner 要的是数据（dict） |

```python
# agent/planner/planner.py 开头（已实测能跑通）
import os
import sys

# 两次 dirname：planner/ → agent/ → back_study/。core/ 也要挂（db 要用）。
_BACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_BACK, 'core'), _BACK):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agent import config as C            # 零成本：不拉 langchain
from agent import model as M

# 共享基建的用法（签名都是现成的）
#   M.pick()                        → 模型名
#   M.chat(temperature=..., num_ctx=...)  → ChatOllama 实例
#   C.TEMPERATURE / C.RECURSION_LIMIT / C.MAX_TRIES ...
```

**为什么用 `from agent import` 而不是 `from .. import`**：planner.py 也支持
直接 `python planner.py` 跑，相对导入会报 "no known parent package"。
挂 sys.path + 绝对导入，两种跑法都能活。

**加第三个 Agent 时**：照 `qa/` 抄一个子目录就行 —— 建目录、`from .. import config, model`、
写自己的 state / nodes / graph。外面的东西一个都不用改。

### 落点文件

```
back_study/agent/planner/planner.py     你要写的图（骨架已建好，write 节点待填）
back_study/agent/planner/lab/s1.py…s6.py  从零练手的步骤（和成品分开，互不影响）
back_study/app/routers/agent.py         参考它加一个 POST /api/agent/plan
web/src/views/path/PathView.vue         把 fetchDue 旁边加一个 fetchPlan
```

前端那一步可以最后做 —— 先用 `demo.py` 在命令行看见结果，确认链路通了再接页面。

---

## Step 0 · 环境自检（5 分钟）

```bash
cd E:\AAA_实验室项目\study

# 依赖在不在
back_study/.venv/Scripts/python.exe -c "from langgraph.graph import StateGraph, START, END; print('langgraph ok')"

# Ollama 在不在、有没有模型
curl -s --noproxy '*' http://127.0.0.1:11434/api/tags | head -c 300
```

**验收**：第一条打印 `langgraph ok`；第二条能看到 `qwen3:8b`。
（curl 访问 127.0.0.1 必须加 `--noproxy '*'`，本机开着代理，不加会 502，
很容易误判成服务没起来。）

---

## Step 1 · 一个节点的最小图（30 分钟）

**目标**：理解 State 是什么、节点怎么接、图怎么编译。

新建 `back_study/agent/planner/lab/s1.py`：

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):          # ← 整条流水线唯一的数据载体
    question: str
    answer: str

def node_answer(s: State) -> dict:
    # TODO: 调模型，返回 {'answer': ...}
    # 提示：from langchain_ollama import ChatOllama
    #      llm = ChatOllama(model='qwen3:8b', temperature=0.3)
    #      llm.invoke(...) 返回 .content
    return {'answer': 'TODO'}

g = StateGraph(State)            # 1. 建图，声明状态形状
g.add_node('answer', node_answer)  # 2. 加节点
g.add_edge(START, 'answer')        # 3. 连边
g.add_edge('answer', END)
app = g.compile()                # 4. 编译

print(app.invoke({'question': '什么是 RAG？'}))
```

**验收**：`python back_study/agent/planner/lab/s1.py` 打出一段像样的回答（约 15-30 秒，
第一次要把 5GB 模型加载进显存）。

**这一步必踩的坑**：

- `qwen3:8b` 是**思考型模型**，不关思考链的话输出里混着大段内心独白。
  构造 `ChatOllama` 时要能关掉它（参考答案见 `agent/model.py`，搜 `think`）。
- import langchain 那几行**放在函数里**，不要放模块顶部。langchain 冷启动
  2-3 秒，放顶部就等于每次后端启动都替 AI 买单，而这个接口可能一天没人调。

参考：`agent/model.py`

---

## Step 2 · 两个节点 + 状态传递（30 分钟）

**目标**：节点之间**只通过 State 传数据**，不要搞全局变量。

加一个检索节点：

```python
class State(TypedDict):
    question: str
    context: str      # 检索到的卡片内容
    answer: str

def node_retrieve(s: State) -> dict:
    # TODO: 从卡片库里找出和问题相关的几张卡，拼成一段文字
    # 入口：sys.path 加上 back_study 和 back_study/core 之后 import db
    #      db.all_cards() 拿全部卡片，自己写个关键词打分
    return {'context': 'TODO'}

def node_answer(s: State) -> dict:
    # TODO: 把 s['context'] 塞进提示词里再问模型
    #       —— 这一步做完，回答就从「模型瞎编」变成「基于你的卡片库」
    return {'answer': 'TODO'}

g.add_edge(START, 'retrieve')
g.add_edge('retrieve', 'answer')
```

**验收**：问"SpringBoot 自动装配怎么跑起来的"，回答里应该出现你卡片库里的具体说法，
而不是泛泛而谈。

**坑**：`db.all_cards()` 返回的卡片是完整 dict，别整个塞给模型 —— 8B 模型上下文
塞满就答非所问了。只挑 `title / oneLine / mechanism` 这几个字段。

参考：`agent/tools.py`（数据函数 `rank`）、`agent/nodes.py`（`retrieve`）

---

## Step 3 · 条件边 + 回头重来（45 分钟）★这一步是编排的价值所在

**目标**：答完之后自己检查一遍，不满意就**回到检索节点换个角度再来**。

```python
class State(TypedDict):
    question: str
    context: str
    answer: str
    retry: int        # 已经重来了几次

def node_check(s: State) -> dict:
    # TODO: 让模型判断「这个回答是否真的用上了 context」
    #      返回 {'ok': True/False}
    return {'ok': True}

def should_retry(s: State) -> str:
    # 条件边：返回**下一个节点的名字**
    if s.get('ok') or s.get('retry', 0) >= 2:
        return 'end'
    return 'retrieve'          # ← 回到前面那个节点

g.add_node('check', node_check)
g.add_edge('answer', 'check')
g.add_conditional_edges('check', should_retry,
                        {'retrieve': 'retrieve', 'end': END})
```

**验收**：故意问一个卡片库里没有的东西（比如"怎么用 Rust 写内核"），
应该看到它重试 1-2 次然后老实说"库里没有"。把 `retry` 打印出来确认真的走了循环。

**这一步必踩的坑**：

- **循环必须有出口**。`retry` 不递增、或者上限判断写反，图会一直转，
  直到 `recursion_limit` 报错才停。先写上限位再写循环条件。
- 让模型做判断时，要它**只输出一个词**（比如 `OK` / `RETRY`），然后在代码里
  用 `in` 判断，别让它输出一段话再解析 —— 8B 模型的指令遵循没那么稳。

参考：`agent/graph.py`（`build_qa`）、`agent/nodes.py`（`check`）

---

## Step 4 · 让模型自己决定调什么工具（45 分钟）

**目标**：从"我写死流程"变成"模型自己决定查什么"。

```python
from langchain_core.tools import tool

@tool
def find_card(query: str) -> str:
    """按关键词找卡片。用户问到某个具体知识点时用这个。"""
    # TODO: 返回 JSON 字符串（工具返回值必须是字符串）
    return '[]'

tools = [find_card, ...]           # ★ 别超过 6 个
llm_with_tools = llm.bind_tools(tools)
```

**验收**：问"今天该复习什么"，模型应该**自己**去调 `due_today` 这类工具，
而不是你写死先调哪个。把返回的 `tool_calls` 打出来看。

**坑（都是实测出来的）**：

- 工具的 **docstring 是给模型看的说明书**，不是给人看的注释。写清"什么时候用"，
  模型才知道该不该调它。写"查找卡片"这种废话，模型永远不调。
- **工具别超过 6 个**。8B 模型在十几个工具里选，会开始乱选或不选。
- **模型会把参数填成空串**。工具函数第一行先判空，空了就返回全部列表兜底。
- **数字写在返回值的开头，模型看不见**。总数、统计值放末尾。
- 调 `db.due_list()` 时注意：文件后端和 MySQL 返回**结构不一样**
  （一个卡片嵌在 `row['card']` 里，一个是平铺）。只按顶层取 `id` 会拿到一堆
  `null`，然后模型理直气壮地说"卡片库是空的"—— 事实上库里有 20 张卡。
  这种故障最阴的地方是：**模型没有编造，它只是忠实地读了错误的数据。**

参考：`agent/tools.py`

---

## Step 5 · ReAct：让循环由模型控制（30 分钟）

手写图（Step 1-4）的好处是每步都看得见；坏处是流程写死。
ReAct 是把「下一步干什么」交给模型：

```python
from langgraph.prebuilt import create_react_agent
agent = create_react_agent(llm, tools)
result = agent.invoke({'messages': [('user', question)]},
                      config={'recursion_limit': 20})   # ★ 必设
```

**验收**：问"我有几张卡？哪几张该复习了？"，它应该连着调两个工具再回答。
把 `result['messages']` 打出来，能看到完整的思考-调用-观察轨迹。

**坑**：`recursion_limit` **必须显式给**，否则模型在工具之间打转时能跑到默认上限，
报出来的错还看不出是死循环。

参考：`agent/graph.py`（`build_react`）、`agent/runtime.py`

---

## Step 6 · 流式输出（30 分钟）

本地 8B 出字慢，20 秒空白 ≈ 用户以为坏了。流式必须做。

```python
async for chunk in app.astream_events(inputs, version='v2'):
    if chunk['event'] == 'on_chat_model_stream':
        print(chunk['data']['chunk'].content, end='', flush=True)
```

**验收**：能看到一个字一个字往外蹦，而不是等 20 秒一次性出完。

参考：`agent/runtime.py`（`stream`）、`app/routers/agent.py`（SSE 那段）

---

## Step 7 · 接进 FastAPI（45 分钟）

按项目的路由约定来（`app/routers/` 下一个业务域一个文件）：

```python
# app/routers/planner.py
@router.post('/api/agentlab/ask')
async def ask(body: XxxIn):          # ★ async def
    out = await asyncio.to_thread(run_my_graph, body.question)
    return {'ok': True, 'answer': out}
```

然后把你的 router 加进 `app/routers/__init__.py` 的 `ALL` 元组里才会生效。

**为什么这里用 `async def`，而其他路由都是同步 `def`**（项目里唯一一个例外）：
AI 单次调用 20-30 秒。同步 `def` 会被丢进线程池，默认只有 **40 个槽**，
几个并发就把池子占满，连 `/api/health` 都排不上队。
`async def` + `asyncio.to_thread()` 既不堵事件循环，也不占线程池槽位。

**验收**：
```bash
back_study/.venv/Scripts/python.exe back_study/run.py 8099
curl -s --noproxy '*' -X POST http://127.0.0.1:8099/api/agentlab/ask \
  -H "Content-Type: application/json" -d '{"question":"什么是 RAG"}'
```

参考：`app/routers/agent.py`

---

## Step 8 · 选做：多轮对话 + 断点续跑

- **多轮**：把历史消息存在 `State` 里（`messages: list`），每轮 append。
  参考答案在 `agent/runtime.py` 的 `chat()`。
- **断点续跑**：LangGraph 的 checkpointer 可以接 PostgreSQL —— 你机器上
  PG 已经装好了（`study_algo` 库，密码 123456）。接上之后，对话能跨进程恢复。
  你现在已经有两个 `langgraph` / `langgraph_db` 库，就是之前试这个留下的。

---

## 全部踩过的坑（按被坑的概率排序）

| # | 坑 | 症状 |
|---|---|---|
| 1 | langchain 的 import 写在模块顶部 | 后端冷启动凭空慢 2-3 秒 |
| 2 | 思考型模型没关思考链 | 输出里混一大段 `思考：...`，解析全乱 |
| 3 | ReAct 没设 `recursion_limit` | 模型打转，报的错还看不出是死循环 |
| 4 | 工具超过 6 个 / docstring 写得含糊 | 模型该调不调、不该调乱调 |
| 5 | 工具参数被模型填空串 | 工具返回空，模型说"没有数据" |
| 6 | 循环没有出口条件 | 图一直转，直到超限报错 |
| 7 | 总数写在返回值开头 | 模型"数不出有几张卡" |
| 8 | `due_list()` 两种返回结构没兼容 | 全是 `null`，模型以为库是空的 |
| 9 | AI 路由写成同步 `def` | 几个并发把线程池占满，health 都排队 |
| 10 | `num_ctx` 没显式给 | 长文档被静默截断，还以为是模型笨 |

---

## 每步的对照表

| 步骤 | 你要写 | 参考答案 |
|---|---|---|
| 1 最小图 | `agent/planner/lab/s1.py` | `agent/model.py` |
| 2 检索 | `agent/planner/lab/s2.py` | `agent/qa/tools.py`、`agent/qa/nodes.py` |
| 3 条件边/循环 | `agent/planner/lab/s3.py` | `agent/qa/graph.py:build_qa` |
| 4 工具调用 | `agent/planner/lab/s4.py` | `agent/qa/tools.py` |
| 5 ReAct | `agent/planner/lab/s5.py` | `agent/qa/graph.py:build_react` |
| 6 流式 | `agent/planner/lab/s6.py` | `agent/qa/runtime.py:stream_react` |
| 7 HTTP | `app/routers/planner.py` | `app/routers/agent.py` |

## 命令速查

```bash
cd E:\AAA_实验室项目\study
back_study/.venv/Scripts/python.exe back_study/agent/planner/lab/s1.py   # 跑你的某一步
back_study/.venv/Scripts/python.exe back_study/agent/qa/demo.py --status # 参考答案探活
back_study/.venv/Scripts/python.exe back_study/agent/planner/run.py --dump  # 验规划取数
node back_study/scripts/check.js                                  # 改完跑全量校验
```
