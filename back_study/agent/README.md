# agent/ —— LangGraph + LangChain + 本地 Ollama

一个能跑的最小 AI 层，挂在现有卡片库上。**可选旁支**，不进后端主链路。

## 目录结构（先看懂这层，再看下面）

```
agent/
├── config.py      【公共】所有可调参数（温度、重试上限、检索条数……）
├── model.py       【公共】造模型。唯一决定「用哪个模型、什么参数」的地方
├── qa/            【业务】问答 Agent —— 已跑通，接口 /api/agent/ask
│   ├── tools.py   能做什么：查卡片 / 看细节 / 查邻居 / 查今日到期
│   ├── nodes.py   每步做什么：检索 / 回答 / 自检（各自的提示词在这）
│   ├── graph.py   按什么顺序做：把节点连成图（固定流程 & ReAct 两条）
│   ├── runtime.py 怎么跑起来：实例缓存 / 多轮历史 / 流式输出
│   ├── websearch.py 联网搜索（360 搜索，免 key；请求带 webSearch:true 才用）
│   └── demo.py    命令行入口
└── planner/       【业务】学习路径规划 Agent —— 服务 /path 今日路径页
    ├── planner.py LangGraph 编排（collect→score→write→verify→route）
    └── run.py     命令行入口（--dump 验取数 / --top N 跑全图 / --status 探活）
```

**关键约定（2026-09-29 定的）**：
- `config.py` / `model.py` 是**公共层**，所有业务 Agent 共用，改行为先来这看。
- 每个业务 Agent 是**自己一个子目录**（`qa/`、`planner/`），里面只放它自己的
  `tools / nodes / graph / runtime`。新增 Agent 就再建一个目录，互不污染。
- 业务 Agent 内部 `from .. import config as C` / `from .. import model as M` 取公共层；
  需要独立 `python xxx/run.py` 直跑时，用绝对 import `from agent import config as C`。
- **「流程里有箭头吗？」是上不上 LangGraph 的唯一判据**：没有就别上，
  `core/llm.py` 的 `enrich` / `to_card` 那种「一次结构化抽取」用三个函数写完就对。

## 装

```bash
.venv/Scripts/pip.exe install -i https://pypi.tuna.tsinghua.edu.cn/simple \
    langgraph langchain langchain-ollama
```

2026-09-29 装的版本：langgraph 1.2.12 / langchain 1.4.3 / langchain-core 1.6.5 /
langchain-ollama 1.1.0（Python 3.10.11），顺带 30 多个间接依赖。

不装也完全能起服务 —— 只有调 `/api/agent/*` 时才返 503 并提示怎么装。

## 跑：问答 Agent（qa/）

```bash
cd E:\AAA_实验室项目\study

# 命令行
.venv/Scripts/python.exe back_study/agent/qa/demo.py --status
.venv/Scripts/python.exe back_study/agent/qa/demo.py "SpringBoot 自动装配是怎么跑起来的"
.venv/Scripts/python.exe back_study/agent/qa/demo.py --mode react "今天该复习什么"
.venv/Scripts/python.exe back_study/agent/qa/demo.py --stream "什么是 RAG"
.venv/Scripts/python.exe back_study/agent/qa/demo.py --chat        # 多轮，带上下文

# HTTP（先起后端 python back_study/run.py 8080）
curl --noproxy '*' http://127.0.0.1:8080/api/agent/status
curl --noproxy '*' -X POST http://127.0.0.1:8080/api/agent/ask \
     -H "Content-Type: application/json" -d '{"question":"今天该复习什么","mode":"react"}'
```

第一次跑慢是正常的（Ollama 要加载 5GB 模型进显存）。实测：flow 约 26 秒，
react 约 24 秒，流式约 14 秒出第一个字。

### 问答 HTTP 接口

| 端点 | 说明 |
|---|---|
| `GET /api/agent/status` | 探活。ok:false 是正常状态（HTTP 仍 200），前端据此换提示文字 |
| `POST /api/agent/ask` | 问一句。`mode` 选 flow/react，`stream:true` 走 SSE |

`AskIn`: `question` / `mode` / `stream` / `history` / `profile` / `webSearch`
`AskOut`: `ok` / `answer` / `mode` / `steps`（react 的工具调用轨迹）/ `ms`

`webSearch:true` 时在卡片资料后追加【网页】搜索结果（360 搜索，免 key、
失败静默不影响回答）；前端问答页顶栏的「联网」按钮就是它。

### 问答两种模式怎么选

```
build_qa()     流程固定：检索 → 回答 → 自检 → 不合格重来
               每一步你说了算，能在任意一步插手。适合「该查什么」确定的场景。
build_react()  ReAct：模型自己决定查不查、查什么、查几次
               灵活，但控制不了它绕几圈 —— 必设 recursion_limit，工具别给太多。
```

react 的检索底料由 `runtime._react_ground()` **代码代搜**后拼在问题后面
（提示词光写"先 search_cards"，8B 实测不查）；命中的卡直接算进 `sources`。
`webSearch:true` 时底料里还会带上【网页】搜索结果（网页不进 sources）。

## 跑：路径规划 Agent（planner/）

```bash
cd E:\AAA_实验室项目\study

# 只验取数（不调模型，秒回）—— 改图前先跑这个确认数据对
.venv/Scripts/python.exe back_study/agent/planner/run.py --dump

# 跑全图（调模型，出今天该学的候选 + 打分）
.venv/Scripts/python.exe back_study/agent/planner/run.py --top 20

# 探活
.venv/Scripts/python.exe back_study/agent/planner/run.py --status
```

`planner.py` 的图：`collect`（拉候选+先验掌握度）→ `score`（按优先级/先修/到期打分）
→ `write`（**TODO 待填**：调模型生成自然语言路径）→ `verify`（拒空/超限/
幻觉 id/重复/缺理由）→ `route`（`C.MAX_TRIES` 次内不过就放行）。

## 三条硬约束

1. **不进主链路。** langchain import 一次 2-3 秒，塞进 `app/main.py` 等于让每次
   后端冷启动替 AI 买单。`app/routers/agent.py` 全部在函数内部 import。
2. **零成本 import。** `model.py` / 各 `tools.py` 把 langchain 的 import 写在函数里
   —— 因为探活端点要复用它们，探活不该拉起整棵依赖树。
   `nodes` / `graph` / `runtime` 是「真跑 agent 才加载」，可以在顶部 import。
3. **模型选择复用 `core/llm.py`。** 不在 agent 里另起一套优先级，
   否则会出现网页端用 qwen3、agent 用另一个，然后你以为是模型不行。

**为什么问答路由用 async def**（其他路由都是同步 def）：
其他路由只做毫秒级 db 读写，同步 def 丢线程池没问题；这里是**几十秒**的调用，
线程池默认 40 槽，几个并发就占满，连 `/api/health` 都排不上队。
所以用 `async def` + `asyncio.to_thread()` —— 既不堵事件循环，也不占线程池槽位。

## 踩过的坑（都是实测，不是抄文档）

1. **推理模型必须关 think**。qwen3 / deepseek-r1 默认把 token 烧在 `<think>` 里，
   表现是「等了十几秒，返回空字符串」。`model.py` 里写死 `think=False`。
2. **num_ctx 要显式给**。Ollama 默认上下文几千，塞长文档**静默截断** ——
   不报错，就是少了后半段，极难查。
3. **`db.due_list()` 有两种返回结构**。文件后端把卡放在 `row['card']` 里，
   MySQL 快路径返回扁平行。只按顶层取 `id` 会全是 null，模型拿到一堆 null
   就得出「卡片库是空的」的结论，然后理直气壮告诉用户假话。（已兼容）
4. **模型会把工具参数填成空串**（实测调过 `search_cards({'query': ''})`）。
   工具要防御：没关键词就列全部，别回「没找到」。
5. **数字写在返回的开头，模型经常看不见**（列完 20 张还说"没有统计张数的功能"）。
   总数放末尾。
6. **8B 模型自检能力有限**，自检没过最多重来一次，重太多次只是烧时间。
7. **计时别写进 print 的参数里**：`print('...%s' % (time.time()-t0, ask(q)))`
   会先算减法（元组从左到右求值），永远显示 0.0s。
