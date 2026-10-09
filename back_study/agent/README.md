# agent/ —— LangGraph + LangChain + 本地 Ollama

一个能跑的最小 AI 层，挂在现有卡片库上。**可选旁支**，不进后端主链路。

## 目录结构（先看懂这层，再看下面）

```
agent/
├── config.py      【公共】所有可调参数（温度、重试上限、检索条数……）
├── model.py       【公共】造模型。唯一决定「用哪个模型、什么参数」的地方
├── qa/            【业务】问答 Agent —— 已跑通，接口 /api/agent/ask
│   ├── tools.py   4 个内部工具：查卡片 / 看细节 / 查邻居 / 查今日到期
│   ├── nodes.py   每步做什么：检索 / 回答 / 自检（各自的提示词在这）
│   │              answer 节点带 token sink，流式靠它
│   ├── graph.py   按什么顺序做：把节点连成图（固定流程 & ReAct 两条）
│   ├── runtime.py 怎么跑起来：实例缓存 / 多轮历史 / **两个模式都流式**
│   ├── websearch.py 联网搜索（360 搜索，免 key；请求带 webSearch:true 才用）
│   ├── retrieval.py 混合检索（向量 + 关键词双通道，给 RAG 用）
│   ├── retr_cache.py 检索结果缓存（Redis，实测 384ms → 63ms）
│   ├── ans_cache.py  答案缓存（Redis，命中毫秒级；见下方「三个缓存」）
│   └── demo.py    命令行入口
├── cards/         【业务】造卡 Agent —— 把文档/知识点变成原理卡（详见 docs/学习路线.md 6.1）
│   ├── nodes.py   refine 定切分点 → draft 出草稿
│   ├── dedup.py   查重（近重标题去重）
│   ├── graph.py   造卡流转（只流转，runtime 落盘）
│   └── runtime.py 实例缓存 / 落盘 / 查重
├── verify/        【业务】卡片校验 / 自纠 —— react 答完后核对引用卡
│   ├── runtime.py 逐张联网取证 + 一次批量 LLM 判别（300s→60s）
│   └── cache.py   校验结果缓存（Redis，命中秒回）
├── planner/       【业务】学习路径规划 Agent —— 服务 /path 今日路径页
│   ├── planner.py LangGraph 编排（collect→score→write→verify→route）
│   └── run.py     命令行入口（--dump 验取数 / --top N 跑全图 / --status 探活）
├── mcp.py         【公共】MCP 客户端桥接：起子进程 → 把 server 工具包成 langchain 工具
└── servers/       【公共】4 个 stdio MCP server（详见下文「外部工具层：MCP」）
    ├── web_search_mcp.py     联网搜索（360，免 key）
    ├── code_exec_mcp.py      本地 Python 沙箱（隔离子进程 + 超时）
    ├── github_resource_mcp.py Github 学习资源检索（搜仓库免 token / 搜代码需 GITHUB_TOKEN）
    └── cards_mcp.py          造卡能力封装（generate_card，不进每轮 QA）
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
    langgraph langchain langchain-ollama mcp
```

2026-09-29 装的版本：langgraph 1.2.12 / langchain 1.4.3 / langchain-core 1.6.5 /
langchain-ollama 1.1.0 / **mcp 1.30.0**（Python 3.10.11），顺带 30 多个间接依赖。

⚠️ **`mcp` 必须锁 1.x**：2.x 把 `FastMCP` 改名 `MCPServer`、server API 大改，装到 2.3.0 直接 import 报错。
本机已降到 `mcp==1.30.0`（最后一个 1.x，FastMCP 可用、client stable）；升级到 2.x 需重写 `servers/*.py` 端。

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

## 两个模式都流式（2026-10-08 改）

以前只有 react 流式，flow 走 `stream:false` 一次性等全文 —— 本地 8B 要
20~40 秒空白，用户盯着只能判断「坏了」。现在 flow 也流式。

**为什么原来做不到**：flow 的 answer 节点是 `M.chat().invoke()` 一次性返回；
而 LangGraph 节点函数**只能收到 state**，没法多传一个 `on_token` 参数。

```python
# nodes.py —— 用 ContextVar 绕过去（和 tools.set_current_user 同一套路）
_on_token = ContextVar('qa_on_token', default=None)

def answer(state):
    sink = _on_token.get()
    if sink is None:                      # 没装 → 老路径，行为完全不变
        return {'answer': M.chat().invoke(msgs).content, ...}
    buf = []
    for piece in M.chat().stream(msgs):
        buf.append(piece); sink(piece)
    return {'answer': ''.join(buf), ...} # state 仍等完整生成后才写
```

SSE 层用**后台线程生成 + 队列转发**（sink 是同步回调，里面不能 `yield`）。
实测 **444 帧正文、出字跨度 103.67s**（首帧 0.1s）。

★ **流式不改质检**：flow 也有 `grade` 自检，它拿到的仍是完整答案，
没过检照样重写一轮 —— 所以可能看到答案被覆盖重写，这是设计如此。

## 三个缓存（Redis，2026-10-08 新增）

| 文件 | 缓存什么 | 实测 |
|---|---|---|
| `qa/retr_cache.py` | 混合检索结果（只存 id+score） | 384ms → **63ms** |
| `qa/ans_cache.py` | 答案 | 103s → 命中毫秒级 |
| `verify/cache.py` | 校验结论 | 60s → 命中秒回 |

★ **动手前先测**：我原以为「复习队列」最值得缓存，实测 `due_list` 只要 **67ms**
（已有 SQL 快路径）—— 不值得。真正的大头是 `retrieval.retrieve()` 384ms。

**两条设计规矩**（细节见 docs/开发者文档.md 技术点 7）：

1. **失效靠内容指纹，不靠 TTL**。key 里带 `md5(影响该结果的字段内容)`：
   改了卡 → 指纹变 → 自动重算。「卡已改却拿到旧结论」比慢严重得多。
   检索用**全库指纹**（`level` 不进 —— 标卡不该让全库缓存作废）。
2. **缓存里只存「指向」不存「内容」**。检索只存 `id + score`，
   **card 本体每次现取** → 改卡立刻生效。

答案缓存**刻意保守**：有多轮历史一律不查（会答偏）；只写「检索没命中卡」的答案
（拿不到用了哪几张卡就构造不出正确指纹）—— 宁可不缓存。

开关：`RETR_CACHE=0` / `QA_CACHE=0` / `VERIFY_CACHE=0`。
状态在 `/api/health` 的 `cache.biz.{retr,qa,verify}`。

★ **写缓存不要裸 `except: pass`**：踩过 `SearchHit` 是 `__slots__` 对象、
没有 `.get()` → AttributeError 被吞掉 → **缓存从没写进去却完全静默**，
表现是「加了缓存但一点没变快」（实测 0.9x）。至少 `print(..., file=sys.stderr)`。

## 跑：卡片校验（verify/）

react 答完后核对**这次引用到的**前 2-3 张卡，有错就在聊天流里反问用户
「要不要按最新资料修正」。

```bash
cd E:\AAA_实验室项目\study\back_study
.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'core')
import db
from agent.verify import runtime as vr
cards = db.all_cards()[:2]
for r in vr.verify_cards(cards):
    print(r['card_id'], '→', r['proposed_patch'])
"
```

- **绝不自动改知识库**：只产出 `proposed_patch`，落库必须用户点确认
  （`POST /api/agent/verify/apply`）。自动改=「AI 偷偷改知识库」，错了难追溯。
- **修正内置卡用覆盖层**（`data/store/cards.override.json`），不动源码、可还原。
  最初实现成「复制成同 id 自定义卡」会**让内置卡凭空消失**——MySQL `cards` 表
  主键只有 `id`，`ON DUPLICATE KEY` 静默覆盖了内置卡行。

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

## 外部工具层：MCP（Model Context Protocol）

问答 Agent 从「只检索库内卡片」升级成「能调外部工具」——连 Github 拉学习资源、在本地沙箱跑代码、联网搜。
这是本项目从"只有一个 LangGraph"变成"完整 Agent"的关键。**可选旁支**：没装 `mcp` 包时这些工具自动降级。
（更细的桥接原理、踩坑见 `docs/学习路线.md` 第 6.1 节。）

### 怎么接

每个 MCP server 是一个独立的 stdio 子进程，走 JSON-RPC。桥接代码在 `mcp.py`：

- `stdio_client` 拉起子进程 → `initialize` 握手 → `list_tools` 拿清单
- 把每个工具包成 langchain `StructuredTool`（动态 pydantic schema：函数签名+类型提示→入参，docstring→描述）
- client 是 async、业务运行时是 sync，`mcp.py` 开一条后台线程挂事件循环，用 `run_coroutine_threadsafe` 适配
- **任一 server 起不来都只降级、不崩服务**（实测 github 搜仓库因网络/代理超时 → 返回中文说明、不抛）

server 清单开关在 `mcp_servers.json`（name / command / args / enabled）。

### 4 个 server

| server | 进每轮 QA？ | 干什么 | 文件 |
|---|---|---|---|
| `web-search` | ✅ | 360 搜索，免 key，失败返回空不抛 | `servers/web_search_mcp.py` |
| `code-exec` | ✅ | 本地 subprocess 跑 Python（超时 10s/上限 30s、输出截断 4k），演示/验证用 | `servers/code_exec_mcp.py` |
| `github-resource` | ✅ | 学生问知识点时，除卡片库外再拉 **Github 仓库（学习路线/roadmap）/ 代码示例**（搜仓库免 token；搜代码需 `GITHUB_TOKEN`） | `servers/github_resource_mcp.py` |
| `cards` | ❌ | 造卡能力的 MCP 封装（`generate_card`），**复用 cards Agent 造卡逻辑** | `servers/cards_mcp.py` |

### 工具预算（实测定的）

qwen3:8b 工具一多就选错。最终定调 **4 内部 + 3 MCP = 7 个**进每轮问答工具集
（`search_cards` / `card_detail` / `related_cards` / `due_today` + `web_search` / `run_python` / `github_search`）。
**`cards` server 刻意不进每轮 QA 列表**——它属"内容生产"重动作，改由导入流程 / 另一个 Agent 直接 import 调用。

### 坑

1. **`mcp` 2.x 把 `FastMCP` 改名 `MCPServer`、server API 大改**，装到 2.3.0 直接 import 报错，已降到 `mcp==1.30.0`（最后一个 1.x）。升级 2.x 需重写 `servers/*.py` 端。
2. **stdio server 的 stdout 只能有 JSON-RPC 报文**：框架默认把 "Processing request..." 打到 stdout 会污染流，server 端把 `mcp` logger 设为 WARNING。
3. **stdio server 里再 fork 子进程（code-exec 跑 Python），必须显式把 stdin 重定向成 `DEVNULL`**，否则子进程继承 JSON-RPC 的 stdin 管道在 Windows 下挂死（不是代码慢，是管道被占）。

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
