// 严格 JSON 字面量：Node(vm) 与 Python(json) 都能直接读，请勿改回单引号
// Python · FastAPI 架构与实战（2026-10-09）
// ★ 缺口：原来只有 2 张（Flask vs FastAPI 原理、WSGI/ASGI），
//   缺「架构怎么搭」「依赖注入怎么分级」「中间件怎么写」这些实战骨架。
var CARDS_FASTAPI = [
  {
    "id": "fastapi-architecture",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "FastAPI",
      "整体架构与请求生命周期"
    ],
    "title": "FastAPI 的架构是什么？一个请求从进来到返回经过哪些层？",
    "oneLine": "Starlette 提供 ASGI 底座与路由，Pydantic 做校验，FastAPI 把它们组装成「读注解→查依赖→调函数→序列化」的高层接口。",
    "analogy": "像餐厅：Starlette 是厨房与传菜系统，Pydantic 是验菜单的服务员，FastAPI 是把整套流程编排给客人的门面。",
    "why": "理解这三层分工，才知道什么时候该用 FastAPI 的语法、什么时候要下沉到 Starlette 写原语。",
    "mechanism": [
      "① Starlette（ASGI）：真正的底层——路由、请求响应对象、中间件、生命周期，都是它实现的",
      "② Pydantic：按类型注解校验请求体/参数，并生成 OpenAPI 文档",
      "③ FastAPI：把前两者粘起来的「 DSL」——你写装饰器和类型注解，它产出路由表和文档",
      "④ 请求生命周期：中间件栈 → 依赖注入解析 → 参数校验 → 端点函数 → 序列化响应",
      "⑤ 依赖注入在**参数校验前**执行：Depends 的结果可以参与后续参数解析",
      "⑥ 多个可路由：APIRouter 分模块，各自带 prefix/tags，最后 include_router 汇总",
      "⑦ 需要 FastAPI 没封装的能力时，可直接用Starlette 的 Request/Response/WebSocket 兜底"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "ASGI中间件栈",
        "依赖注入解析",
        "参数校验(Pydantic)",
        "端点函数",
        "序列化响应"
      ],
      "frames": [
        {
          "s": 0,
          "note": "Starlette 层：中间件、路由匹配"
        },
        {
          "s": 1,
          "note": "先解析 Depends，再校验普通参数"
        },
        {
          "s": 2,
          "note": "Pydantic 按注解校验，不符直接 400/422"
        },
        {
          "s": 3,
          "note": "你的业务函数在这里跑"
        }
      ]
    },
    "interviewQ": [
      "FastAPI 和 Starlette 是什么关系？",
      "依赖注入在参数校验之前还是之后？",
      "什么时候需要直接用 Starlette？"
    ],
    "keywords": [
      "FastAPI",
      "Starlette",
      "ASGI",
      "架构",
      "依赖注入",
      "生命周期"
    ],
    "scene": [
      "面试被问「FastAPI 底层是什么」，答 Starlette 做ASGI + Pydantic 做校验，自己组装。",
      "想给所有请求加统一耗时统计，FastAPI 没现成封装，用@app.middleware 写。"
    ],
    "tags": [
      "FastAPI",
      "架构",
      "Web框架"
    ],
    "related": [
      {
        "id": "python-asgi-uvicorn",
        "kind": "extends",
        "note": "ASGI 是这套架构的底座"
      },
      {
        "id": "python-web-framework",
        "kind": "extends",
        "note": "与 Flask 的定位对比"
      },
      {
        "id": "fastapi-dependency-di",
        "kind": "extends",
        "note": "依赖注入是架构的关键机制"
      }
    ]
  },
  {
    "id": "fastapi-dependency-di",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "FastAPI",
      "依赖注入体系"
    ],
    "title": "Depends 的 dependencies 列表怎么用？和参数级 Depends 有什么区别？",
    "oneLine": "参数级 Depends 把结果喂给当前函数，函数级 dependencies 只做「执行但不取值」的副作用（鉴权、限流）。",
    "analogy": "参数级像「点菜时指定要哪道菜」（结果拿到手），函数级像「进店先洗手」（做了但不带走）。",
    "why": "很多人在路由装饰器里写依赖却取不到结果，混淆了这两种用法。",
    "mechanism": [
      "① 参数级：def f(db = Depends(get_db)) —— get_db() 的返回值赋给 db",
      "② 函数级：@router.get('/x', dependencies=[Depends(auth)]) —— 只执行 auth，不传值进函数",
      "③ 函数级典型用途：统一鉴权、限流、审计日志——这些要副作用不要返回值",
      "④ 依赖可以**嵌套**：get_db 自己也可以有依赖（如Depends(get_session)）",
      "⑤ 依赖可设 cache_key：同一请求内多个端点参数依赖同一个值只算一次（如当前用户）",
      "⑥ 子依赖覆盖：路径/查询参数类依赖可以传 use_cache=False 强制每次重算",
      "⑦ yield 依赖：生成器里yield 前是进入、yield 后是清理（数据库会话常用）"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "解析依赖树",
        "执行只读依赖(get_user)",
        "执行yield依赖(开DB会话)",
        "调用端点",
        "清理依赖"
      ],
      "frames": [
        {
          "s": 0,
          "note": "先解析整棵依赖树"
        },
        {
          "s": 1,
          "note": "有缓存的依赖本次只算一次"
        },
        {
          "s": 2,
          "note": "yield 依赖的清理在响应后"
        }
      ]
    },
    "interviewQ": [
      "参数级Depends 和 dependencies 列表的区别？",
      "怎么让「获取当前用户」在一个请求里只算一次？",
      "yield 依赖什么时候执行清理？"
    ],
    "keywords": [
      "Depends",
      "依赖注入",
      "dependencies",
      "yield依赖",
      "cache_key",
      "鉴权"
    ],
    "scene": [
      "路由写了 dependencies=[Depends(鉴权)] 却取不到用户信息——那是函数级，只执行不传值。",
      "每个请求都查一次用户表，用 cache_key=True 改成只查一次。"
    ],
    "tags": [
      "FastAPI",
      "依赖注入",
      "架构"
    ],
    "related": [
      {
        "id": "fastapi-architecture",
        "kind": "extends",
        "note": "依赖注入在请求生命周期中的位置"
      },
      {
        "id": "python-context-manager",
        "kind": "extends",
        "note": "yield 依赖本质是上下文管理器"
      }
    ]
  },
  {
    "id": "fastapi-middleware",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "FastAPI",
      "中间件与异常处理"
    ],
    "title": "FastAPI 中间件怎么写？和装饰器有什么区别？",
    "oneLine": "中间件包住**所有**请求、能拿到原始 Request/Response；装饰器只包住单个端点、拿不到 Response。",
    "analogy": "中间件像小区门卫（所有人进出都过），装饰器像贴在某家门上的春联（只管那一户）。",
    "why": "跨域、耗时统计、请求日志这类横切逻辑必须用中间件，用装饰器写会漏。",
    "mechanism": [
      "① @app.middleware('http') 注册，签名是 (request, call_next) -> Response",
      "② 进入：调用前的代码（如拦超大 body、附加 request.state）",
      "③ call_next(request) 才真正往下走到路由",
      "④ 退出：能拿到 response 改header（如加 CORS、no-store）",
      "⑤ ⚠️ BaseHTTPMiddleware 有性能代价（走额外 ASGI 包装），极致性能可用纯 ASGI 中间件",
      "⑥ 装饰器（如 @router.post 之外的路径操作装饰器）只能包端点、拿不到 Response",
      "⑦ 注册顺序：后加的中间件在**外层**（先执行进入）"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "中间件进入",
        "call_next 调路由",
        "端点执行",
        "中间件退出改响应"
      ],
      "frames": [
        {
          "s": 0,
          "note": "进入段：附加 request.state 等"
        },
        {
          "s": 1,
          "note": "call_next 才走到路由"
        },
        {
          "s": 2,
          "note": "端点返回后回到中间件"
        },
        {
          "s": 3,
          "note": "退出段：改响应头"
        }
      ]
    },
    "interviewQ": [
      "中间件和路径操作装饰器的区别？",
      "call_next 是什么？",
      "BaseHTTPMiddleware 有什么代价？"
    ],
    "keywords": [
      "中间件",
      "middleware",
      "call_next",
      "Request",
      "Response",
      "横切"
    ],
    "scene": [
      "要给所有接口加统一耗时日志，写了个装饰器结果只有部分接口生效——应该用中间件。",
      "中间件里给 request.state 挂用户信息，端点里直接读，不用层层传参。"
    ],
    "tags": [
      "FastAPI",
      "中间件",
      "架构"
    ],
    "related": [
      {
        "id": "fastapi-architecture",
        "kind": "extends",
        "note": "中间件在请求生命周期的最外层"
      },
      {
        "id": "fastapi-exception",
        "kind": "extends",
        "note": "异常处理常与中间件配合"
      }
    ]
  },
  {
    "id": "fastapi-exception",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "FastAPI",
      "异常处理"
    ],
    "title": "FastAPI 怎么统一处理异常？为什么不该到处 try/except？",
    "oneLine": "注册 @app.exception_handler 把领域异常翻译成统一 JSON 响应，端点只管抛、不用包 try。",
    "analogy": "像前台统一收走所有问题并转给对应部门，而不是让每个窗口自己处理投诉。",
    "why": "散落 try/except 会重复代码且容易漏掉某个端点，注册 handler 是单一出口。",
    "mechanism": [
      "① 抛 HTTPException(400, 'msg') 或自定义业务异常（如 BizError）",
      "② @app.exception_handler(BizError) 注册处理器，把异常翻译成 JSONResponse",
      "③ 自定义异常要继承 Exception，并在其中带上 code/msg",
      "④ ⚠️ 不存在的属性仍会抛 500：建议兜底一个 Exception handler 但要记日志",
      "⑤ 好处：端点只管抛业务异常，响应格式全站一致",
      "⑥ 相比裸 try/except：不用重复导入响应类、不用每个端点都写样板"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "端点抛业务异常",
        "exception_handler 匹配",
        "翻译成JSONResponse",
        "返回统一格式"
      ],
      "frames": [
        {
          "s": 0,
          "note": "端点只抛不接"
        },
        {
          "s": 1,
          "note": "按异常类型分派 handler"
        },
        {
          "s": 2,
          "note": "统一响应结构"
        }
      ]
    },
    "interviewQ": [
      "FastAPI 怎么统一处理异常？",
      "自定义异常要注意什么？",
      "为什么不建议到处 try/except？"
    ],
    "keywords": [
      "异常",
      "exception_handler",
      "HTTPException",
      "统一响应",
      "错误处理"
    ],
    "scene": [
      "每个端点都写一遍 try/except 返回同样格式，改一次格式要改十几个地方。",
      "注册一个 Exception 兜底 handler 后，漏网异常也不再裸奔 500。"
    ],
    "tags": [
      "FastAPI",
      "异常",
      "架构"
    ],
    "related": [
      {
        "id": "fastapi-middleware",
        "kind": "extends",
        "note": "异常常在中间件的 try 里被捕获"
      }
    ]
  },
  {
    "id": "fastapi-router",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "FastAPI",
      "路由组织与响应模型"
    ],
    "title": "APIRouter 怎么组织多文件项目？response_model 有什么作用？",
    "oneLine": "APIRouter 按业务分模块带 prefix/tags；response_model 声明返回结构，既限字段又生文档。",
    "analogy": "APIRouter 像给一栋楼分层（每层一个业务），response_model 像给每间房画个户型图。",
    "why": "单文件写几十个端点必然失控；不声明 response_model 会把内部字段全暴露出去。",
    "mechanism": [
      "① router = APIRouter(prefix='/api/users', tags=['用户'])，各模块一个",
      "② app.include_router(router) 汇总（★静态挂载要放最后，路由注册顺序影响匹配）",
      "③ response_model=UserOut 声明返回结构：多余字段会被过滤、文档自动生成",
      "④ ⚠️ 不声明 response_model 时，内部字段（如密码哈希）会整个泄露给前端",
      "⑤ status_code 参数声明成功码；tags 影响 Swagger 分组",
      "⑥ APIRouter 的依赖也可以是模块级 dependencies=[Depends(auth)]，统一给组内端点鉴权"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "建router(带prefix)",
        "各端点挂载",
        "app.include_router汇总",
        "response_model过滤"
      ],
      "frames": [
        {
          "s": 0,
          "note": "按业务模块拆"
        },
        {
          "s": 1,
          "note": "prefix 统一前缀"
        },
        {
          "s": 2,
          "note": "response_model 过滤敏感字段"
        }
      ]
    },
    "interviewQ": [
      "APIRouter 怎么组织项目？",
      "response_model 有什么作用？",
      "路由注册顺序有什么影响？"
    ],
    "keywords": [
      "APIRouter",
      "路由",
      "include_router",
      "response_model",
      "模块化"
    ],
    "scene": [
      "后端返回了用户对象（含密码哈希），前端能在 Network 里看到——没声明 response_model。",
      "把所有端点塞一个文件超2000 行，改成 APIRouter 按 users/orders 拆开。"
    ],
    "tags": [
      "FastAPI",
      "路由",
      "架构"
    ],
    "related": [
      {
        "id": "fastapi-architecture",
        "kind": "extends",
        "note": "APIRouter 是 FastAPI 架构的路由层"
      }
    ]
  },
  {
    "id": "fastapi-pagination",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "FastAPI",
      "数据库与分页"
    ],
    "title": "FastAPI 怎么连数据库？为什么分页接口要用 limit/offset 参数校验？",
    "oneLine": "用Depends 注入会话（yield 依赖保证关闭），分页用 Query(ge=,le=) 声明上下限防全表查询。",
    "analogy": "像从书架取书：会话管理是借书证（借完要还），分页是「一次借几本」不能无限借。",
    "why": "数据库会话漏关会连接池耗尽；limit 不设限会被恶意传 limit=999999 拖垮 DB。",
    "mechanism": [
      "① yield 依赖：def get_db() 打开会话，yield 前连接、yield 后关闭（异常也关）",
      "② yield 依赖的清理在**响应发出后**执行，避免连接被提前释放",
      "③ 分页：skip: int = Query(0, ge=0)、limit: int = Query(20, ge=1, le=100)",
      "④ ⚠️ le=100 这类上限必须有：无界limit 相当于把整表丢给内存",
      "⑤ ORM 查询用 select().offset().limit() 对应数据库分页，别先查全量再切片",
      "⑥ 总数单独 count 查询，一次分页要两次 SQL（数据 + 总数）"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "Depends(get_db)",
        "yield前开会话",
        "端点查询",
        "响应发出后关会话"
      ],
      "frames": [
        {
          "s": 0,
          "note": "yield 依赖管理连接生命周期"
        },
        {
          "s": 1,
          "note": "limit/offset 用 Query 限范围"
        },
        {
          "s": 2,
          "note": "清理在响应后，异常也关"
        }
      ]
    },
    "interviewQ": [
      "FastAPI 怎么管理数据库会话？",
      "为什么分页要限制 limit 上限？",
      "yield 依赖什么时候清理？"
    ],
    "keywords": [
      "数据库",
      "会话",
      "分页",
      "limit",
      "offset",
      "yield依赖",
      "连接池"
    ],
    "scene": [
      "服务跑久了数据库连接池耗尽，查出是 get_db 没关连接。",
      "接口没限制 limit，被传limit=1000000 一次拉全表把内存打爆。"
    ],
    "tags": [
      "FastAPI",
      "数据库",
      "分页"
    ],
    "related": [
      {
        "id": "fastapi-dependency-di",
        "kind": "extends",
        "note": "get_db 就是个 yield 依赖"
      },
      {
        "id": "python-context-manager",
        "kind": "extends",
        "note": "yield 依赖本质是上下文管理器"
      }
    ]
  },
  {
    "id": "fastapi-async-db",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "FastAPI",
      "异步与并发"
    ],
    "title": "FastAPI 里什么时候用 async def，什么时候用普通 def？",
    "oneLine": "端点写 def（同步库）会被丢线程池；要 async def 就必须用异步驱动（asyncpg/aiomysql），否则阻塞事件循环。",
    "analogy": "async 的服务员能同时照看多桌，但端上菜时你不能站着不动等他——同步库就属于「站着不动」。",
    "why": "这是 FastAPI 新手最容易踩的性能坑：写了 async 却调同步库，并发直接崩。",
    "mechanism": [
      "① 端点写 def → Starlette丢线程池执行（适合同步库）",
      "② 端点写 async def → 在事件循环上跑（适合真异步库/网络IO）",
      "③ ⚠️ async def 里调 requests/同步SQLAlchemy = **阻塞整个事件循环**，所有请求一起卡",
      "④ 异步要配异步驱动：asyncpg（PG）/aiomysql（MySQL）/httpx（HTTP）",
      "⑤ 实在没法换同步库，就在 async 里用 run_in_executor / starlette 的iterate_in_threadpool 包起来",
      "⑥ 选型结论：**不确定就写 def**（进线程池不会错），要真并发再上async + 异步栈"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "f1",
          "label": "端点"
        },
        {
          "id": "f2",
          "label": "def→线程池"
        },
        {
          "id": "f3",
          "label": "async def→事件循环"
        },
        {
          "id": "f4",
          "label": "阻塞?"
        }
      ],
      "edges": [
        {
          "from": "f1",
          "to": "f2",
          "label": "同步库"
        },
        {
          "from": "f1",
          "to": "f3",
          "label": "异步库"
        },
        {
          "from": "f3",
          "to": "f4",
          "label": "调同步库则阻塞"
        }
      ],
      "frames": [
        {
          "note": "def 走线程池，不会卡住事件循环",
          "n": "f1"
        },
        {
          "note": "async 要配异步驱动",
          "n": "f2"
        },
        {
          "note": "async+同步库 = 事件循环被阻塞",
          "n": "f3"
        }
      ]
    },
    "interviewQ": [
      "FastAPI 端点什么时候用 async def？",
      "async 里调同步库会怎样？",
      "async def 和 def 的底层区别？"
    ],
    "keywords": [
      "async",
      "事件循环",
      "线程池",
      "异步驱动",
      "阻塞",
      "asyncpg"
    ],
    "scene": [
      "async def 端点里用了 requests，压测时吞吐暴跌——同步IO 堵死了事件循环。",
      "面试被问「async 一定比 def 快吗」，答不一定，取决于有没有阻塞调用。"
    ],
    "tags": [
      "FastAPI",
      "异步",
      "并发",
      "性能"
    ],
    "related": [
      {
        "id": "python-asgi-uvicorn",
        "kind": "extends",
        "note": "ASGI 服务器决定并发模型"
      },
      {
        "id": "python-concurrency-model",
        "kind": "extends",
        "note": "并发选型的通用原则"
      }
    ]
  },
  {
    "id": "fastapi-webhook",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "FastAPI",
      "实战模式"
    ],
    "title": "FastAPI 怎么接第三方回调？文件上传和后台任务怎么处理？",
    "oneLine": "回调接口用后台任务/队列解耦，文件上传用 UploadFile（流式），耗时操作丢 BackgroundTasks 别让用户干等。",
    "analogy": "回调是别人来敲门，先开门收下（快速响应），活儿留到关门后干（后台任务）。",
    "why": "同步处理耗时操作会让对方（支付/IM 平台）超时重试，引发重复通知。",
    "mechanism": [
      "① 第三方回调要**快速返回 200**，耗时逻辑丢后台（BackgroundTasks 或任务队列）",
      "② BackgroundTasks 是「响应后执行」的轻量方案（进程内，重启会丢）",
      "③ 可靠场景用 Celery/ARQ 任务队列（持久化、可重试、可跨进程）",
      "④ 文件上传：参数声明 UploadFile，读用 await file.read()，二进制流式处理",
      "⑤ ⚠️ UploadFile 是临时文件，大文件应边写磁盘边校验（类型/大小/内容）",
      "⑥ 回调接口要做**幂等**（去重键），因为对方可能重复推送"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "收到回调",
        "验签+去重",
        "快速200响应",
        "后台/队列处理耗时逻辑"
      ],
      "frames": [
        {
          "s": 0,
          "note": "回调先快速响应，避免对方重试"
        },
        {
          "s": 1,
          "note": "验签防伪造，去重防重复处理"
        },
        {
          "s": 2,
          "note": "耗时逻辑丢后台/队列"
        }
      ]
    },
    "interviewQ": [
      "FastAPI 怎么接第三方回调？",
      "BackgroundTasks 和 Celery 怎么选？",
      "文件上传要注意什么？"
    ],
    "keywords": [
      "回调",
      "webhook",
      "BackgroundTasks",
      "UploadFile",
      "幂等",
      "Celery"
    ],
    "scene": [
      "支付回调接口同步查数据库耗时 2 秒，对方超时后重复推送了 5 次。",
      "上传大文件先读进内存直接 OOM，改成 UploadFile 边写边处理。"
    ],
    "tags": [
      "FastAPI",
      "实战",
      "后台任务",
      "文件上传"
    ],
    "related": [
      {
        "id": "fastapi-middleware",
        "kind": "extends",
        "note": "回调的验签常在中间件统一做"
      },
      {
        "id": "python-concurrency-model",
        "kind": "compare",
        "note": "耗时任务该丢线程还是队列"
      }
    ]
  }
];
if (typeof module !== "undefined" && module.exports) {
  module.exports = CARDS_FASTAPI;
}