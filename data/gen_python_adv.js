// 严格 JSON 字面量：Node(vm) 与 Python(json) 都能直接读，请勿改回单引号
// Python 进阶补齐（2026-10-09）：原来 18 张全是语法基础（GIL/闭包/装饰器/生成器），
// 补齐到 32 张 —— 补上面向对象、并发模型、协程、Web 框架、测试工程化、性能剖析。
var CARDS_PY_ADV = [
  {
    "id": "python-oop-dunder",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "面向对象",
      "魔术方法与数据模型"
    ],
    "title": "__getattr__ 和 __getattribute__ 有什么区别？",
    "oneLine": "__getattribute__ 拦所有属性访问，__getattr__ 只在「常规查找失败后」才被调用。",
    "analogy": "__getattribute__ 是门卫（所有人进门都查），__getattr__ 是前台（只有没登记的人才找他）。",
    "why": "区别决定了实现 getattr 时的性能——前者每次访问都走它，后者只在走空路径时走。",
    "mechanism": [
      "① 属性访问先走 __getattribute__，它内部做通用查找（type → 实例 → 类）",
      "② 通用查找失败会调 __getattr__（如果有），否则抛 AttributeError",
      "③ 所以自定义 __getattr__ 比改 __getattribute__ 安全，Python 内部才不会因你的逻辑崩溃",
      "④ ⚠️ 坑：__getattr__ 里访问 self.其它 递归引用同名 __getattr__ 会无限递归",
      "⑤ 常用双下：__init__ 初始化、__repr__ 调试显示、__eq__ 相等、__len__ 长度、__enter__/__exit__ 上下文管理器",
      "⑥ ⚠️ 坑：定义了 __eq__ 就默认没有 __hash__，对象变不可哈希（不能再放进 set/dict）",
      "⑦ data model 让 Python 的运算符（+、[]、for）都能被重载，这是「运算符重载」的底层机制"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "访问属性",
        "__getattribute__",
        "常规查找",
        "__getattr__"
      ],
      "frames": [
        {
          "s": 0,
          "note": "obj.x 触发访问"
        },
        {
          "s": 1,
          "note": "__getattribute__ 先拦所有访问"
        },
        {
          "s": 2,
          "note": "常规查找(type/实例/类)"
        },
        {
          "s": 3,
          "note": "失败才走 __getattr__，否则抛异常"
        }
      ]
    },
    "interviewQ": [
      "定义了 __eq__ 后为什么不能哈希？",
      "__getattr__ 递归怎么避免？",
      "Python 的运算符重载靠什么机制？"
    ],
    "keywords": [
      "dunder",
      "魔术方法",
      "getattr",
      "数据模型",
      "hash",
      "eq"
    ],
    "scene": [
      "ORM 里用 __getattr__ 把列名映射成属性值，写的时候不小心无限递归了。",
      "定义了 __eq__ 之后对象放不进 set，报「unhashable type」。"
    ],
    "tags": [
      "面向对象",
      "魔术方法",
      "数据模型"
    ],
    "related": [
      {
        "id": "python-decorator",
        "kind": "extends",
        "note": "装饰器本质就是用 __call__ 重构调用行为"
      },
      {
        "id": "python-descriptor",
        "kind": "extends",
        "note": "属性、classmethod 都是描述符"
      }
    ]
  },
  {
    "id": "python-descriptor",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "面向对象",
      "描述符与元编程"
    ],
    "title": "描述符（descriptor）是什么？property 和它什么关系？",
    "oneLine": "一个类如果定义了 __get__，它的实例就成为「描述符」，控制属性访问；property 是它的语法糖。",
    "analogy": "描述符像一个门锁：你「拿」属性时它不直接给，而是先经过锁的加工。",
    "why": "它实现了 property、classmethod、staticmethod、参数校验、ORM 字段定义——Python 里大量魔法都靠它。",
    "mechanism": [
      "① 描述符 =定义了 __get__/__set__/__delete__ 的类；它的实例作为另一个类的属性",
      "② 访问 obj.attr 时，先找type(obj) 里 attr 是否是描述符，是则调它的 __get__",
      "③ 实例字典优先级高于类属性（数据描述符除外——它会覆盖实例字典）",
      "④ property、classmethod、staticmethod、functools.cached_property 都是描述符的实现",
      "⑤ ⚠️ 非数据描述符（只定义了 __get__）会被实例字典覆盖，数据描述符（还定义了 __set__/__delete__）优先",
      "⑥ 典型用途：ORM 的字段类型校验（赋值时检查类型）、懒加载属性、只读属性"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "x1",
          "label": "访问 obj.attr"
        },
        {
          "id": "x2",
          "label": "查实例字典"
        },
        {
          "id": "x3",
          "label": "类属性是描述符?"
        },
        {
          "id": "x4",
          "label": "调 __get__/__set__"
        }
      ],
      "edges": [
        {
          "from": "x1",
          "to": "x2",
          "label": "先查"
        },
        {
          "from": "x2",
          "to": "x3",
          "label": "查类属性"
        },
        {
          "from": "x3",
          "to": "x4",
          "label": "是则走描述符"
        }
      ],
      "frames": [
        {
          "note": "属性访问入口",
          "n": "x1"
        },
        {
          "note": "实例字典里有就直接返回",
          "n": "x2"
        },
        {
          "note": "否则看类属性是不是描述符",
          "n": "x3"
        },
        {
          "note": "描述符控制最终读写行为",
          "n": "x4"
        }
      ]
    },
    "interviewQ": [
      "property 的底层是什么？",
      "数据描述符和非数据描述符的区别？",
      "如何用描述符实现字段校验？"
    ],
    "keywords": [
      "描述符",
      "descriptor",
      "property",
      "getset",
      "元编程",
      "cached_property"
    ],
    "scene": [
      "Flask 的路由、SQLAlchemy 的字段都是描述符，赋值时自动做类型检查。",
      "面试被问「property 原理」，答它是个数据描述符，赋值走 __set__。"
    ],
    "tags": [
      "面向对象",
      "描述符",
      "元编程"
    ],
    "related": [
      {
        "id": "python-oop-dunder",
        "kind": "extends",
        "note": "描述符靠魔术方法协议工作"
      }
    ]
  },
  {
    "id": "python-abc-protocol",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "面向对象",
      "抽象基类与协议"
    ],
    "title": "抽象基类 ABC 和结构化子类型（duck typing）怎么选？",
    "oneLine": "ABC 显式声明「必须实现什么」，Protocol 隐式要求「结构上像就行」，两者都是鸭子类型的强化。",
    "analogy": "ABC 像「必须考驾照才能上路」的规定，Protocol 像「你会开车就行」——不问有没有证。",
    "why": "决定了库设计时该强制继承还是允许隐式实现，直接影响扩展性和耦合。",
    "mechanism": [
      "① 鸭子类型：只要有 .read 方法就能传给 readAll，不检查类型",
      "② ABC 用 metaclass=ABCMeta + @abstractmethod，禁止实例化抽象类，子类必须实现",
      "③ ABC 是**名义继承**：子类必须显式继承才能获得实现约束",
      "④ Protocol 是**结构化子类型**：不需要继承，有对应方法就满足类型",
      "⑤ Protocol 的优势：第三方库可以「鸭子补丁」而不用继承你的基类",
      "⑥ 现代 Python 推荐 Protocol 做接口、ABC 做需要共享实现或实例检查的基类"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "ABC",
          "lines": [
            "class A(Shape)",
            "必须继承",
            "抽象方法强制实现"
          ],
          "note": "名义继承"
        },
        {
          "title": "Protocol",
          "lines": [
            "class P(Shape)",
            "不用继承",
            "有方法就算"
          ],
          "note": "结构化"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "ABC 强制继承"
        },
        {
          "s": 1,
          "note": "Protocol 只看结构"
        }
      ]
    },
    "interviewQ": [
      "ABC 和 Protocol 的区别？",
      "什么时候该用 ABC 而不是 Protocol？",
      "什么是鸭子类型？"
    ],
    "keywords": [
      "ABC",
      "Protocol",
      "鸭子类型",
      "抽象基类",
      "结构化子类型",
      "abstractmethod"
    ],
    "scene": [
      "写工具库时用 Protocol 定义的接口，第三方类不用改一行就满足了类型约束。",
      "面试被问「什么时候用 ABC」，答需要共享基类实现或运行时 isinstance 检查时。"
    ],
    "tags": [
      "面向对象",
      "类型",
      "设计"
    ],
    "related": [
      {
        "id": "python-typing-generics",
        "kind": "extends",
        "note": "Protocol 是现代类型注解的核心玩法"
      }
    ]
  },
  {
    "id": "python-typing-generics",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "类型系统",
      "类型注解与泛型"
    ],
    "title": "类型注解在运行时不生效，那它有什么用？",
    "oneLine": "注解主要是给静态检查器（mypy）看，运行时由 pydantic 等库读取做校验。",
    "analogy": "注解像文档注释的升级版——运行时不管，但 IDE 和检查工具会拿它当契约。",
    "why": "大项目靠它发现类型错误；FastAPI 靠它做参数校验和生成文档。",
    "mechanism": [
      "① 注解默认被解释器忽略（存进 __annotations__），不影响运行",
      "② 静态检查器（mypy/pyright）读注解做类型推导，提前发现逻辑错误",
      "③ FastAPI/pydantic 在运行时读注解 → 做参数校验 + 生成 Swagger 文档",
      "④ 泛型 T 用 TypeVar 声明，泛型容器 list[int]/dict[str,int] 约束元素类型",
      "⑤ ⚠️ 注意 Optional[X] 等价于 Union[X, None]，但不等于默认值——没传就是 None",
      "⑥ 现代Python 支持 | 语法（int | None）更简洁，需要 3.10+"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "注解的去向",
          "lines": [
            "mypy 静态检查",
            "pydantic 运行时校验",
            "IDE 补全"
          ],
          "note": "工具链消费"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "注解本身不参与运行，工具消费它"
        }
      ]
    },
    "interviewQ": [
      "类型注解在运行时生效吗？",
      "泛型怎么用 TypeVar？",
      "FastAPI 怎么利用注解？"
    ],
    "keywords": [
      "类型注解",
      "泛型",
      "TypeVar",
      "mypy",
      "pydantic",
      "Optional"
    ],
    "scene": [
      "给 FastAPI 接口写def f(x: int)，传字符串直接 422——pydantic 读了注解。",
      "老项目没注解，mypy 全是 Any，类型错误全靠人肉发现。"
    ],
    "tags": [
      "类型",
      "注解",
      "泛型"
    ],
    "related": [
      {
        "id": "python-abc-protocol",
        "kind": "extends",
        "note": "Protocol 建立在类型注解之上"
      },
      {
        "id": "python-mypy",
        "kind": "extends",
        "note": "类型注解的消费者之一"
      }
    ]
  },
  {
    "id": "python-concurrency-model",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "并发模型",
      "并发方案选型"
    ],
    "title": "多线程、多进程、asyncio 怎么选？",
    "oneLine": "IO 密集用 asyncio，CPU 密集用多进程，需要同步调用简单并发用线程池。",
    "analogy": "多线程像一个人排队买票，多进程像开多个窗口，asyncio 像一个人同时用手机预约多个窗口。",
    "why": "选错就是性能腰斩——CPU 密集用 asyncio 反而更慢（GIL 下协程不并行）。",
    "mechanism": [
      "① 多线程：适合 IO 密集（等网络/文件时释放 GIL），但 CPU 密集受 GIL 限制无法并行",
      "② 多进程：真正利用多核，但有序列化/通信开销，进程数受内存限制",
      "③ asyncio：单线程事件循环，适合高并发 IO（大量连接等待），CPU 密集会卡住整个循环",
      "④ 线程池（concurrent.futures）：CPU 密集要用 ProcessPoolExecutor，IO 密集用 ThreadPoolExecutor",
      "⑤ 实际选型：爬虫/接口调用→asyncio 或线程池；数据处理/模型推理→多进程；既有 IO 又有计算→混合",
      "⑥ 协程不能替代线程做需要抢占的场景（如 CPU 密集用协程会阻塞整个事件循环）"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "多线程",
          "lines": [
            "IO 密集✓",
            "CPU 受 GIL✗"
          ],
          "note": "共享内存，切换轻"
        },
        {
          "title": "多进程",
          "lines": [
            "CPU 密集✓",
            "内存开销大"
          ],
          "note": "真并行，有序列化成本"
        },
        {
          "title": "asyncio",
          "lines": [
            "高并发IO✓",
            "CPU会阻塞循环✗"
          ],
          "note": "单线程事件循环"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "先判断任务类型"
        },
        {
          "s": 1,
          "note": "IO 密集倾向线程/协程"
        },
        {
          "s": 2,
          "note": "CPU 密集必须多进程"
        }
      ]
    },
    "interviewQ": [
      "CPU 密集为什么不能靠线程池？",
      "asyncio 为什么不能做 CPU 密集？",
      "什么时候混合用多线程和多进程？"
    ],
    "keywords": [
      "并发",
      "多线程",
      "多进程",
      "asyncio",
      "GIL",
      "线程池",
      "选型"
    ],
    "scene": [
      "接口压测用 asyncio 吞吐上不去，换线程池立刻翻倍——原来混了 CPU 密集的 JSON 序列化。",
      "面试被问「GIL 什么时候能被去掉」，答 3.13+ 的 free-threaded 构建，但有兼容开销。"
    ],
    "tags": [
      "并发",
      "性能",
      "选型"
    ],
    "related": [
      {
        "id": "python-gil",
        "kind": "extends",
        "note": "GIL 是线程选型的关键约束"
      },
      {
        "id": "python-asyncio",
        "kind": "extends",
        "note": "协程方案的细节"
      }
    ]
  },
  {
    "id": "python-asyncio-eventloop",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "并发模型",
      "asyncio 事件循环"
    ],
    "title": "asyncio 的事件循环是怎么跑协程的？await 到底在等什么？",
    "oneLine": "单线程事件循环调度协程，await 时挂起让出控制权，等IO 完成再恢复——全程不创建线程。",
    "analogy": "像服务员同时照看多桌客人：某桌要等菜就把这桌挂起，先去照看别的桌。",
    "why": "理解了「await 让出控制权」，才能定位协程里哪行阻塞了事件循环。",
    "mechanism": [
      "① 事件循环是while 真：取就绪的协程执行，遇 await 且未就绪则挂起",
      "② await 等待的是 IO 事件（socket 可读、文件就绪、定时器），不是阻塞线程",
      "③ ⚠️ 协程里做 CPU 密集计算会**阻塞整个循环**（单线程），所有连接一起卡",
      "④ asyncio.sleep(0) 用于主动让出控制权（配合并发任务），asyncio.sleep(1) 是真正挂起",
      "⑤ Task 是协程的调度单位，create_task 后并发执行，gather 收集结果",
      "⑥ asyncio.run() 创建并关闭事件循环；应用入口用它跑 async main"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "取就绪协程",
        "执行到await",
        "挂起",
        "IO完成",
        "恢复执行"
      ],
      "frames": [
        {
          "s": 0,
          "note": "单线程循环逐个调度"
        },
        {
          "s": 1,
          "note": "遇 await 未就绪就挂起"
        },
        {
          "s": 2,
          "note": "控制权让给别的协程"
        },
        {
          "s": 3,
          "note": "IO 完成触发回调恢复"
        }
      ]
    },
    "interviewQ": [
      "await 的时候线程在干什么？",
      "协程里能写阻塞代码吗？",
      "Task 和 coroutine 的区别？"
    ],
    "keywords": [
      "asyncio",
      "协程",
      "事件循环",
      "await",
      "Task",
      "非阻塞"
    ],
    "scene": [
      "协程里写了 requests.get，整个服务的连接都卡住了——同步阻塞调用堵塞事件循环。",
      "面试被问「await 是并发还是并行」，答并发（单线程），并行要靠多进程。"
    ],
    "tags": [
      "并发",
      "协程",
      "asyncio"
    ],
    "related": [
      {
        "id": "python-concurrency-model",
        "kind": "extends",
        "note": "asyncio 是并发方案之一"
      },
      {
        "id": "fe-promise",
        "kind": "compare",
        "note": "JS Promise 微任务 vs Python 协程，思路同源"
      }
    ]
  },
  {
    "id": "python-context-manager",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "工程化",
      "上下文管理器"
    ],
    "title": "with 语句的 __enter__/__exit__ 是怎么保证异常安全的？",
    "oneLine": "with 进入时调 __enter__、退出时（无论有无异常）调 __exit__，所以资源一定被释放。",
    "analogy": "像借东西必须归还：无论中途成功还是出错，借的东西都会自动还回去。",
    "why": "文件、锁、数据库连接都要「不管怎样都得关」，手动 try/finally 容易漏。",
    "mechanism": [
      "① with 用 contextlib 的__enter__/__exit__ 协议管理资源",
      "② 正常结束和抛异常都会走 __exit__（相当于自动 finally）",
      "③ __exit__ 收到 (exc_type, exc_val, exc_tb)，返回 True 可**吞掉**异常",
      "④ @contextmanager 装饰器可以把「有 yield 的函数」变成上下文管理器，yield 前=进入、yield 后=退出",
      "⑤ ⚠️ contextmanager 里抛异常在 yield 之前= 不会执行清理；yield 之后抛出则清理会执行",
      "⑥ threading.Lock、文件对象、socket 本身都是上下文管理器，天然支持 with"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "进入",
        "__enter__",
        "代码块",
        "__exit__(含异常)"
      ],
      "frames": [
        {
          "s": 0,
          "note": "with 触发进入"
        },
        {
          "s": 1,
          "note": "__enter__ 拿到资源"
        },
        {
          "s": 2,
          "note": "执行代码块"
        },
        {
          "s": 3,
          "note": "无论有无异常都走 __exit__ 释放"
        }
      ]
    },
    "interviewQ": [
      "with 的异常安全怎么保证？",
      "__exit__ 返回 True 是什么意思？",
      "contextmanager 装饰器原理？"
    ],
    "keywords": [
      "with",
      "上下文管理器",
      "contextmanager",
      "enter",
      "exit",
      "资源释放"
    ],
    "scene": [
      "忘了 close 文件句柄，用 with 之后不用操心了。",
      "自己实现一个计时器上下文管理器，用 @contextmanager 加 yield。"
    ],
    "tags": [
      "工程化",
      "语法",
      "资源管理"
    ],
    "related": [
      {
        "id": "python-context-manager-advanced",
        "kind": "extends",
        "note": "异步上下文管理器 await 变体"
      }
    ]
  },
  {
    "id": "python-context-manager-advanced",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "工程化",
      "异步上下文管理"
    ],
    "title": "异步 with（async with）和 with 有什么区别？",
    "oneLine": "异步资源的 __aenter__/__aexit__ 是协程，进入退出要 await，异步锁用它实现。",
    "analogy": "普通 with 是进同步浴室，async with 是进需要等排队的那种。",
    "why": "异步连接池、异步锁都用它，手动 acquire/release 在 await 之间可能被打断导致状态错乱。",
    "mechanism": [
      "① async with 调用 __aenter__/__aexit__，它们是协程，要 await",
      "② ⚠️ 不能用普通 with 管异步资源——拿到的 awaitable 没被等待",
      "③ asyncio.Lock 支持 async with，退出自动 release，且能防并发重复获取",
      "④ 异步上下文的退出也在 await 中完成，异常同样会走 __aexit__",
      "⑤ contextlib.asynccontextmanager 装饰器可把有 yield 的异步函数变成异步上下文管理器",
      "⑥ 典型场景：async with aiohttp.ClientSession() 复用连接、async with db.transaction() 保证事务"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "await __aenter__",
        "代码块",
        "await __aexit__"
      ],
      "frames": [
        {
          "s": 0,
          "note": "异步进入要 await"
        },
        {
          "s": 1,
          "note": "执行代码块"
        },
        {
          "s": 2,
          "note": "异步退出，异常也会走"
        }
      ]
    },
    "interviewQ": [
      "async with 和 with 的区别？",
      "为什么异步锁要用 async with？",
      "asynccontextmanager 怎么用？"
    ],
    "keywords": [
      "async with",
      "异步上下文",
      "asynccontextmanager",
      "异步锁"
    ],
    "scene": [
      "手写 acquire()/release() 包异步锁，协程切换时锁状态错乱，改 async with 解决。",
      "aiohttp 的 Session 用 async with 包裹才能正确关闭。"
    ],
    "tags": [
      "异步",
      "上下文管理",
      "并发"
    ],
    "related": [
      {
        "id": "python-context-manager",
        "kind": "extends",
        "note": "同步上下文管理器的异步版本"
      }
    ]
  },
  {
    "id": "python-web-framework",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "Web 框架",
      "Flask 与 FastAPI"
    ],
    "title": "Flask 和 FastAPI 有什么本质区别？什么时候选哪个？",
    "oneLine": "Flask 灵活轻量、无类型校验；FastAPI 基于类型注解自动校验 + 生成文档 + 原生 async。",
    "analogy": "Flask 像手动挡：你掌控一切但要自己接线。FastAPI 像自动挡带导航：类型注解一写，参数校验和文档自动有了。",
    "why": "选型影响开发效率和接口契约的严谨性。",
    "mechanism": [
      "① Flask 是微框架，只给路由和请求对象，其余全靠扩展",
      "② FastAPI 用 Pydantic 模型做请求体校验，从类型注解自动生成 Swagger 文档",
      "③ FastAPI 原生 async/await（异步框架），Flask 是同步的（用gevent/eventlet 异步化）",
      "④ FastAPI 自带依赖注入系统（Depends），Flask 没有官方方案",
      "⑤ Flask 生态更成熟（各种扩展），FastAPI 现代、性能好、自带文档",
      "⑥ 选型：要快速搭简单 API/复用现有 Flask 扩展→Flask；要类型安全+自动文档+高并发→FastAPI"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "Flask",
          "lines": [
            "灵活轻量",
            "手动校验",
            "同步为主"
          ],
          "note": "微框架+扩展"
        },
        {
          "title": "FastAPI",
          "lines": [
            "类型驱动",
            "自动校验+文档",
            "原生async"
          ],
          "note": "现代异步框架"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "核心差异在类型注解的利用"
        },
        {
          "s": 1,
          "note": "FastAPI 把注解变成了运行时能力"
        }
      ]
    },
    "interviewQ": [
      "FastAPI 相比 Flask 的核心优势？",
      "Flask 怎么实现异步？",
      "为什么 FastAPI 能自动生成文档？"
    ],
    "keywords": [
      "Flask",
      "FastAPI",
      "Web框架",
      "异步",
      "依赖注入",
      "选型"
    ],
    "scene": [
      "新项目用 FastAPI 写完接口，Swagger 文档自动就有了，前端能直接对着调。",
      "面试被问「FastAPI 为什么快」，答基于 async + Pydantic 校验在应用层完成。"
    ],
    "tags": [
      "Web框架",
      "Flask",
      "FastAPI"
    ],
    "related": [
      {
        "id": "python-typing-generics",
        "kind": "extends",
        "note": "FastAPI 靠类型注解实现校验"
      },
      {
        "id": "python-asgi-uvicorn",
        "kind": "extends",
        "note": "FastAPI 跑在 ASGI 服务器上"
      }
    ]
  },
  {
    "id": "python-asgi-uvicorn",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "Web 框架",
      "ASGI 与 WSGI"
    ],
    "title": "WSGI 和 ASGI 有什么区别？为什么异步框架需要 ASGI？",
    "oneLine": "WSGI 是同步接口（一次处理一个请求），ASGI 支持 async 并发——高并发异步必须用 ASGI 服务器。",
    "analogy": "WSGI 像一个窗口排队办业务，ASGI 像多个窗口同时接待。",
    "why": "决定 Web 服务的并发模型——用错就是异步框架跑出了同步效果。",
    "mechanism": [
      "① WSGI（Flask/Django）每个请求独立处理完再下一个，天然阻塞",
      "② ASGI（FastAPI/Starlette）支持 async，一个事件循环并发处理多个请求",
      "③ Uvicorn 是 ASGI 服务器，run.py 里就用了它",
      "④ 异步框架配同步服务器（Flask 那种）会导致并发能力被废掉",
      "⑤ 异步下CPU 密集任务要丢线程池 executor，否则阻塞事件循环",
      "⑥ ⚠️ 数据库驱动也要选异步版（asyncpg/aiomysql）否则同步驱动会卡住"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "请求到达",
        "ASGI协议",
        "事件循环",
        "并发处理"
      ],
      "frames": [
        {
          "s": 0,
          "note": "ASGI 服务器接收请求"
        },
        {
          "s": 1,
          "note": "交给 async 应用"
        },
        {
          "s": 2,
          "note": "事件循环调度协程"
        },
        {
          "s": 3,
          "note": "单线程并发多个请求"
        }
      ]
    },
    "interviewQ": [
      "WSGI 和 ASGI 的区别？",
      "为什么异步框架必须配异步服务器？",
      "异步应用里做 CPU 密集怎么办？"
    ],
    "keywords": [
      "ASGI",
      "WSGI",
      "uvicorn",
      "异步",
      "事件循环",
      "并发"
    ],
    "scene": [
      "FastAPI 接口吞吐上不去，查出用的同步 pymysql 驱动，阻塞了事件循环。",
      "面试被问「为什么 FastAPI 要用 Uvicorn」，答它是 ASGI 服务器支持 async。"
    ],
    "tags": [
      "Web框架",
      "异步",
      "协议"
    ],
    "related": [
      {
        "id": "python-asyncio",
        "kind": "extends",
        "note": "ASGI 的并发靠事件循环"
      },
      {
        "id": "python-web-framework",
        "kind": "extends",
        "note": "FastAPI 跑在 ASGI 服务器上"
      }
    ]
  },
  {
    "id": "python-testing",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "工程化",
      "测试"
    ],
    "title": "为什么要有测试？单元测试、集成测试、端到端测试怎么分层？",
    "oneLine": "单元测一个函数、集成测模块协作、端到端测完整链路，越往下越慢越少但越接近真实。",
    "analogy": "单元测试像检查单个零件，集成测试像组装后试运转，端到端像整车上路。",
    "why": "没有测试的重构等于闭眼改代码——改完不知道有没有破坏别的。",
    "mechanism": [
      "① 单元测试（pytest）：测单个函数/类，快、数量多、定位准",
      "② 集成测试：测模块间协作（如API +数据库），慢一些",
      "③ 端到端（E2E）：模拟用户完整流程，最慢、最少、最接近真实",
      "④ ⚠️ 测试金字塔：底层多、顶层少；如果倒过来（E2E 最多），跑得慢又难定位",
      "⑤ mock 隔离外部依赖（数据库、网络），让单元测试又快又稳",
      "⑥ 覆盖率是参考不是目标——关键是测「容易出错的地方」而非凑数字"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "测试金字塔",
          "lines": [
            "E2E 少/慢",
            "集成 中",
            "单元 多/快"
          ],
          "note": "下宽上窄"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "越底层越快越多，越上层越慢越少"
        }
      ]
    },
    "interviewQ": [
      "测试金字塔是什么？",
      "什么时候用 mock？",
      "覆盖率重要吗？"
    ],
    "keywords": [
      "测试",
      "pytest",
      "单元测试",
      "mock",
      "覆盖率",
      "集成测试"
    ],
    "scene": [
      "改了个工具函数，结果三个模块的输出都变了——因为没有单元测试兜底。",
      "面试被问「你怎么保证重构安全」，答先补测试再重构，测试金字塔覆盖关键路径。"
    ],
    "tags": [
      "工程化",
      "测试",
      "质量"
    ],
    "related": [
      {
        "id": "python-tooling",
        "kind": "extends",
        "note": "测试是工程化的一部分"
      }
    ]
  },
  {
    "id": "python-mypy",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "类型系统",
      "静态类型检查"
    ],
    "title": "mypy 有什么用？为什么类型注解不写等于白写？",
    "oneLine": "mypy 静态分析代码，在运行前发现类型错误和潜在 bug，不影响运行速度。",
    "analogy": "像代码体检：运行前就查出隐患，不用等程序崩了才知道。",
    "why": "动态语言的大项目靠人眼看不住类型，mypy 把很多错误提前到写代码时。",
    "mechanism": [
      "① mypy 读类型注解做静态类型推导，报告不一致处",
      "② 不写注解的类型是 Any，mypy 无法检查——注解是它的输入",
      "③ 渐进式类型：允许部分代码有注解，mypy 从有注解处向无注解处推断",
      "④ 能发现「传错类型」「返回类型不一致」「属性不存在」等运行才暴露的问题",
      "⑤ ⚠️ 不写注解的项目等于放弃类型保护，全是 Any 静默通过",
      "⑥ 配合 ruff（代码风格+基础检查）+ pytest（行为）构成 Python 三件套"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "写注解",
        "mypy静态分析",
        "报类型不一致",
        "修复"
      ],
      "frames": [
        {
          "s": 0,
          "note": "注解是mypy 的输入"
        },
        {
          "s": 1,
          "note": "静态分析不运行代码"
        },
        {
          "s": 2,
          "note": "提前发现类型错误"
        },
        {
          "s": 3,
          "note": "运行时无需成本"
        }
      ]
    },
    "interviewQ": [
      "mypy 有什么用？",
      "为什么类型注解要写全？",
      "静态检查和动态检查的区别？"
    ],
    "keywords": [
      "mypy",
      "静态检查",
      "类型",
      "注解",
      "ruff"
    ],
    "scene": [
      "一个函数参数写错类型，mypy 提前报错，运行到那条数据才崩。",
      "面试被问「Python 要不要类型」，答大项目值得，注解+mypy 是性价比最高组合。"
    ],
    "tags": [
      "类型",
      "工程化",
      "静态检查"
    ],
    "related": [
      {
        "id": "python-typing-generics",
        "kind": "extends",
        "note": "注解是静态检查的基础"
      },
      {
        "id": "python-tooling",
        "kind": "extends",
        "note": "mypy+ruff+pytest 三件套"
      }
    ]
  },
  {
    "id": "python-tooling",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "工程化",
      "依赖与工具链"
    ],
    "title": "requirements.txt 和 pyproject.toml 有什么区别？虚拟环境为什么要隔离？",
    "oneLine": "pyproject.toml 是现代标准（依赖+打包+工具配置），requirements.txt 只管依赖；venv 隔离不同项目的包版本。",
    "analogy": "同一个电脑上不同房间有不同温度（venv），避免一个项目升级包把另一个搞崩。",
    "why": "依赖冲突是 Python 最常见的「环境玄学」问题，隔离是解法。",
    "mechanism": [
      "① venv 给每个项目一个独立的 site-packages，激活后pip 只装到这个环境",
      "② requirements.txt 传统只列依赖；pyproject.toml 是现代标准（PEP 518），统一依赖/构建/工具配置",
      "③ ⚠️ 不锁版本（requirements 里不写 ==）会导致「昨天能跑今天崩」",
      "④ 现代用 uv/pip-tools 生成锁文件（requirements.lock 或 uv.lock）保证可重现",
      "⑤ 项目配置统一放 pyproject.toml（工具如 ruff/mypy 的配置也在这）",
      "⑥ ⚠️ 全局装包会污染所有项目，某个包升级导致老项目依赖它的功能悄悄坏了"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "全局环境",
          "lines": [
            "项目A 需要1.0",
            "项目B 需要2.0",
            "冲突!"
          ],
          "note": "不隔离的痛"
        },
        {
          "title": "venv 隔离",
          "lines": [
            "A/.venv → 1.0",
            "B/.venv → 2.0"
          ],
          "note": "各管各的"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "不隔离必然冲突"
        },
        {
          "s": 1,
          "note": "venv 每个项目独立"
        }
      ]
    },
    "interviewQ": [
      "为什么每个项目都要 venv？",
      "pyproject.toml 相比 requirements 的优势？",
      "什么是依赖锁定？"
    ],
    "keywords": [
      "venv",
      "虚拟环境",
      "pyproject",
      "requirements",
      "依赖",
      "uv",
      "锁定"
    ],
    "scene": [
      "在一个项目里升级了 requests，另一个老项目直接崩——因为没隔离。",
      "面试被问「怎么保证别人能跑你的代码」，答锁依赖版本 + pyproject.toml。"
    ],
    "tags": [
      "工程化",
      "依赖",
      "环境"
    ],
    "related": [
      {
        "id": "python-packaging",
        "kind": "extends",
        "note": "构建分发也是工程化一环"
      },
      {
        "id": "python-mypy",
        "kind": "extends",
        "note": "工具配置统一放pyproject"
      }
    ]
  },
  {
    "id": "python-packaging",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "工程化",
      "打包与发布"
    ],
    "title": "一个 Python 包是怎么被打包发布的？",
    "oneLine": "把代码打成 wheel 上传 PyPI，用户 pip install 拉下来安装；元信息写在 pyproject 里。",
    "analogy": "像与应用商店：开发打包上架，用户一键安装。",
    "why": "让代码可分发复用，是从「脚本」到「库」的跃迁。",
    "mechanism": [
      "① 包结构需要 __init__.py（或 pyproject 声明），构建工具收集源码",
      "② pyproject.toml 声明包元信息（名字/版本/依赖/入口），替代旧setup.py",
      "③ wheel 是构建产物（.whl），已编译/打包好，安装快",
      "④ 构建：python -m build →生成 sdist + wheel；上传：twine upload",
      "⑤ ⚠️ 版本号要遵循语义化版本（主版本.次版本.修订号），破坏性改动升主版本",
      "⑥ 入口点 entry_points 可暴露命令行工具（console_scripts）"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "写pyproject",
        "build构建",
        "生成wheel",
        "twine上传PyPI"
      ],
      "frames": [
        {
          "s": 0,
          "note": "元信息声明在 pyproject"
        },
        {
          "s": 1,
          "note": "构建工具收集成包"
        },
        {
          "s": 2,
          "note": "产出 wheel"
        },
        {
          "s": 3,
          "note": "上传后用户可 pip install"
        }
      ]
    },
    "interviewQ": [
      "wheel 和 sdist 区别？",
      "怎么发布一个包到 PyPI？",
      "entry_points 有什么用？"
    ],
    "keywords": [
      "打包",
      "wheel",
      "PyPI",
      "pyproject",
      "twine",
      "版本号"
    ],
    "scene": [
      "写了个工具函数库想给别人用，打成 wheel 上传 PyPI，别人 pip install 就能用。",
      "面试被问「怎么让同事复用你的代码」，答发到内部 PyPI 或直接给 wheel。"
    ],
    "tags": [
      "工程化",
      "打包",
      "发布"
    ],
    "related": [
      {
        "id": "python-tooling",
        "kind": "extends",
        "note": "打包依赖配置声明"
      }
    ]
  },
  {
    "id": "python-memory-leak",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "性能",
      "内存与性能"
    ],
    "title": "Python 怎么排查内存泄漏？为什么 del 不好使？",
    "oneLine": "引用计数归零才释放，要排查「谁还持有引用」；del 只删名字，容器里的引用还在。",
    "analogy": "内存像水箱，引用是水龙头，del 只关一个水龙头，水箱要等所有水龙头关了才空。",
    "why": "长跑服务内存持续上涨最终 OOM，是线上常见事故。",
    "mechanism": [
      "① Python 用引用计数为主 + 分代 GC 为辅，无限循环引用靠 GC 兜底",
      "② 泄漏真因通常是「意料外的引用」：全局容器堆积、闭包持有、异常未关闭资源",
      "③ ⚠️ del 只删除变量名（减引用），如果列表里还有引用，数据不会释放",
      "④ 排查用 tracemalloc / objgraph 找谁分配了内存、谁持有引用",
      "⑤ 循环引用只能靠 gc.collect() 手动触发（gc 默认自动跑但有阈值）",
      "⑥ 大量小对象用__slots__ 减少实例字典开销"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "对象分配",
        "引用+1",
        "del/出作用域",
        "引用归零才释放"
      ],
      "frames": [
        {
          "s": 0,
          "note": "分配对象引用计数为1"
        },
        {
          "s": 1,
          "note": "被多处引用计数增加"
        },
        {
          "s": 2,
          "note": "del 只减一处"
        },
        {
          "s": 3,
          "note": "必须所有引用都释放才回收"
        }
      ]
    },
    "interviewQ": [
      "Python 内存泄漏怎么排查？",
      "del 为什么有时候没用？",
      "__slots__ 有什么用？"
    ],
    "keywords": [
      "内存",
      "泄漏",
      "引用计数",
      "tracemalloc",
      "objgraph",
      "slots"
    ],
    "scene": [
      "一个后台任务队列越跑越大，列表里堆积了一堆任务对象没释放。",
      "面试被问「Python 会内存泄漏吗」，答引用计数+GC 能回收，但意料外的引用会泄漏。"
    ],
    "tags": [
      "内存",
      "性能",
      "GC"
    ],
    "related": [
      {
        "id": "python-gc-generations",
        "kind": "extends",
        "note": "分代 GC 是循环引用的兜底"
      },
      {
        "id": "fe-weakref",
        "kind": "compare",
        "note": "弱引用是防泄漏的一种手段"
      }
    ]
  },
  {
    "id": "python-gc-generations",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "性能",
      "垃圾回收"
    ],
    "title": "Python 的分代 GC 是怎么工作的？为什么关了会内存涨？",
    "oneLine": "引用计数为主，分代 GC 兜底循环引用；新生代频繁回收、老生代很少回收以省时间。",
    "analogy": "像整理房间：新 messes 马上扫（新生代），老角落偶尔扫（老生代），不动手就一直乱。",
    "why": "理解它能解释「为什么内存会涨」以及「什么时候该手动 gc.collect()」。",
    "mechanism": [
      "① 引用计数为主：计数归零立即回收，不用等 GC",
      "② 循环引用（互相引用但外部不可达）引用计数永不归零→ 需要分代 GC",
      "③ 分代：0代新对象频繁回收，1代晋升，2代老对象很少回收",
      "④ 分代依据「幸存者」——活过多次回收的更可能长期存活，放老生代省扫描成本",
      "⑤ ⚠️ 关掉 gc 后循环引用永不回收，长跑服务内存会持续涨",
      "⑥ 大量不可变对象（如大量字符串/元组）可以安全关gc 提升性能"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "新对象入0代",
        "频繁扫描0代",
        "幸存晋升1代",
        "很少扫描2代"
      ],
      "frames": [
        {
          "s": 0,
          "note": "新分配对象进新生代"
        },
        {
          "s": 1,
          "note": "新生代频繁但只扫少量"
        },
        {
          "s": 2,
          "note": "活下来晋升老生代"
        },
        {
          "s": 3,
          "note": "老生代很少扫，降低开销"
        }
      ]
    },
    "interviewQ": [
      "Python 为什么还需要分代 GC？",
      "什么情况下可以关闭 GC？",
      "循环引用为什么引用计数回收不了？"
    ],
    "keywords": [
      "GC",
      "分代",
      "循环引用",
      "引用计数",
      "gc.collect"
    ],
    "scene": [
      "调高 GC 阈值后处理速度提升了 30%——原来频繁扫描新生代开销大。",
      "面试被问「Python 内存机制」，答引用计数为主 + 分代 GC 兜底循环引用。"
    ],
    "tags": [
      "GC",
      "内存",
      "性能"
    ],
    "related": [
      {
        "id": "python-memory-leak",
        "kind": "extends",
        "note": "分代 GC 是内存管理的一部分"
      }
    ]
  },
  {
    "id": "python-cprofile",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "性能",
      "性能剖析"
    ],
    "title": "Python 怎么定位性能瓶颈？为什么不能凭直觉猜？",
    "oneLine": "先用 cProfile 找到最耗时的函数，再用 py-spy 定位具体行；直觉经常猜错方向。",
    "analogy": "病人看病要先量体温血压，不能凭「我觉得是感冒」就开药。",
    "why": "性能优化最贵的成本是「优化错地方」——白花时间还引入 bug。",
    "mechanism": [
      "① cProfile 统计函数级调用次数和耗时，找出热点",
      "② ⚠️ cProfile 本身有开销（记录每次调用），别在生产开",
      "③ line_profiler 精确到行；py-spy 无侵入采样，生产可用",
      "④ 常见误判：以为慢在业务逻辑，其实慢在 N+1 查询或序列化",
      "⑤ 先测后改（先有基线），改完再测对比——没有基线的优化无法证明有效",
      "⑥ cProfile 输出能用 snakeviz / flamegraph 可视化"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "跑cProfile",
        "找热点函数",
        "line_profiler定位",
        "优化后对比"
      ],
      "frames": [
        {
          "s": 0,
          "note": "先量化，别凭直觉"
        },
        {
          "s": 1,
          "note": "cProfile 找函数级热点"
        },
        {
          "s": 2,
          "note": "定位到具体行"
        },
        {
          "s": 3,
          "note": "优化后要有对比数据"
        }
      ]
    },
    "interviewQ": [
      "Python 怎么分析性能？",
      "cProfile 有开销吗？",
      "为什么优化前要先测？"
    ],
    "keywords": [
      "性能",
      "cProfile",
      "py-spy",
      "profiling",
      "热点",
      "line_profiler"
    ],
    "scene": [
      "以为卡在正则匹配，profile 出来 90% 时间在数据库往返——N+1 查询。",
      "面试被问「怎么优化性能」，答先 profiling 定位瓶颈再改，凭直觉容易白干。"
    ],
    "tags": [
      "性能",
      "工具",
      "profiling"
    ],
    "related": [
      {
        "id": "python-tooling",
        "kind": "extends",
        "note": "性能剖析是工程化工具链一环"
      }
    ]
  },
  {
    "id": "python-dataclass",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "面向对象",
      "dataclass 与枚举"
    ],
    "title": "dataclass 和 Enum 各自解决什么问题？",
    "oneLine": "dataclass 自动生成 __init__/__repr__/__eq__ 简化数据类；Enum 定义有限取值集合防拼写错误。",
    "analogy": "dataclass 像自动帮你写好样板代码的数据表；Enum 像一份固定的选项清单。",
    "why": "减少样板代码 + 用可读常量代替魔法字符串，提升可维护性。",
    "mechanism": [
      "① @dataclass 自动生成 __init__、__repr__、__eq__，只声明字段",
      "② frozen=True 不可变（可哈希）；slots=True 省内存",
      "③ field(default_factory=list) 处理可变默认值（不能用 list 默认值）",
      "④ ⚠️ dataclass 默认不处理可变默认值，要用 default_factory",
      "⑤ Enum 定义有限选项，用Color.RED 而不是魔法字符串 'red'",
      "⑥ Enum 成员不可变、可哈希，适合做常量；str Enum 还能直接当字符串用"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "dataclass",
          "lines": [
            "@dataclass",
            "声明字段即可",
            "自动生成魔法方法"
          ],
          "note": "省样板"
        },
        {
          "title": "Enum",
          "lines": [
            "class Status(Enum)",
            "Status.DONE",
            "防拼写错"
          ],
          "note": "有限选项"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "data类省样板代码"
        },
        {
          "s": 1,
          "note": "Enum 用常量替魔法字符串"
        }
      ]
    },
    "interviewQ": [
      "dataclass 省了什么代码？",
      "可变默认值为什么要 default_factory？",
      "Enum 相比常量字符串的优势？"
    ],
    "keywords": [
      "dataclass",
      "Enum",
      "枚举",
      "frozen",
      "default_factory"
    ],
    "scene": [
      "写数据类时手写 __init__ 十几个字段，改一个字段要动两处。",
      "状态机用魔法字符串'pending'，手拼错了不报错排查半天。"
    ],
    "tags": [
      "面向对象",
      "语法",
      "数据结构"
    ],
    "related": [
      {
        "id": "python-oop-dunder",
        "kind": "extends",
        "note": "dataclass 自动生成魔术方法"
      }
    ]
  },
  {
    "id": "python-iter-yield",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "性能",
      "迭代器与大对象"
    ],
    "title": "yield 和 return 有什么区别？生成器什么时候比列表快？",
    "oneLine": "yield 逐个产出并保留状态（省内存），return 一次性返回全部结果；数据大时生成器优势明显。",
    "analogy": "return 像把一整车货一次交付，yield 像一辆辆送，货主不用全囤着。",
    "why": "处理大数据（文件、日志、大列表）时生成器避免一次性占满内存。",
    "mechanism": [
      "① yield 使函数成为生成器，返回值是生成器对象，执行到yield才暂停",
      "② return 结束生成器（StopIteration），一次 return 后函数就结束了",
      "③ 生成器省内存：不需要把全部结果存进列表，边算边产出",
      "④ ⚠️ 生成器只能遍历一次（耗尽后再 for 无输出），要复用得重新创建或转列表",
      "⑤ yield from 可委托给另一个生成器/可迭代对象，实现递归迭代",
      "⑥ 大文件逐行处理、CSV 流式解析都用生成器避免撑爆内存"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "y1",
          "label": "调用生成器"
        },
        {
          "id": "y2",
          "label": "执行到yield挂起"
        },
        {
          "id": "y3",
          "label": "返回一个值"
        },
        {
          "id": "y4",
          "label": "继续下次执行"
        }
      ],
      "edges": [
        {
          "from": "y1",
          "to": "y2"
        },
        {
          "from": "y2",
          "to": "y3"
        },
        {
          "from": "y3",
          "to": "y4",
          "label": "下次next()"
        },
        {
          "from": "y4",
          "to": "y2",
          "label": "继续"
        }
      ],
      "frames": [
        {
          "note": "调用不执行，只创建生成器",
          "n": "y1"
        },
        {
          "note": "next() 才执行到第一个 yield",
          "n": "y2"
        },
        {
          "note": "每次产出一个值",
          "n": "y3"
        },
        {
          "note": "用完内存就释放，不囤数据",
          "n": "y4"
        }
      ]
    },
    "interviewQ": [
      "yield 和 return 区别？",
      "生成器什么时候比列表快？",
      "什么是 yield from？"
    ],
    "keywords": [
      "生成器",
      "yield",
      "迭代器",
      "惰性求值",
      "内存"
    ],
    "scene": [
      "读一个 10GB 的日志文件，用 readlines 内存爆了，改成逐行 yield 稳了。",
      "面试被问「生成器的好处」，答惰性求值省内存，且能处理无限序列。"
    ],
    "tags": [
      "性能",
      "迭代",
      "内存"
    ],
    "related": [
      {
        "id": "python-generator",
        "kind": "extends",
        "note": "生成器基础概念"
      }
    ]
  },
  {
    "id": "python-copy-deepcopy",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "性能",
      "拷贝与内存"
    ],
    "title": "浅拷贝和深拷贝有什么区别？为什么嵌套列表用 copy 会联动？",
    "oneLine": "浅拷贝只复制外层容器（内层还是同一对象），深拷贝递归复制所有层。",
    "analogy": "浅拷贝像复印一份目录（条目指向原书），深拷贝才是把每本书也复印一份。",
    "why": "误用浅拷贝会导致改一个影响另一个，是常见的隐蔽 bug。",
    "mechanism": [
      "① copy.copy / [:] / list() 是浅拷贝：只复制一层，内层对象共享",
      "② copy.deepcopy 递归复制所有层，包含嵌套的列表/字典/自定义对象",
      "③ ⚠️ 坑：[[1,2],[3,4]] 做浅拷贝后改 a[0][0]，b[0][0] 也变（共享内层列表）",
      "④ 基本类型（int/str/tuple）不涉及拷贝问题（不可变）",
      "⑤ deepcopy 对不可拷贝对象（文件句柄、连接）会失败，需自定义 __deepcopy__",
      "⑥ 性能：deepcopy 开销大，浅拷贝能解决就别深拷贝"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "浅拷贝",
          "lines": [
            "a[0] ──→ 列表X",
            "b[0] ──→ 列表X"
          ],
          "note": "共享内层"
        },
        {
          "title": "深拷贝",
          "lines": [
            "a[0] → 列表X",
            "b[0] → 列表Y"
          ],
          "note": "各自独立"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "浅拷贝共享内层对象"
        },
        {
          "s": 1,
          "note": "深拷贝各层独立"
        }
      ]
    },
    "interviewQ": [
      "浅拷贝和深拷贝区别？",
      "为什么嵌套列表浅拷贝会联动？",
      "什么对象不能 deepcopy？"
    ],
    "keywords": [
      "拷贝",
      "deepcopy",
      "浅拷贝",
      "引用",
      "内存"
    ],
    "scene": [
      "复制配置列表后改一项，另一份也变了——嵌套结构用了浅拷贝。",
      "面试被问「深拷贝代价」，答递归所有层，大对象开销大，能浅就浅。"
    ],
    "tags": [
      "性能",
      "内存",
      "对象"
    ],
    "related": [
      {
        "id": "py-mutable-default",
        "kind": "extends",
        "note": "可变/不可变决定拷贝行为"
      }
    ]
  },
  {
    "id": "python-logging",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "工程化",
      "日志"
    ],
    "title": "为什么用 logging 而不是 print？",
    "oneLine": "logging 有级别、格式、时间戳、可输出到文件/远程，且可配置；print 只适合调试临时输出。",
    "analogy": "print 像是随便写在纸上，logging 像正式的日志系统（分级、归档、可检索）。",
    "why": "线上问题排查需要按级别过滤、留存记录，print 做不到。",
    "mechanism": [
      "① logging 分级别：DEBUG/INFO/WARNING/ERROR/CRITICAL，可按需过滤",
      "② 结构化输出：时间、级别、模块、消息，便于检索定位",
      "③ 可同时输出到控制台和文件（Handler），还能发到远程",
      "④ root logger + 模块 logger 的层级结构，模块只管用不用管配置",
      "⑤ ⚠️ print 没有级别，线上 DEBUG 信息全打出来反而淹没关键错误",
      "⑥ ⚠️ 基本配置用 basicConfig 只在未配置时生效，库代码不要调，改用 getLogger"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "log.info调用",
        "级别过滤",
        "Formatter格式化",
        "Handler输出"
      ],
      "frames": [
        {
          "s": 0,
          "note": "模块调getLogger 不自己配"
        },
        {
          "s": 1,
          "note": "按级别过滤"
        },
        {
          "s": 2,
          "note": "加时间/级别/模块"
        },
        {
          "s": 3,
          "note": "输出到文件/控制台/远程"
        }
      ]
    },
    "interviewQ": [
      "logging 相比 print 的优势？",
      "为什么库代码不该调 basicConfig？",
      "什么是结构化日志？"
    ],
    "keywords": [
      "logging",
      "日志",
      "级别",
      "Handler",
      "Formatter",
      "root"
    ],
    "scene": [
      "线上排查问题翻日志，一屏print 的调试信息把 ERROR 冲没了。",
      "面试被问「怎么规范打日志」，答用 logging、库只getLogger 不配置级别。"
    ],
    "tags": [
      "工程化",
      "日志",
      "可观测"
    ],
    "related": [
      {
        "id": "python-tooling",
        "kind": "extends",
        "note": "日志规范是工程化一环"
      }
    ]
  },
  {
    "id": "python-virtualenv-pip",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "工程化",
      "依赖管理工具"
    ],
    "title": "pip、pip-tools、uv、poetry 有什么区别？",
    "oneLine": "pip 是安装器，poetry/uv 是依赖管理+锁定工具，pip-tools 用 requirements 文件做锁定。",
    "analogy": "pip 是「能装就行」的工具箱，uv/poetry 是「装好并锁住版本」的项目管家。",
    "why": "依赖管理是 Python 项目可重现的基础，工具选错会导致部署失败。",
    "mechanism": [
      "① pip install 直接装，不管版本 → 可能装到不兼容的新版",
      "② 锁文件（requirements.txt 里写 == 版本 / uv.lock / poetry.lock）保证可重现",
      "③ pip-tools 从 pyproject 生成锁定的 requirements.txt",
      "④ uv 是新工具（Rust 写），比 pip 快一个数量级，能替代 pip+venv+pip-tools",
      "⑤ poetry 统一管理依赖+虚拟环境+打包，声明式体验好",
      "⑥ ⚠️ 团队项目必须提交锁文件，否则「你本地能跑我这跑不了」"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "pip",
          "lines": [
            "能装",
            "不管版本"
          ],
          "note": "安装器"
        },
        {
          "title": "uv",
          "lines": [
            "装+锁+建环境",
            "快"
          ],
          "note": "一站式"
        },
        {
          "title": "poetry",
          "lines": [
            "声明式依赖",
            "锁文件"
          ],
          "note": "项目管理"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "工具定位不同"
        },
        {
          "s": 1,
          "note": "关键是锁不锁版本"
        }
      ]
    },
    "interviewQ": [
      "为什么需要锁文件？",
      "uv 相比 pip 快在哪？",
      "poetry 和 pip 的区别？"
    ],
    "keywords": [
      "pip",
      "uv",
      "poetry",
      "依赖管理",
      "锁文件",
      "pip-tools"
    ],
    "scene": [
      "同事拉代码跑不起来，就是没提交锁文件。",
      "面试被问「Python 依赖管理怎么做」，答 pyproject 声明 +锁文件 +venv 隔离。"
    ],
    "tags": [
      "工程化",
      "依赖",
      "工具"
    ],
    "related": [
      {
        "id": "python-tooling",
        "kind": "extends",
        "note": "依赖工具是工程化核心"
      }
    ]
  },
  {
    "id": "python-serialization",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "工程化",
      "序列化"
    ],
    "title": "pickle 有什么安全风险？为什么反序列化不可信数据很危险？",
    "oneLine": "pickle 反序列化能执行任意代码，只能用于可信数据；跨系统/跨语言用 JSON。",
    "analogy": "pickle 像「能还原成任何东西的机器」，给它一个坏数据它就可能执行恶意指令。",
    "why": "这是真实的安全漏洞来源，面试常问。",
    "mechanism": [
      "① pickle 序列化的是**字节码/状态**，不只是数据 → 反序列化时可触发 __reduce__ 执行任意代码",
      "② ⚠️ 反序列化不可信 pickle = 远程代码执行（RCE），这是真实攻击面",
      "③ JSON 只序列化数据结构（dict/list/str），不执行代码 → 跨系统安全",
      "④ Python 特有类型（datetime/decimal/自定义类）JSON 存不下，需自定义编码",
      "⑤ 性能：pickle 二进制更快更大，JSON 文本可读但慢；msgpack 是折中",
      "⑥ 跨语言/发前端用 JSON，Python 内部缓存可用 pickle（自建、可信）"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "接收不可信数据",
        "pickle.loads",
        "执行__reduce__",
        "任意代码执行"
      ],
      "frames": [
        {
          "s": 0,
          "note": "不可信来源的数据"
        },
        {
          "s": 1,
          "note": "pickle 反序列化会重建对象"
        },
        {
          "s": 2,
          "note": "重建过程可触发任意代码"
        },
        {
          "s": 3,
          "note": "→ 远程代码执行"
        }
      ]
    },
    "interviewQ": [
      "pickle 有什么安全风险？",
      "为什么 JSON 更安全但类型受限？",
      "什么时候可以放心用 pickle？"
    ],
    "keywords": [
      "pickle",
      "序列化",
      "安全",
      "RCE",
      "JSON",
      "msgpack"
    ],
    "scene": [
      "加载用户上传的 pkl 文件直接执行了恶意代码——pickle 反序列化的经典漏洞。",
      "面试被问「为什么不用 pickle 传数据」，答能执行代码 + 跨语言不支持。"
    ],
    "tags": [
      "安全",
      "序列化",
      "工程化"
    ],
    "related": [
      {
        "id": "python-tooling",
        "kind": "extends",
        "note": "序列化是工程化常见场景"
      }
    ]
  }
];
if (typeof module !== "undefined" && module.exports) {
  module.exports = CARDS_PY_ADV;
}