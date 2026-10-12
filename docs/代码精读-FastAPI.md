# FastAPI 逐行精读

> **这份文档解决什么**：你说「FastAPI 基础不牢固，怕看不懂代码」。
> 那这份文档就把项目里真实的代码**摊开，一行一行讲清楚**——
> 每行在干什么、**为什么这么写**、**换一种写法会怎样**。
>
> **不是** API 文档（那是 `/docs` Swagger 自己会生成的），
> **不是** 项目介绍（那是 README）。
> 这里只做一件事：**让你把代码读成「人话」**。
>
> **怎么用**：建议左边开着这份文档，右边开着对应的 `.py` 文件，
> 一行一行对着看。**每读懂一行再往下走**，别跳。
> 读不动的地方通常不是 FastAPI 的问题，是 Python 语法不熟——
> 那种地方我标了「这条是 Python 不是 FastAPI」。

---

## 目录（按这个顺序读，一次一节）

| 节 | 读什么 | 解决什么疑问 | 篇幅 |
|---|---|---|---|
| [§1](#1-先搞懂-5-个概念fastapi-到底在做什么) | 概念 | 「FastAPI 到底是什么？装饰器是什么？」 | 中 |
| [§2](#2-逐行读-runpy一个入口文件该有哪些东西) | `run.py` | 「程序从哪开始？第一行 import 干嘛的？」 | 短 |
| [§3](#3-逐行读-schemaspydantic-模型到底在干嘛) | `schemas.py` | 「请求体怎么被校验的？为什么字段名要写两遍？」 | 中 |
| [§4](#4-逐行读-depspy依赖注入是什么东西) | `deps.py` | 「`Depends(current_user)` 到底注入了什么？」 | 中 |
| [§5](#5-逐行读-learningpy一个端点从进来到返回) | `learning.py` | 「一个请求进来，经过了哪几层？`async`/`def` 差在哪？」 | **长（核心）** |
| [§6](#6-逐行读-mainpy装配层中间件与异常) | `main.py` | 「中间件是什么？异常怎么被翻译成 JSON？404 为什么能回落？」 | 长 |
| [§7](#7-把整条链路串一遍一个请求的完整一生) | 全串 | 「从前端点一下到数据落盘，完整走一遍」 | 中 |
| [§8](#8-你必须掌握的-8-个-fastapi-知识点) | 清单 | 「学完了要能答出这 8 个问题」 | 短 |

---

## 1. 先搞懂 5 个概念（FastAPI 到底在做什么）

在读代码前，先把 FastAPI 的本质说清楚。**这一节看不懂，后面全是空中楼阁。**

### 概念 1：FastAPI 本质是「一个会读你函数签名的 HTTP 服务器」

你平时写的：

```python
@app.get('/api/cards/{cid}')
def card_detail(cid: str):
    return db.card(cid)
```

这一行代码里发生了 4 件事：

1. **`@app.get('/api/cards/{cid}')`** —— 这叫**装饰器**（decorator）。
   它的意思是：「**把这个函数注册到 FastAPI 的路由表里**」。
   路由表就是一张对照表：`'/api/cards/{cid}' → 这个函数`。
   装饰器**不会删掉你的函数**，它只是「顺手把函数登记了一下」，
   登记完还把原函数返回给你，所以别的地方还能继续 `import` 它。

2. **`'/api/cards/{cid}'`** —— 这是**路径模板**。
   大括号里是**参数名**，不是字面量。
   假设有人请求 `/api/cards/java-hashmap`，
   FastAPI 会自动把 `java-hashmap` 这个字符串提取出来，
   **作为 `cid` 参数传给你的函数**。你不用自己从 URL 里切字符串。

3. **`cid: str`** —— 这是**类型标注**。FastAPI 靠它做两件事：
   - 生成 Swagger 文档（`/docs` 页面能填表单调接口）
   - **校验**：如果来的不是字符串（比如 `123`），直接返 422 错误，
     **你的函数根本不会被执行**。

4. **`return db.card(cid)`** —— 返回值会被 FastAPI **自动序列化成 JSON**。
   你不用 `json.dumps()`，不用设 `Content-Type`。

> ★ **一句话总结**：FastAPI = 读你的函数签名 → 建路由表 → 收到匹配的 HTTP 请求
> → 校验参数 → 调用你的函数 → 把返回值变成 JSON。
> **你的函数只关心业务，框架管 HTTP。**

### 概念 2：`Depends()` 是「参数注入」，本质是「这个参数由框架帮你算好传进来」

```python
def review_due(user=Depends(current_user)):
    ...
```

你可能会想：`user` 从哪来的？函数调用时没人传它啊。

答案是：**FastAPI 在调用你的函数之前，先把 `current_user()` 执行了，
把它的返回值塞给 `user`**。

```
HTTP 请求进来
  ↓
FastAPI 看到「这个函数要一个 user 参数，且标记了 Depends」
  ↓
先执行 current_user()  ← 这一步会读 Authorization 头、验 token
  ↓
把返回值赋给 user
  ↓
现在才真正调用 review_due(user=返回值)
```

`current_user()` 是个普通函数（见 `deps.py`），它读请求头里的 token，
验完返回一个 `{'id': ..., 'username': ...}` 的字典，或者验不过就抛 401。

**所以「依赖注入」这个名字的意思是**：
你声明「我要这个」，框架负责「怎么弄到给你」。

### 概念 3：`async def` vs `def` —— 本项目最关键的决策

FastAPI 有两种写函数的方式，**行为完全不同**：

| | `def`（同步） | `async def`（异步） |
|---|---|---|
| FastAPI 怎么处理 | 丢进**线程池**执行 | 在**事件循环**上直接 await |
| 适合什么 | **阻塞操作**（读文件、查数据库） | **高并发等待**（请求外部 AI、调网络） |
| 本项目用在哪 | 绝大多数端点（db 是同步 IO） | 只有 `/api/agent/*` |

**为什么这个区别这么重要**（这是本项目踩过的坑）：

- **事件循环**可以理解成一个「同时处理很多请求的厨师」。
  `async def` 的函数在厨师手里**执行时，这个厨师不能去干别的**。
- 如果你在 `async def` 里写了一个卡 3 秒的同步操作（读文件），
  **所有其他请求都被这 3 秒卡住了**——因为厨师被占用了。
- 反过来，`def` 会被丢到线程池，**占用的是别的工人**，厨师还能去处理下一个请求。

> ★ **本项目的规则**：
> `core/db.py` 是同步的文件/数据库 IO → 所以绝大多数端点写 `def`。
> `/api/agent/*` 要等本地大模型（几十秒）→ 写 `async def` + `asyncio.to_thread()`
> （把等待丢到线程池，不占事件循环）。
>
> **这不是「哪种更高级」，是「哪种不会把服务卡死」。**

### 概念 4：中间件（Middleware）= 「每个请求进出都要过的一道手续」

```python
@app.middleware('http')
async def guard(request, call_next):
    # ← 请求进来时先跑这里
    resp = await call_next(request)   # ← 这里才真正执行你的端点
    # ← 端点返回后再跑这里
    return resp
```

`call_next(request)` 相当于「**继续往下走，帮我执行后面的端点**」。
中间件就是在这前后加逻辑——本项目用来：
- 进：拦超大请求体（>16MB 直接 413 拒掉）
- 出：给所有 API 响应加 `Cache-Control: no-store`

**为什么写在 `main.py` 而不是每个端点里**：
因为「每个请求都要加」的事，如果每个端点各写一遍，就是几十份重复代码。
中间件写一次，全站生效。

### 概念 5：应用装配 = 「把所有零件挂到这个车上」

`main.py` 干的事，通俗说就三件：
1. **造一个 app**：这是「应用」本身，是个空车
2. **装零件**：CORS 中间件、异常处理器、各个路由、静态文件目录
3. **定规矩**：请求体上限、错误怎么翻译成 JSON、404 怎么回落

**FastAPI 的注册顺序有意义**（本项目踩过）：
静态资源必须**最后**挂载，因为它挂在 `/` 上，能匹配一切。
挂早了会把 `/api/*` 也当成静态文件吃掉。

---

## 2. 逐行读 `run.py`：一个入口文件该有哪些东西

这是整个后端的第一行代码。先把它读透，你对「Python 程序怎么启动」就通了。

```python
import os
import sys
```

> ★ **这是 Python，不是 FastAPI**。
> `import` 就是「把某个模块的功能拿进当前文件用」。
> `os` = 操作系统相关（路径、环境变量），`sys` = Python 自身相关（路径搜索、退出码）。

```python
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
```

**逐行拆**：
- `__file__` —— Python 内置变量，**当前文件自己的路径字符串**。比如 `E:/.../back_study/run.py`
- `os.path.abspath(...)` —— 把路径转成**绝对路径**（纯字符串运算，不读文件）
- `os.path.dirname(...)` —— **截掉最后一段文件名**，只留目录：`E:/.../back_study`

**这三行合起来在干嘛**：
把「我自己在哪个目录」加进 `sys.path`（Python 搜索模块时会看的目录列表）。

**为什么必须做**：
项目里的 `import db`、`import llm` 不是全限定名（不是 `from core import db`），
Python 靠 `sys.path` 去找 `db.py`。不加这一句，
你在项目根目录跑 `python back_study/run.py` 会报 `ModuleNotFoundError: No module named 'db'`。
> 这也是为什么上面那些 `import db` 前面要加 `# noqa: E402`
> （E402 =「import 不在文件顶部」，因为上面插了代码，lint 会报，加 noqa 静音）。

```python
if os.getcwd() != HERE:
    os.chdir(HERE)
```

**在干什么**：把「当前工作目录」切到 `back_study/`。

**`cwd` vs `__file__` 的区别**（容易混）：
- `os.getcwd()` = 你**人在哪个目录**（你 `cd` 到哪就是哪）
- `__file__` = **这个脚本文件在哪**（跟着文件走，不受 `cd` 影响）

**为什么要切**：`--reload` 模式会另起子进程，
子进程靠「当前目录」去找 `app.main`，目录不对就起不来。

```python
def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    except Exception:
        pass
```

**在干什么**：把标准输出改成 UTF-8 且**行缓冲**（写一行就立刻显示，不攒着）。

**为什么**：`line_buffering=True` —— 启动时打印的那几行横幅是排查
「服务到底起没起」的第一手信息。如果输出重定向到文件，
Python 默认攒满缓冲区才写，你盯着空文件以为服务挂了，其实它早打印了。

```python
lan = '--lan' in argv
reload_ = '--reload' in argv
port = 8080
for a in argv:
    if a.isdigit():
        port = int(a)
```

**在干什么**：解析命令行参数。`argv` 是你敲的命令后面那些词
（`sys.argv[1:]` 切掉了第 0 个——脚本自己）。
比如你跑 `python run.py 8099 --lan`，`argv` 就是 `['8099', '--lan']`。

- `'--lan' in argv` = 列表里有没有这个字符串 → 有就 `True`
- `a.isdigit()` = 这个字符串是不是纯数字 → 是就当端口号

```python
try:
    import uvicorn
except ImportError:
    print('缺依赖：FastAPI / uvicorn / PyJWT 还没装。')
    return 1
```

**在干什么**：检查依赖装了没。

**★ 这里体现一种项目一贯的思路**（值得学）：
**错误要给人「人话」和「怎么办」，不是抛个栈让人自己查**。
它不只说「ImportError」，还告诉你「装哪条命令」和「为什么以前不需要装」。

```python
os.environ['CARDS_PORT'] = str(port)
os.environ['CARDS_LAN'] = '1' if lan else '0'
```

**在干什么**：把命令行参数**通过环境变量**传给 `app/main.py`。

**★ 为什么绕一道环境变量，不直接当参数传过去**：
因为 `--reload` 会重启子进程，**函数参数传不进新进程，但环境变量会**。
这是「跨进程通信」的经典做法。

```python
uvicorn.run('app.main:app', host=..., port=port, ...)
```

**'app.main:app' 是字符串不是对象** —— 这是 uvicorn 的特殊语法，
意思是「去 `app/main.py` 里找名叫 `app` 的变量」。
用字符串而不是对象，也是为了 `--reload` 能重新加载。

**`host='0.0.0.0'` vs `'127.0.0.1'`**（你手机要连电脑时会用到）：
- `127.0.0.1` = 只允许本机访问，外部访问不到
- `0.0.0.0` = 监听所有网卡，手机同 WiFi 就能连 ← `--lan` 就是开这个

---

## 3. 逐行读 `schemas.py`：Pydantic 模型到底在干嘛

你现在可能对「请求体」这件事有疑问：前端 POST 一个 JSON 过来，
**后端怎么知道里面有哪些字段、类型对不对**？答案就是 Pydantic 模型。

```python
from pydantic import BaseModel, ConfigDict, Field

class ProgressIn(BaseModel):
    level: int = Field(..., description='1 = 不会，2 = 模糊，3 = 会')
```

**逐行拆**：
- `class ProgressIn(BaseModel)` —— 定义一个类，**继承** `BaseModel`。
  **继承** =「白拿 BaseModel 的全部能力」，我们只加自己的字段。
- `level: int` —— 一个叫 `level` 的字段，类型是整数。
- `Field(..., description='...')` —— 三个点 `...` 是「**必填**」的意思
  （Pydantic 里的省略号表示「这里有个默认值，但它是空的→必须有值」）。
  `description` 会显示在 Swagger 文档里。

**它带来的三个效果**：
1. **校验**：前端传 `{"level": 5}` → FastAPI 自动返 422，**你的函数根本不会执行**
2. **转换/强类型**：`{"level": 3}` → 你拿到的 `body.level` 是**整数 3**，不是字符串 `"3"`
3. **文档**：自动出现在 `/docs`

```python
class Loose(BaseModel):
    model_config = ConfigDict(extra='allow')

class CardIn(Loose):
    title: Optional[str] = None
    # ... 20 个字段
```

- `class Loose(BaseModel)` —— 先定义一个「宽松基类」。**继承**它就等于
  「我也是一个 BaseModel，但我允许额外字段」。
- `ConfigDict(extra='allow')` —— **收到请求里我没定义的字段，也照样留着不扔**。

**★ 为什么这个项目要「宽松」**（文件里的注释解释了）：
卡片身上有一批内部字段（`_custom`、`_draft`、`_from`）是数据层自己维护的。
如果用严格模型（Pydantic 默认会**扔掉**未声明的字段），
这些内部字段会被**悄悄吃掉**——那才是真的破坏契约。

- `Optional[str] = None` —— 「这个字段可以不填，不填就是 `None`」。
  `Optional[X]` 就是「可以是 X，也可以是 None」。
- `List[str]` —— 字符串列表。`Dict[str, Any]` —— 「键是字符串、值什么都行」的字典。

**`Field(..., max_length=100)` 那个 `PickIn`** —— 上限 100 个 id。
这就是「用模型做业务限制」的例子。

> ★ **关键理解**：`schemas.py` 只管「**类型对不对、参数缺没缺**」，
> **不管业务规不合法**（比如「scene 至少 2 条」）。
> 业务校验的真相在 `core/importer.py:validate()`。
> **分工**：schema 管形状，业务管规矩。

---

## 4. 逐行读 `deps.py`：依赖注入是什么东西

这个文件只有 40 行，但它支撑了全站的登录鉴权。

```python
def token_from_header(authorization):
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    return parts[1].strip() or None
```

**逐行拆**：
- 这个函数**不是端点**，是普通工具函数。参数 `authorization` 是
  「传进来一个请求头字符串」，所以外面调用时要先拿到那个字符串。
- `if not authorization: return None` —— 没传（空/None）就返回 None。
  > ★ **`not x` 是「x 为假」**：None、空字符串 `''`、0、空列表都算假。
  > 这是 Python 的真假判断规则（叫**真值性**）：**空的都是假的，其余都是真的**。
- `authorization.split(None, 1)` —— 按空白切一刀，**最多切 1 刀**。
  `"Bearer abc123"` → `['Bearer', 'abc123']`。
  第一个 `None` 表示「按任意空白切」，比写 `' '` 强（多个空格也能切对）；
  第二个 `1` 是「最多切 1 刀」。
- `len(parts) != 2 or parts[0].lower() != 'bearer'` —— 两个条件任一成立就返回 None：
  要么切出来不是 2 段（格式不对），要么第一段不是 `bearer`（不是 Bearer 格式）。
- `.lower() != 'bearer'` —— 小写比较，所以 `Bearer` / `bearer` / `BEARER` 都认。
- `.strip() or None` —— 去空白后如果是空字符串，返回 None（「什么都没有」）。

**★ 为什么格式不对返回 `None` 而不是抛异常**：
因为「没有 token / token 格式不对」是**正常情况**（没登录嘛），不是错误。
抛异常会让上层不得不处理一堆「其实很正常」的情况。

```python
def current_user(authorization: str = Header(None)):
    """必须登录。没登录 / token 过期一律 **401**。"""
    token = token_from_header(authorization)
    payload = (security.read_token(token, security.get_secret())
               if token else None)
    if not payload:
        raise HTTPException(401, '未登录或登录已过期')

    u = db.user_get(payload.get('sub'))
    if not u:
        # 签名有效但账号已被删。当未登录处理，别放进去
        raise HTTPException(401, '账号不存在')
    return db.public_user(u)
```

**这就是 §1 概念 2 说的那个 `current_user`**。FastAPI 会在调用
任何带 `Depends(current_user)` 的端点前，**先执行这个函数**。

**逐行拆**：
- `authorization: str = Header(None)` —— `Header(None)` 告诉 FastAPI：
  「这个参数从 HTTP **请求头** `Authorization` 里取，默认值 None」。
  > ★ **`Header` 和 `Query` 的区别**：
  > `Query` 从 URL 的 `?x=1` 取；`Header` 从请求头取；
  > `Path` 从 URL 路径的 `{cid}` 取（但路径参数通常直接写 `cid: str`，不用写 `Path`）。
- `security.read_token(token, secret)` —— 验 JWT 签名，看能不能解出用户信息。
  **解不开（签名不对/过期）就返回 falsy**。
- `payload.get('sub')` —— JWT 里存用户 id 的字段叫 `sub`
  （subject 缩写，JWT 标准约定）。`sub` 是标准字段名，不是这个项目随便起的。
- `db.user_get(...)` —— 去数据库查这个用户还在不在。
- `db.public_user(u)` —— **脱敏**！把密码哈希之类去掉再返回。

**★ 为什么用 401 不用 403**（注释解释了，很实际）：
前端 `api/client.js` 只对 401 做「清 token + 跳登录页」。
如果返 403，前端会当成普通错误弹个 toast，
用户就**卡在当前页面反复点**，不知道自己已经掉线了。

**★ 为什么末尾必须 `public_user()` 而不是 `return u`**：
如果你直接返回数据库原始行 `u`，里面可能有 `password_hash`。
一 JSON 序列化发给前端，用户在浏览器 F12 里就能看到密码哈希。
> **凡是个人数据出口，先想「这是不是个人数据」。**
> 这跟 §5 讲的「`OVERDUE_NEVER` 翻译成 None」是同一个思想：
> **内部状态和对外契约要分离。**

---

## 5. 逐行读 `learning.py`：一个端点从进来到返回 ★核心

这一节最长，但**最重要**——读透这一节，你就能独立读项目里任何端点。
我们读三个函数：一个最简单的（`get_progress`）、
一个带请求体的（`set_progress`）、一个参数最多的（`review_due`）。

### 5.1 文件顶部的三行「装配」

```python
from fastapi import APIRouter, Depends, HTTPException, Query
import db
from ...deps import current_user
from ...schemas import PickIn, ProgressIn

router = APIRouter(prefix='/api', tags=['学习'])
```

**逐行拆**：
- `APIRouter` —— **路由的「小分组」**。可以把一堆相关端点装进一个 router，
  最后统一注册到 app 上。为什么不直接用 `@app.get`？
  因为端点一多，几十个 `@app.get` 散在各处不好管；
  按业务域分组（learning / cards / docs…）更清晰。
- `prefix='/api'` —— **这个 router 里所有端点的公共前缀**。
  后面写 `@router.get('/progress')`，实际路径是 `/api/progress`。
  **省得每个端点都重复写 `/api`**。
- `tags=['学习']` —— **Swagger 文档里的分组名**。
  打开 `/docs` 会看到「学习」这个折叠面板，把复习/进度相关端点收在一起。
- `from ...deps import current_user` —— **三个点**是「往上三级」。
  当前文件是 `app/routers/web/learning.py`，
  `.` = `app/routers/web/`，`..` = `app/routers/`，
  `...` = `app/`。所以 `...deps` = `app/deps.py`。
  > ★ **这是 Python 不是 FastAPI**。数点数的规则：从**当前包**往上数，
  > 一个点是当前目录，两个点是上一层。
- `HTTPException` —— **主动抛错用的**。`raise HTTPException(400, 'msg')`。
- `Query` —— 声明「这个参数从 **URL 查询串** 来」（`?limit=50` 这种）。

**★ 记住一条**：`main.py` 里 `for _r in ROUTERS: app.include_router(_r)`，
所以这里 `prefix='/api'` 会自动生效，不用手动拼。

### 5.2 最简单的端点（GET，返回数据）

```python
@router.get('/progress', summary='全部进度')
def get_progress(user=Depends(current_user)):
    return {'ok': True, 'progress': db.get_progress(user.get('id'))}
```

**逐行拆**：
- `@router.get('/progress', summary='全部进度')` —— 装饰器。
  `summary` 是 Swagger 文档里显示的一句话说明。
- `def get_progress(...)` —— **注意写的是 `def` 不是 `async def`**。
  **因为** `db.get_progress()` 是读 JSON/数据库的**同步阻塞 IO**。
  （回到 §1 概念 3：写 `async def` 会把整个事件循环卡住，一个请求卡死所有人。）
- `user=Depends(current_user)` —— **依赖注入**。
  框架在调用 `get_progress` 之前会先执行 `current_user()`，
  把返回值塞给 `user`。验不过它直接抛 401，**你的函数根本不会跑**。
- `user.get('id')` —— **从字典取值**。`current_user()` 返回的是
  `{'id': 123, 'username': 'xxx', ...}`，`.get('id')` 取出 `123`。
  用 `.get()` 而不是 `['id']` 是**防御性写法**：键不存在时返回 `None` 而不是崩。
- `return {'ok': True, 'progress': ...}` —— 返回一个 **Python 字典**。
  FastAPI 看到 dict，会**自动**转成 JSON。所以你**不用**写
  `json.dumps()`，也**不用**设 `Content-Type`。
  最终响应体是 `{"ok": true, "progress": {...}}`。

> ★ **全项目的统一返回约定**：成功返 `{'ok': True, ...}`。
> 失败返 `{'ok': False, 'msg': '人话原因'}`。
> 前端所有分支都读 `ok` 和 `msg`。**这是契约，破坏它前端就崩。**

### 5.3 带请求体的端点（PUT）—— 你会卡住的地方

```python
@router.put('/progress/{cid}', summary='标记某张卡的掌握程度')
def set_progress(cid: str, body: ProgressIn, user=Depends(current_user)):
```

这行函数签名有**三个参数**，来源完全不同——这是最容易懵的地方，做个表：

| 参数 | 从哪来 | FastAPI 怎么拿到的 |
|---|---|---|
| `cid` | **URL 路径**：`/api/progress/java-hashmap` | 从 `'{cid}'` 大括号里提取，自动变成字符串 |
| `body` | **请求体**：前端 POST 的 JSON `{level: 3}` | 按 `ProgressIn` 模型校验后传进来 |
| `user` | **登录态** | `Depends(current_user)` 主动执行注入的 |

**★ 一个关键点：参数名 `body` 是你自己起的**，
FastAPI 只看**类型标注** `ProgressIn` 就知道「哦，这是从请求体里按这个模型解析」。

**继续往下读**：

```python
    if body.level not in (1, 2, 3):
        raise HTTPException(400, _LEVEL_HINT)
```

- `body.level` —— 前端传了 `{"level": 3}`，经过 `ProgressIn` 校验后，
  你拿到的 `body` 是一个 **`ProgressIn` 类型的对象**（不是字典了！），
  `.level` 是**整数 3**。所以能直接 `3 in (1,2,3)` 判断。
  > ★ **注意**：因为是模型对象，`body.level` 用**点**取；
  > 如果 `body` 是字典，就得写 `body['level']`。
- `not in (1, 2, 3)` —— Python 元组 `(1,2,3)` 是「一个装了三个数的集合」。
- `raise HTTPException(400, _LEVEL_HINT)` —— 主动抛错。
  `400` 是 HTTP 状态码（Bad Request），`_LEVEL_HINT` 是给用户看的人话。
  **抛异常后，函数立刻停止**，后面的代码不执行。

> ★ **★ 这个项目有个「故意反 FastAPI 默认」的地方，务必看懂**：
> 上面明明可以用 Pydantic 的 `Field(ge=1, le=3)` 让框架自动校验，
> 但它**故意不这么做**，改成手动判断再抛 400。为什么？
> 因为用 `Field(ge=1,le=3)`，FastAPI 校验不过会返 **422**；
> 而这个项目的旧前端到处写 `if (status === 400)`，
> 返 422 会**静默走进「服务器错误」分支**，错误信息全丢。
> **校验方式可以换，但对外的状态码不能换。** 这是「接口契约」意识。

```python
    rec = db.set_level(cid, body.level, user_id=user.get('id'))
    return {'ok': True, 'id': cid, 'progress': rec}
```

- 调业务层，把结果和参数一起返回。
- `user_id=user.get('id')` —— **命名参数**（带等号），明确告诉 Python
  「这个值给 `user_id` 这个参数」。不能写成 `user.get('id')` 裸在中间。

### 5.4 参数最多的端点（`review_due`）—— 查询参数怎么声明

这是全项目参数最多的端点，逐个拆：

```python
@router.get('/review/due', summary='今日复习队列')
def review_due(limit: int = Query(50, ge=1, le=500),
               domain: Optional[str] = Query(None),
               dirs: Optional[str] = Query(
                   None, description='学习方向 id，逗号分隔...'),
               include_all: str = Query('', alias='all',
                                        description='=1 时把没到期的也带上'),
               pick: str = Query('',
                                 description='=1 时只回今日自选清单里的卡'),
               by: str = Query('level',
                               description='level=按自评档位排 | bkt=按 BKT 掌握度排'),
               user=Depends(current_user)):
```

**先讲 `Query(...)` 是什么**：
它告诉 FastAPI「这个参数从 **URL 的 `?` 后面** 来」。
请求 `/api/review/due?limit=100&by=bkt` →
`limit` 拿到 `100`，`by` 拿到 `'bkt'`。

**`Query(50, ge=1, le=500)` 四个部分**：

| 部分 | 意思 |
|---|---|
| `50` | **默认值**：不传就用 50 |
| `ge=1` | greater-equal，**大于等于** 1 |
| `le=500` | less-equal，**小于等于** 500 |
| （不传） | **必填**（有默认值就可省） |

**★ 这里的 `ge/le` 就是「参数校验」**：
如果前端传 `?limit=9999`，FastAPI **自动返 422**，
`review_due` 函数根本不会执行——省了一次可能拖垮服务的全库查询。

**`Optional[str] = Query(None)`** —— 「可以不传，不传是 `None`」。

**★ `alias='all'` 这个细节很实战**：
Python 里 `all` 是**内置函数名**（判断「是否全为真」）。
如果参数也叫 `all` 会覆盖内置函数（在函数体内就不能用 `all()` 了）。
`alias='all'` 的意思是：**对外（URL 里）叫 `all`，但函数内变量叫 `include_all`**。
> 前端请求还是 `?all=1`，但后端代码里用的是 `include_all`——
> **对外契约和内部命名解耦**，两边都不用将就。

**`by: str = Query('level', description='...')`** —— 默认值是字符串 `'level'`。

**现在读函数体**（这个函数体里有**两个极重要的顺序陷阱**）：

```python
    if pick == '1':
        ids = set(db.get_today_pick(user.get('id')))
        items = [x for x in db.due_list(include_all=True, user_id=user.get('id'))
                 if x['card']['id'] in ids]
```

- `set(...)` —— 转成集合。**为什么**？因为下一步用 `in ids` 判断「在不在」。
  **列表的 `in` 是逐个比对（O(n)），集合是哈希查找（O(1)）**。
  几百张卡时差别不大，但这是「选对数据结构」的好例子。
- `[x for x in ... if ...]` —— **列表推导式**，Python 的经典写法，等价于：
  ```python
  items = []
  for x in db.due_list(...):
      if x['card']['id'] in ids:
          items.append(x)
  ```
  但写得紧凑。> ★ **这是 Python 不是 FastAPI**。

**下面这段是全项目最值钱的注释之一**（`else` 分支）：

```python
    else:
        items = db.due_list(domain=domain or None, include_all=(include_all == '1'),
                           user_id=user.get('id'))
        if dirs:
            kws = db.direction_kws([d.strip() for d in dirs.split(',') if d.strip()])
            if kws:
                items = [x for x in items if db.card_hit(x['card'], kws)]
```

- `include_all == '1'` —— 这是个**字符串比较**，不是布尔。
  为什么 `all` 是字符串？因为前端可能传 `?all=true` 或 `?all=1`，
  统一用字符串 `'1'` 判断最简单。
- `[d.strip() for d in dirs.split(',') if d.strip()]` —— 处理 `?dirs=ai,java` 这种
  逗号分隔的值：按逗号切 → 每段去空格 → 丢掉空段。

**★★ 陷阱一：筛选必须在截断之前**
```python
    if by == 'bkt':
        items = db.sort_by_mastery(items, user.get('id'))
    items = items[:limit]        # ← 截断在最后
```
注释原话：「BKT 优先级排序必须在截断**之前**。
否则只对『已经取到的前 limit 张』排序，等于没排——
真正掌握度低的卡**已经被 limit 截掉了**。」

- `items[:limit]` —— Python 的**切片**，`[:50]` = 「取前 50 个」。
  （`[:n]` 是「到 n 为止」，不写结尾就是「到末尾」。）

> ★ **这类 bug 最可怕的地方在于「不报错」**：
> 程序正常运行、返回 200、只是结果不对。
> **顺序放反了，功能看起来是好的，只是少了个排序。**
> 读代码时看到「先筛选后截断」这类逻辑，要立刻问：
> 「反过来会怎样？」

**然后构造返回数据**：

```python
    queue = [{'id': x['card']['id'], 'title': x['card'].get('title'),
              ...
              'overdue': None if x['overdue'] == db.OVERDUE_NEVER else x['overdue']}
             for x in items]
```

- 这是**「字典字面量 + 列表推导式」的组合**：对每个 `x` 造一个新字典。
- `x['card']['id']` —— 直接下标，**因为一定存在**（一定有 id）。
- `x['card'].get('title')` —— 用 `.get()`，**因为 title 可能没有**。
  > ★ **什么时候用 `['k']`、什么时候用 `.get('k')`**：
  > 「**一定有**」用 `['k']`（没有就崩，崩了说明数据不对，要暴露）；
  > 「**可能没有**」用 `.get('k')`（没有给 `None`，别让整个请求挂掉）。
- `None if x['overdue'] == db.OVERDUE_NEVER else x['overdue']` ——
  **把内部哨兵值翻译成前端能懂的 `None`**。
  > ★ **「内部状态」和「对外契约」要分离**。
  > db 层用 `999` 表示「从没复习过」（因为要做排序，不能用 None）；
  > 但前端看到 `999` 会以为是「逾期 999 天」，所以出口翻译成 `null`。
  > **而且用常量 `db.OVERDUE_NEVER` 而不是写死 999**——因为这个值改过一次，
  > 写死就会漏（注释里明说了）。

**最后补 BKT 的 p 值**：

```python
    if by == 'bkt':
        for row, x in zip(queue, items):
            row['p'] = x.get('p')
```

- `zip(a, b)` —— **把两个列表按位置配对**。
  `queue` 是刚造好的，`items` 是原始数据，两个一一对应，
  `zip` 让你能同时遍历它们，把 p 值贴回对应的那一行。

> ★ **`zip` 的坑**：长度不等时它**按最短的截断**，静默丢掉多余的。
> 这里的 `queue` 和 `items` 是 1:1（queue 正是由 items 造出来的），所以安全。

```python
    return {'ok': True, 'today': db.today_str(), 'total': len(items), 'queue': queue}
```

**★ 为什么 `total` 用 `len(items)` 而不是 `len(queue)`**：
它们数值相同，但**含义不同**。`total` 是「今天有多少张到期」——
一个给用户看的数字，即使前端只 `limit=20` 显示 20 张，
`total` 也告诉用户「其实有 300 张」。这个数字必须算在截断**之前**。

### 5.5 读到这里，你应该能回答这几个问题

1. `cid`、`body`、`user` 三个参数分别从哪来？（§5.3 的表）
2. 为什么这个项目的端点大多写 `def` 而不是 `async def`？
3. `Query(50, ge=1, le=500)` 里三个部分各是什么作用？
4. 为什么 `alias='all'` 要给参数改名？
5. 「筛选必须在截断之前」——反过来会出什么症状？
6. `x['card']['id']` 和 `x['card'].get('title')` 为什么写法不一样？

---

## 6. 逐行读 `main.py`：装配层、中间件与异常

`main.py` 不含业务，它做的是**把零件装到车上，并定三条规矩**：
请求体多大、报错怎么翻译、404 怎么回落。

### 6.1 造 app：这一步之后才开始有「服务」

```python
app = FastAPI(
    title=API_TITLE,        # Swagger 页面顶部的大标题
    version=API_VERSION,
    description=API_DESC,   # Markdown 描述
    openapi_tags=OPENAPI_TAGS,   # Swagger 左侧的分组顺序
    lifespan=lifespan,      # ★ 启动/关闭钩子
)
```

**★ `lifespan` 值得单独说**（很多人第一次见）：

```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.ensure_store()      # ← 启动时跑：确保存储可用
    _banner()              # ← 打印启动横幅
    yield                  # ← 这里「悬着」，服务运行中
    # ← 服务关闭时跑（这里没写清理代码）
```

`@asynccontextmanager` 把一个「有 yield 的 async 函数」变成上下文管理器。
FastAPI 会这样用它：

1. **服务启动时**，执行 `yield` **之前**的部分 → 初始化存储、打印横幅
2. **服务运行中**，`yield` 挂在那里
3. **服务关闭时**，执行 `yield` **之后**的部分 → 清理资源

> ★ **为什么这套逻辑要放 `lifespan` 而不是「每个请求都做一遍」**：
> 「确保存储可用」是一次性的启动工作，不是每个请求都要做。
> 放这里 = 启动时做一次，之后所有请求直接用。
> **这是「把不重复的事做一次」的最典型位置。**

### 6.2 中间件：每个请求进出都要过的两道手续

```python
@app.middleware('http')
async def guard_log_cache(request: Request, call_next):
```

`@app.middleware('http')` 是**另一种装饰器**，作用是「把这个函数变成中间件」。

**中间件的执行顺序**（重要）：

```
请求进来
  ↓
① guard_log_cache  的「进来」部分     ← 检查请求体大小
  ↓
② 路由匹配（找到 @router.get 那个函数）
  ↓
③ 你的端点函数执行
  ↓
④ guard_log_cache  的「出去」部分     ← 加缓存头、记日志
  ↓
响应返回
```

**逐行读这个中间件的三个动作**：

```python
    n = request.headers.get('content-length')
    if n and n.isdigit() and int(n) > MAX_BODY:
        return JSONResponse(status_code=413, content={...})
```

- `request.headers.get('content-length')` —— **取请求头**。
  Content-Length 是客户端「告诉服务器我这个请求体多大」的数字。
- `n and n.isdigit() and int(n) > MAX_BODY` —— 三个条件用 `and` 串起来，
  **全部为真**才进入。`n.isdigit()` 是防「客户端发了非数字」。

**★ 为什么还要第二道（数实际字节）**（注释里的坑，很典型）：

```python
    seen = {'n': 0}
    original_receive = request._receive

    async def counting_receive():
        msg = await original_receive()
        if msg.get('type') == 'http.request':
            seen['n'] += len(msg.get('body') or b'')
            if seen['n'] > MAX_BODY:
                raise _BodyTooLarge()
        return msg

    request._receive = counting_receive
```

**问题**：有些请求用 `Transfer-Encoding: chunked`（分块传输），
**这种请求根本没有 Content-Length 头**！第一道闸门直接放行，
FastAPI 会把整个 body 缓冲进内存 → 16MB 上限形同虚设。

**解法**：**把底层的「收数据」函数换掉**，改成边收边数。
`request._receive` 是 FastAPI/Starlette 内部用来收数据的函数，
我们替换成 `counting_receive`，在真正读数据的时候顺便累计字节数。

> ★ **★ 这里体现一种特别值得学的思路**：
> 「限制大小」这件事，**光检查声明的值是不够的**——
> 声明可以被骗（或者干脆没有），**要数真正收到的东西**。
> 这个思路在你做任何「配额/限流」时都会用到。

**出去的部分**：

```python
    resp = await call_next(request)
    ...
    if is_api:
        resp.headers['Cache-Control'] = 'no-store'
        sys.stderr.write('%s %s → %d  %.0fms\n' % (...))
    else:
        resp.headers.setdefault('Cache-Control', 'no-cache')
    return resp
```

- `resp.headers['Cache-Control'] = 'no-store'` —— 给响应加头。
  `no-store` = 浏览器**不许缓存**。
  > ★ **为什么进度/笔记接口必须 no-store**（注释解释了）：
  > 否则你标记了「会」，刷新一下页面又变回原样，
  > 用户会以为数据丢了——其实是浏览器给了缓存。
- `setdefault(...)` —— 「**没有才设**」。`setdefault` 的意思是
  「如果这个键不存在才设置，已存在就保留」。
  （`no-cache` 只对 `sw.js` 用——Service Worker 必须每次都去服务器问，
  否则版本更新推不下去。）

### 6.3 异常处理器：把所有错误翻译成前端认识的形状

**FastAPI 默认的错误格式**前端不认识：

```json
{"detail": [{"loc": ["body", "level"], "msg": "value is not a valid integer"}]}
```

而前端所有分支都读 `body.msg`。所以要统一翻译。

```python
@app.exception_handler(StarletteHTTPException)
async def on_http_error(_request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code,
                        content={'ok': False, 'msg': str(exc.detail)})
```

**逐行拆**：
- `@app.exception_handler(某个异常类型)` —— 装饰器：
  「**捕获这类异常**，统一交给这个函数处理」。
- `StarletteHTTPException` —— **FastAPI 的底层框架 Starlette 的异常类**。
  你 `raise HTTPException(400, '...')` 抛的，最终就变成它。
  （FastAPI 的 `HTTPException` 是 Starlette 版的子类。）
- `exc.status_code` —— 原始的状态码，**原样保留**（400 还是 400，不改）。
- `str(exc.detail)` —— 把异常里带的「人话原因」取出来。

> ★ **关键理解：装饰器「不改返回值，只改错误的形状」。**
> 正常返回的 JSON 一个字都不动，只有**抛异常**的那些才走这几个 handler。

**参数校验错误（422 → 400）**：

```python
@app.exception_handler(RequestValidationError)
async def on_bad_params(_request, exc):
    errs = exc.errors()
    if errs and errs[0].get('type') == 'json_invalid':
        return JSONResponse(status_code=400,
                            content={'ok': False, 'msg': '请求体不是合法 JSON'})
    detail = '参数不合法'
    if errs:
        first = errs[0]
        name = '.'.join(str(x) for x in first.get('loc', ())
                       if isinstance(x, str) and x not in ('body', 'query', 'path'))
        msg = first.get('msg') or detail
        detail = ('%s: %s' % (name, msg)) if name else msg
    return JSONResponse(status_code=400, content={'ok': False, 'msg': detail})
```

- `exc.errors()` —— 拿到**错误明细列表**，每条有 `type` / `loc` / `msg`。
  `loc` 形如 `('body', 'level')`——**第 0 项是位置**（body/query/path），
  **后面才是字段名**。
- `if ... type == 'json_invalid'` —— 单独处理「你发的根本不是合法 JSON」。
  > ★ **为什么要单独处理**：Pydantic 的原话是 `JSON decode error`，
  > 直接弹给用户太出戏。这里换成中文人话。
- 那段 `name = '.'.join(...)` 是**过滤掉 `body`/`query`/`path` 这些位置词**，
  只留真正的字段名。`loc = ('body', 'level')` → 提取出 `"level"` →
  最终 msg 是 `level: value is not a valid integer`。

**★ 为什么要把 422 改成 400**（注释里写了原因）：
FastAPI 默认参数不对返 **422**，而老前端到处写 `if (status === 400)`。
返 422 会**静默走进「服务器错误」分支**，错误信息就丢了。
> **这就是「对外契约不能随便改」**——同一个含义的状态码，
> 对前端来说不是「差不多」，是「另一个分支」。

### 6.4 静态挂载：为什么必须最后

```python
_data_mount = GuardedStatic(directory=DATA_DIR, html=False)
_data_mount.deny = ('store/',)
app.mount('/data', _data_mount, name='data')     # ← 先挂这个

_web_mount = SpaStatic(directory=STATIC_DIR, html=True)
_web_mount.deny = ()
app.mount('/', _web_mount, name='static')        # ← 最后挂 '/'，吃掉一切
```

**★ 为什么 `app.mount('/', ...)` 必须放最后**（这是本项目踩过的坑）：
`/` 是「**任何路径**」的意思。Starlette **按注册顺序**匹配路由，
所以 `/` 一旦先注册，**它会把后面所有的 `/api/xxx` 都当成静态文件**处理——
API 就全废了。

**`SpaStatic` 类（单页应用回落）**——这是前端路由的必需品：

```python
class SpaStatic(GuardedStatic):
    async def get_response(self, path: str, scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as e:
            if e.status_code != 404:
                raise
        except OSError:
            ...
            raise StarletteHTTPException(404)
        # 只有「前端路由」才回落成 index.html
        if rel == 'api' or rel.startswith('api/') or os.path.splitext(rel)[1]:
            raise StarletteHTTPException(404)
        try:
            return await super().get_response('index.html', scope)
        except StarletteHTTPException:
            raise StarletteHTTPException(404)
```

**★ 这段代码要理解的是「为什么需要它」**：
Vue 用 **history 模式**做路由，网址是 `/cards`、`/login`——
**但服务器磁盘上根本没有 `/cards` 这个文件**（只有 `index.html`）！
默认的 StaticFiles 见到 `/cards` 找不到文件，直接 404，
用户**手一刷新就白屏**（他刚从这一页点进去过）。

所以必须：**找不到文件时，回落成 `index.html`**，
让前端的 Vue Router 去解析这个路径，渲染对应页面。

**★ 这里有个特别隐蔽的坑，注释里明写了**（值得你特别注意）：

> StaticFiles 表达 404 的方式是**抛 HTTPException**，
> 不是返回一个状态码为 404 的 Response。
> 所以这里必须 try/except —— 写成
> `resp = await super().get_response(...); if resp.status_code == 404`
> 的话那行判断**永远执行不到**，页面照样 404，而且看不出哪里错了。

**★ 第二个坑（`except OSError`）**：
节点 id 形如 `sub:work/ai`，含 `:` 和 `/`，拼进静态路径后
Windows 直接抛 `OSError`——**它不是 HTTPException**，
上面的 `except` 抓不到，于是**穿成 500「服务器内部错误」**，
而真因（URL 少编码了一位）被彻底掩盖。
> **教训：`OSError` 不是 `HTTPException`，`except` 抓不到它**。
> 兜底代价只是「把一种 404 报成另一种 404」，收益是**不掩盖真因**。

---

## 7. 把整条链路串一遍：一个请求的完整一生

现在把所有零件拼起来。**这是「点一次『会』」的完整流程**：

```
① 前端发请求
   PUT /api/progress/java-hashmap
   Header: Authorization: Bearer <token>
   Body:   {"level": 3}

② 请求进入 uvicorn → 交给 FastAPI

③ guard_log_cache 中间件（进来部分）
   ├─ 检查 Content-Length，超了直接 413 返回（不进业务）
   └─ 把 _receive 换成「边收边数」的版本

④ 异常处理器层（还没到业务）

⑤ 路由匹配
   app/routers/web/learning.py:32  @router.put('/progress/{cid}')
   ├─ 提取路径参数 cid = 'java-hashmap'
   ├─ 用 ProgressIn 模型校验 body → body.level 是整数 3
   │   （校验不过 → RequestValidationError → 400）
   └─ 看到 Depends(current_user) → 先执行 current_user()
       ├─ 从 Header 读 Authorization
       ├─ 验 JWT 签名 → 解出 user_id
       ├─ db.user_get() 查这个用户还在不在
       └─ 返回脱敏后的 user 字典
           （验不过 → 401，函数根本不会跑）

⑥ 真正执行端点函数 set_progress(cid='java-hashmap', body=ProgressIn(level=3), user={...})
   ├─ 手动检查 level in (1,2,3) → 不在就 400（★不用 Field(ge/le)，因为要返 400 不是 422）
   └─ db.set_level(cid, 3, user_id=user['id'])

⑦ 业务层 core/db.py：set_level()
   ├─ schedule(旧进度, 3)  → 转发给 algo.get().schedule()
   │                          └─ algo/sm2.py 的 20 行算法算出 interval / nextAt
   ├─ backend().progress_put()  → 写进度（MySQL 或 JSON）
   ├─ log_review()              → 追加一条复习事件（算法库）
   └─ mastery_of(refresh=True)  → 重算 BKT 掌握度
       ↑ 这三步在同一个 try 里：派生数据丢了能重算，进度正确性优先

⑧ 返回值 {'ok': True, 'id': cid, 'progress': rec}
   → FastAPI 自动转成 JSON

⑨ 中间件（出去部分）
   ├─ 加 Cache-Control: no-store
   └─ 往 stderr 记一行 "PUT /api/progress/xxx → 200 3ms"

⑩ 响应回给前端
```

**★ 记住这条链的核心：中间件 → 路由匹配 → 依赖注入 → 端点函数 → 业务层 → 返回**

**这个顺序在所有 Web 框架里都一样**（Flask/Django/Express 也是「中间件 → 路由 → 处理」），
学会这一条，FastAPI/Flask 你都能自己摸清了。

---

## 8. 你必须掌握的 8 个 FastAPI 知识点

读完后，你应该能**不看文档**回答这 8 个问题。答不上来的回去看对应节。

1. **FastAPI 的本质是什么？**（§1）
   → 读你函数签名 → 建路由表 → 校验参数 → 调你的函数 → 返回值自动变 JSON。

2. **`@app.get('/x/{id}')` 里的 `id` 怎么传到函数的？**
   → 从 URL 路径的大括号里提取，按类型标注转成对应类型。

3. **`Depends(current_user)` 到底做了什么？**
   → 框架先执行 `current_user()`，把返回值当参数传给你的函数。

4. **`async def` 和 `def` 什么时候用哪个？**
   → 阻塞 IO（文件/数据库）用 `def`（丢线程池）；高并发等待（调 AI/网络）用 `async def`。

5. **`Query(50, ge=1, le=500)` 是什么意思？**
   → 默认值 50；必须 ≥1 且 ≤500；越界自动 422。

6. **`body: ProgressIn` 和 `cid: str` 两种参数的区别？**
   → 一个从请求体（按 Pydantic 模型校验），一个从 URL 路径（按类型标注）。

7. **中间件是什么？在哪执行？**
   → 每个请求进出都要过的一道手续；执行顺序在「路由之前」和「端点之后」。

8. **为什么这个项目把 422 改成 400、把 999 翻译成 None、把 `password_hash` 脱敏？**
   → 对外契约要和前端约定一致，内部状态不能直接泄漏给外部。

---

## 附：怎么继续练？

**光看懂不够，要能自己写。** 三个递进的练习：

1. **改一个端点**：给 `/api/stats` 加一个新查询参数（比如 `?domain=java`），
   只改 `learning.py` 一个文件，看能不能跑通。
2. **加一个端点**：在 `learning.py` 加一个 `GET /api/review/streak`
   （返回连续复习天数），仿照 `get_today_pick` 写。**这是最好的 FastAPI 练习**。
3. **改 schemas**：给 `ProgressIn` 加一个字段，看 Swagger 里有什么变化，
   再故意传错类型看 400 长什么样。

**读代码的通用方法**（记住这一条，比记住任何 API 都重要）：

> 看到不认识的代码，**先问三个问题**：
> ① 这行在**读**什么还是**写**什么？
> ② 如果这行**删掉/改错**会怎样？
> ③ 注释里有没有写**为什么**？
>
> 项目里所有「为什么这么写」的注释都是拿 bug 换的，
> **读注释的收益远大于读实现**。

<!-- 完 -->