// 自动生成于 2026-09-29 by scripts/gen_cards.py（大纲批量造卡）。
// 机器产出，人工复核后可保留/删改；此文件由 git 管理，属「内容」不是「状态」。
var CARDS_PYTHON = [
  {
    "id": "python-gil",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "GIL 全局解释器锁与多线程"
    ],
    "title": "Python 多线程为什么不能真正并行？",
    "oneLine": "GIL 是 Python 的全局锁，限制了多线程的并行执行。",
    "analogy": "只能一个人使用公共电话亭，其他人必须排队等待。",
    "why": "防止多线程同时操作内存导致数据混乱和崩溃。",
    "mechanism": [
      "① GIL 保证同一时间只有一个线程执行 Python 字节码。",
      "② 线程切换需要释放 GIL，导致实际运行时间增加。",
      "③ 默认安装的 Python 绕不开 GIL，多线程无法真正并行（PEP 703 的 free-threaded 构建可去掉 GIL，但要专门装 t 版）。",
      "④ GIL 只卡 CPU 密集型：I/O 密集型（网络、文件）期间线程在等 I/O，多线程依然有效。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "GIL 限制",
        "线程切换",
        "执行字节码"
      ],
      "frames": [
        {
          "s": 0,
          "note": "GIL 阻止多线程同时执行 Python 字节码"
        },
        {
          "s": 1,
          "note": "线程必须释放 GIL 才能切换执行"
        },
        {
          "s": 2,
          "note": "默认构建绕不开 GIL，多线程无法真正并行"
        }
      ]
    },
    "interviewQ": [
      "GIL 能被绕过吗？free-threaded 版本是怎么回事？",
      "多线程在 Python 中的应用场景有哪些？"
    ],
    "keywords": [
      "GIL",
      "多线程",
      "字节码",
      "并行"
    ],
    "scene": [
      "在高并发场景下，Python 多线程效率不高，需使用多进程。",
      "使用多线程处理 I/O 密集型任务，如网络请求和文件读写。"
    ],
    "tags": [
      "并发",
      "线程",
      "性能"
    ],
    "related": [
      {
        "id": "python-free-threading",
        "kind": "extends",
        "note": "免 GIL 的实现是理解 GIL 限制的延伸"
      },
      {
        "id": "java-virtual-threads",
        "kind": "compare",
        "note": "对比 Python 与 Java 的多线程实现方式"
      },
      {
        "id": "java-redisq27",
        "kind": "compare",
        "note": "对比 Redis 与 Python 的多线程限制"
      },
      {
        "id": "java-redis-multithread-after-6",
        "kind": "compare",
        "note": "对比 Redis 与 Python 的多线程演进"
      },
      {
        "id": "python-decorator",
        "kind": "compare",
        "note": "对比函数增强与多线程限制的机制"
      }
    ]
  },
  {
    "id": "python-gc",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "垃圾回收与引用计数"
    ],
    "title": "Python 如何自动回收内存？",
    "oneLine": "Python 通过引用计数和垃圾回收机制自动管理内存。",
    "analogy": "图书馆归还书籍后，管理员会定期清理书架上的空位。",
    "why": "防止内存泄漏，提高程序的稳定性和性能。",
    "mechanism": [
      "① 引用计数跟踪对象的引用数量，当为 0 时释放内存。",
      "② 循环引用会导致内存泄漏，需垃圾回收器（GC）介入。",
      "③ GC 会检测循环引用，将内存归还给系统。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "引用计数",
        "循环引用",
        "垃圾回收"
      ],
      "frames": [
        {
          "s": 0,
          "note": "引用计数跟踪对象引用，无引用即回收"
        },
        {
          "s": 1,
          "note": "循环引用未被引用计数识别，需垃圾回收处理"
        },
        {
          "s": 2,
          "note": "GC 检测并清理循环引用，释放内存"
        }
      ]
    },
    "interviewQ": [
      "Python 的垃圾回收机制有哪些？",
      "如何检测和处理循环引用？"
    ],
    "keywords": [
      "引用计数",
      "垃圾回收",
      "循环引用",
      "内存管理"
    ],
    "scene": [
      "在大型项目中，频繁创建和销毁对象可能导致内存问题。",
      "使用弱引用或垃圾回收器处理循环引用，防止内存泄漏。"
    ],
    "tags": [
      "内存管理",
      "垃圾回收",
      "引用计数"
    ],
    "related": [
      {
        "id": "java-garbage-collection-algorithm",
        "kind": "compare",
        "note": "对比 Python 与 Java 的垃圾回收机制"
      },
      {
        "id": "python-asyncio",
        "kind": "compare",
        "note": "对比内存管理与异步编程的资源管理方式"
      },
      {
        "id": "python-contextmanager",
        "kind": "compare",
        "note": "对比内存回收与资源管理的机制"
      },
      {
        "id": "python-decorator",
        "kind": "compare",
        "note": "对比内存管理与函数增强的实现方式"
      },
      {
        "id": "python-generator",
        "kind": "compare",
        "note": "生成器减少内存占用，与垃圾回收机制共同作用，对比看内存管理全貌"
      }
    ]
  },
  {
    "id": "python-decorator",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "装饰器原理"
    ],
    "title": "Python 装饰器如何实现函数增强？",
    "oneLine": "装饰器通过闭包和函数包装实现函数的动态增强。",
    "analogy": "在快递包裹上贴标签，无需修改包裹内容即可增加功能。",
    "why": "提升代码复用性和可读性，简化函数装饰逻辑。",
    "mechanism": [
      "① 装饰器本质上是一个函数，接收被装饰函数作为参数。",
      "② 装饰器返回一个新函数，用于包裹原始函数的执行。",
      "③ 使用 @ 符号语法糖，将函数赋值给新函数。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "装饰器定义",
        "函数包裹",
        "语法糖应用"
      ],
      "frames": [
        {
          "s": 0,
          "note": "装饰器函数接收原始函数作为参数"
        },
        {
          "s": 1,
          "note": "装饰器返回一个包裹原始函数的新函数"
        },
        {
          "s": 2,
          "note": "使用 @ 符号语法糖，将函数赋值给新函数"
        }
      ]
    },
    "interviewQ": [
      "装饰器的执行顺序如何？",
      "如何实现一个带参数的装饰器？"
    ],
    "keywords": [
      "闭包",
      "函数包装",
      "语法糖",
      "装饰器"
    ],
    "scene": [
      "在 API 接口中，使用装饰器统一处理请求日志和认证。",
      "在大型项目中，通过装饰器实现日志记录和性能监控。"
    ],
    "tags": [
      "函数增强",
      "语法糖",
      "闭包"
    ],
    "related": [
      {
        "id": "python-generator",
        "kind": "compare",
        "note": "对比函数增强与惰性求值的实现方式"
      },
      {
        "id": "python-asyncio",
        "kind": "compare",
        "note": "对比函数增强与异步编程的实现方式"
      },
      {
        "id": "python-gc",
        "kind": "compare",
        "note": "对比函数增强与内存管理的机制"
      },
      {
        "id": "python-gil",
        "kind": "compare",
        "note": "对比函数增强与多线程限制的机制"
      },
      {
        "id": "python-contextmanager",
        "kind": "extends",
        "note": "装饰器是理解上下文管理器机制的基础，装饰器帮助实现上下文管理器的函数增强"
      }
    ]
  },
  {
    "id": "python-generator",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "生成器与迭代器协议"
    ],
    "title": "生成器如何实现惰性求值？",
    "oneLine": "生成器通过 yield 关键字实现惰性求值，减少内存占用。",
    "analogy": "像一个自动售货机，按需提供商品，不一次性全部取出。",
    "why": "减少内存占用，适合处理大数据集和大数据流。",
    "mechanism": [
      "① 使用 yield 关键字将函数转换为生成器，每次调用返回一个值。",
      "② 生成器保存执行状态，下次调用继续从上次中断的位置执行。",
      "③ 生成器通过迭代器协议实现对数据流的控制。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "yield 调用",
        "生成器状态保存",
        "迭代器协议"
      ],
      "frames": [
        {
          "s": 0,
          "note": "yield 关键字将函数转换为生成器，每次返回一个值"
        },
        {
          "s": 1,
          "note": "生成器保存执行状态，下次调用继续从上次中断的位置执行"
        },
        {
          "s": 2,
          "note": "生成器通过迭代器协议实现对数据流的控制"
        }
      ]
    },
    "interviewQ": [
      "生成器与迭代器有何区别？",
      "如何使用生成器处理大数据集？"
    ],
    "keywords": [
      "yield",
      "惰性求值",
      "迭代器协议",
      "生成器"
    ],
    "scene": [
      "在爬虫项目中，使用生成器逐行处理网页内容，节省内存。",
      "处理大数据流时，使用生成器避免一次性加载全部数据。"
    ],
    "tags": [
      "内存优化",
      "惰性求值",
      "迭代器"
    ],
    "related": [
      {
        "id": "python-decorator",
        "kind": "prereq",
        "note": "装饰器是理解生成器机制的基础，装饰器帮助实现生成器的函数增强"
      },
      {
        "id": "python-asyncio",
        "kind": "compare",
        "note": "生成器和异步编程都涉及非阻塞操作，对比看不同方式的并发实现"
      },
      {
        "id": "python-gc",
        "kind": "compare",
        "note": "生成器减少内存占用，与垃圾回收机制共同作用，对比看内存管理全貌"
      },
      {
        "id": "python-deferred-annotations",
        "kind": "compare",
        "note": "生成器和延迟求值都涉及惰性处理，对比看不同场景下的惰性实现"
      },
      {
        "id": "python-contextmanager",
        "kind": "compare",
        "note": "生成器和上下文管理器都涉及资源控制，对比看如何管理不同类型的资源"
      }
    ]
  },
  {
    "id": "python-contextmanager",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "上下文管理器 with"
    ],
    "title": "with 语句如何管理资源？",
    "oneLine": "with 语句通过上下文管理器实现资源的自动释放。",
    "analogy": "像在图书馆借书，使用后自动归还，无需手动操作。",
    "why": "防止资源泄漏，提高代码的健壮性和可读性。",
    "mechanism": [
      "① 上下文管理器通过 __enter__ 和 __exit__ 方法控制资源。",
      "② with 语句在进入代码块时调用 __enter__，离开时调用 __exit__。",
      "③ 资源在 __exit__ 中释放，确保即使出错也能正确关闭。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "with 语句",
        "资源获取",
        "资源释放"
      ],
      "frames": [
        {
          "s": 0,
          "note": "with 语句在进入代码块时调用 __enter__ 方法"
        },
        {
          "s": 1,
          "note": "执行代码块，使用资源"
        },
        {
          "s": 2,
          "note": "离开代码块时调用 __exit__，释放资源"
        }
      ]
    },
    "interviewQ": [
      "上下文管理器如何实现资源释放？",
      "如何自定义上下文管理器？"
    ],
    "keywords": [
      "__enter__",
      "__exit__",
      "资源管理",
      "with"
    ],
    "scene": [
      "在文件操作中，使用 with 确保文件在使用后自动关闭。",
      "在网络连接中，使用 with 确保连接在使用后自动释放。"
    ],
    "tags": [
      "资源管理",
      "上下文管理器",
      "with"
    ],
    "related": [
      {
        "id": "python-gc",
        "kind": "compare",
        "note": "上下文管理器释放资源，与垃圾回收机制共同作用，对比看内存管理全貌"
      },
      {
        "id": "python-asyncio",
        "kind": "compare",
        "note": "上下文管理器和异步编程都涉及非阻塞操作，对比看不同方式的并发实现"
      },
      {
        "id": "python-generator",
        "kind": "compare",
        "note": "上下文管理器和生成器都涉及资源控制，对比看不同资源管理方式"
      },
      {
        "id": "python-decorator",
        "kind": "prereq",
        "note": "装饰器是理解上下文管理器机制的基础，装饰器帮助实现上下文管理器的函数增强"
      },
      {
        "id": "python-deferred-annotations",
        "kind": "compare",
        "note": "上下文管理器和延迟求值都涉及惰性处理，对比看不同场景下的惰性实现"
      }
    ]
  },
  {
    "id": "python-asyncio",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "异步 asyncio 与协程"
    ],
    "title": "asyncio 如何实现异步编程？",
    "oneLine": "asyncio 基于协程实现异步 I/O，提高单线程效率。",
    "analogy": "像一个人同时做多件事情，按需切换任务，不等待完成。",
    "why": "提高 I/O 密集型任务的效率，减少线程开销。",
    "mechanism": [
      "① 使用 async 和 await 关键字定义协程，等待 I/O 操作时让出控制。",
      "② asyncio 事件循环管理协程的调度，按需切换任务。",
      "③ 协程在等待 I/O 时让出 CPU，其他任务可以继续执行。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "协程定义",
        "事件循环",
        "任务切换"
      ],
      "frames": [
        {
          "s": 0,
          "note": "async 和 await 关键字定义协程，等待 I/O 时让出控制"
        },
        {
          "s": 1,
          "note": "asyncio 事件循环管理协程的调度，按需切换任务"
        },
        {
          "s": 2,
          "note": "协程在等待 I/O 时让出 CPU，其他任务继续执行"
        }
      ]
    },
    "interviewQ": [
      "asyncio 的事件循环如何工作？",
      "如何实现异步网络请求？"
    ],
    "keywords": [
      "async",
      "await",
      "事件循环",
      "协程"
    ],
    "scene": [
      "在 Web 服务器中，使用 asyncio 处理多个并发请求。",
      "在爬虫项目中，使用 asyncio 实现异步网络请求。"
    ],
    "tags": [
      "异步编程",
      "事件循环",
      "协程"
    ],
    "related": [
      {
        "id": "python-generator",
        "kind": "extends",
        "note": "异步编程基于生成器实现，生成器是协程的基础，理解生成器有助于理解异步编程"
      },
      {
        "id": "python-decorator",
        "kind": "prereq",
        "note": "装饰器是理解异步编程机制的基础，装饰器帮助实现异步函数的增强"
      },
      {
        "id": "python-gc",
        "kind": "compare",
        "note": "异步编程涉及内存管理，与垃圾回收机制共同作用，对比看内存管理全貌"
      },
      {
        "id": "python-contextmanager",
        "kind": "compare",
        "note": "异步编程和上下文管理器都涉及非阻塞操作，对比看不同方式的并发实现"
      },
      {
        "id": "python-deferred-annotations",
        "kind": "compare",
        "note": "异步编程和延迟求值都涉及惰性处理，对比看不同场景下的惰性实现"
      }
    ]
  }
];

if (typeof module !== "undefined" && module.exports) { module.exports = CARDS_PYTHON; }
