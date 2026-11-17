// 2026-10-03 追加：Python 基础语法与内置机制（8 张）。
//
// 为什么补这个：data/gen_python.js 原来只有 6 张卡，全是「机制层」
// （GIL / GC / 装饰器 / 生成器 / 上下文管理器 / asyncio），**没有一张
// 讲语法和内置数据结构的**。结果是：学的人会讲 GIL，却答不出
// 「可变默认参数为什么危险」「`is` 和 `==` 差在哪」——而这些是
// 面试和真实 bug 里出现频率最高的部分。
//
// 每张卡的取舍标准：**踩过坑 or 面试问过**才写。Python 语法本身不缺，
// 缺的是那些「看起来会写、实际说清原理就答不上」的点。
var CARDS_PYTHON_BASIC = [
  {
    "id": "py-mutable-default",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "函数参数与作用域"
    ],
    "tags": [
      "参数",
      "作用域",
      "坑"
    ],
    "title": "可变默认参数为什么只创建一次？",
    "oneLine": "默认参数在**函数定义时求值一次**，不是每次调用时求值 —— 所以 `def f(x=[])` 会让所有调用共享同一个列表。",
    "analogy": "像给函数配了一个默认行李箱。行李箱是**买函数时**就准备好的，不是每次调用现取一个空的 —— 你往里放东西，用过的人再打开，箱子还是满的。",
    "why": "这是 Python 最高频的隐蔽 bug 来源之一。函数签名写在模块顶层，函数对象只创建一次，默认值也就跟着定了那个唯一一份。",
    "mechanism": [
      "① 函数定义执行的那一刻，Python 就把默认值对象**计算好并放进函数对象的 `__defaults__` 属性**里。",
      "② 之后每次调用传参时，是把调用者的实参**赋值**给形参变量；没传实参就用 `__defaults__` 里那份。",
      "③ 所以 `__defaults__` 里的那个列表是全局唯一的，每次调用都在往**同一个对象**上 append。",
      "④ `def f(x=[])` 的第二、第三次调用会看到第一调用留下的东西 —— 不是「默认值被改了」，是「大家共用同一个对象」。",
      "⑤ 正确写法是 `def f(x=None): if x is None: x = []`：`None` 是不可变单例，每次调用都传同一个，但**判断后重新绑定**一个全新的列表。",
      "⑥ 顺带一提：`def f(x=[])` 之所以不报错，是因为 Python 只有「可变 vs 不可变」之分，没有 Java 那种「对象 vs 基本类型」的 overload 检查。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "定义时求值",
        "存入 defaults",
        "调用共用"
      ],
      "frames": [
        {
          "s": 0,
          "note": "函数定义那一行执行，[] 立刻被创建成唯一对象"
        },
        {
          "s": 1,
          "note": "该列表存进函数对象的 __defaults__，全程只有这一份"
        },
        {
          "s": 2,
          "note": "每次调用不传实参就复用它 → 跨调用累积数据"
        }
      ]
    },
    "interviewQ": [
      "为什么 `def f(x=[])` 不报错，而 `def f(x=[])` 改一下就变成 bug 了？",
      "可变默认参数和 `None` 哨兵分别用在什么场景？"
    ],
    "keywords": [
      "可变默认参数",
      "默认值",
      "__defaults__",
      "None",
      "作用域"
    ],
    "scene": [
      "写缓存/收集器函数时踩过：第一次调用塞进去的数据，第二次调用还在，于是「清空缓存」清不干净。",
      "面试高频题。答不出原理只说「因为默认值只求值一次」通常不够，要能说出对象唯一性和 None 哨兵的区别。"
    ],
    "related": [
      {
        "id": "python-decorator",
        "kind": "prereq",
        "note": "装饰器包装函数时同样要处理默认参数，否则被装饰函数的默认值会被共享"
      },
      {
        "id": "py-scope-closure",
        "kind": "extends",
        "note": "默认参数绑定发生在定义时，闭包捕获发生在运行时，两者时机不同"
      },
      {
        "id": "py-dict-keys",
        "kind": "compare",
        "note": "可变对象不能当 dict 键，与默认参数里放可变对象是同一类陷阱"
      }
    ]
  },
  {
    "id": "py-is-vs-eq",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "数据模型与比较"
    ],
    "tags": [
      "比较",
      "数据模型",
      "坑"
    ],
    "title": "`is` 和 `==` 到底差在哪？",
    "oneLine": "`==` 调 `__eq__` 比**值**，`is` 比**是不是同一个对象**（内存地址）。小整数/短字符串因驻留缓存会出现 `is` 为真但看起来像巧合。",
    "analogy": "`==` 是「两本《深入理解计算机系统》第 3 版内容一样吗」，`is` 是「这两本书是不是同一本」。内容可能一样，但是两本不同的书。",
    "why": "把 `==` 写成 `is`（或反过来）在处理 None、小整数、NaN 时会得到反直觉结果，是 code review 里最常见的写法问题之一。",
    "mechanism": [
      "① `a == b` 调用 `a.__eq__(b)`，默认实现逐字段比较 → 比的是**内容**。",
      "② `a is b` 直接比两个对象的 `id()`（CPython 里就是内存地址）→ 比的是**身份**。",
      "③ CPython 对小整数（-5 到 256）和短字符串做**驻留缓存**，所以 `a = 1000; b = 1000` 后 `a is b` 常常为真 —— 但这不是规范保证，换个实现或大数就不成立。",
      "④ 正确的身份判断只有一个用途：`x is None`。它是「这个变量有没有被赋值」的唯一可靠写法。",
      "⑤ 别写 `if x:` 判断 None —— `0`、`''`、`[]` 都是假值，会被一起吞掉。要区分就用 `is None` / `is not None`。",
      "⑥ `==` 有个陷阱：`float('nan') == float('nan')` 是 **False**（IEEE 754 规定 NaN 不等于任何值，包括自己）。所以 NaN 必须用 `math.isnan()` 判，不能用 `==`。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "取值比较",
        "取地址",
        "驻留缓存"
      ],
      "frames": [
        {
          "s": 0,
          "note": "== 走 __eq__，逐字段比内容"
        },
        {
          "s": 1,
          "note": "is 比 id()，即内存地址"
        },
        {
          "s": 2,
          "note": "小整数/短字符串被驻留缓存 → is 偶然为真，但不是规范保证"
        }
      ]
    },
    "interviewQ": [
      "`is None` 为什么可以，而 `== None` 不行？",
      "NaN 用 `==` 比较会得到什么结果，为什么？"
    ],
    "keywords": [
      "is",
      "==",
      "__eq__",
      "id",
      "None",
      "NaN",
      "驻留缓存"
    ],
    "scene": [
      "排查过 NaN 导致的过滤失效：`df[df['x'] == df['x']]` 恒为空，因为 NaN != NaN。",
      "读别人的代码时看到 `if item:` 然后发现它在判空 list —— 该用 `is not None`。"
    ],
    "related": [
      {
        "id": "py-mutable-default",
        "kind": "compare",
        "note": "都属基础语法里的判等/绑定陷阱，常见于同一个 code review 上下文"
      },
      {
        "id": "py-dict-keys",
        "kind": "extends",
        "note": "dict 查找同时用 hash（等价于 ==）和 eq 身份复核，理解它需要先分清 == 和 is"
      },
      {
        "id": "py-list-mutation",
        "kind": "compare",
        "note": "可变对象共享问题：同一份对象被多处引用，改一处处处变"
      }
    ]
  },
  {
    "id": "py-dict-keys",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "字典与哈希"
    ],
    "tags": [
      "dict",
      "hash",
      "性能"
    ],
    "title": "dict 查找为什么平均 O(1)？",
    "oneLine": "dict 先用 `hash(key)` 把键压成一个整数做桶定位，再在桶内用 `==` 复核身份 —— 所以键必须是**可哈希**的，且自定义类默认按**身份**而不是内容哈希。",
    "analogy": "像图书馆的索书号：先按索书号（hash）直接走到架子前，不用一本本翻；到了架前再核对书名（==）确认没拿错。",
    "why": "这是「为什么不能用 list 当 key」「为什么 dataclass 要 frozen」的根因。理解它才能解释 dict 的两个性能陷阱。",
    "mechanism": [
      "① `hash(key)` 算出一个整数，用它对桶数量取模 → 直接定位到某一个桶，**不用遍历**。",
      "② 哈希会碰撞（不同对象算出同一个 hash），所以定位到桶后还要逐个用 `==` 复核到底是不是同一个键。",
      "③ **键必须可哈希**：不可变类型（str/int/tuple/frozenset/None）都能；list/dict/set 不能，因为它们可变 —— 变了 hash 就变了，dict 内部就再也找不到这个键。",
      "④ 自定义类默认 `__hash__` 基于 `id()`，也就是**按身份**而不是内容。所以两个字段完全相同的对象会占两个键。要按内容哈希得手动写 `__hash__`（写了它就必须同时写 `__eq__`）。",
      "⑤ `@dataclass(frozen=True)` 会自动生成基于字段的 `__hash__` —— 这也是它作为 dict key 的前提。",
      "⑥ 第一个性能陷阱：字典在**扩容**时会 rehash，重hash 全部键的 `hash(key)`，开销大。所以循环里 `d.get(k) or []` 的写法（每次都建新列表）比 `setdefault` 慢很多。",
      "⑦ 第二个陷阱：`del d[k]` 不会立刻把容量还给操作系统，只是把条目标记为「dummy」，**查找仍要路过它**。大量增删后重建 dict（`d = dict(d)`）能恢复紧凑度。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "计算 hash",
        "桶定位",
        "eq 复核"
      ],
      "frames": [
        {
          "s": 0,
          "note": "hash(key) 一次算出整数，不需要遍历键"
        },
        {
          "s": 1,
          "note": "对桶数取模直接跳到某一个桶，O(1) 的来源"
        },
        {
          "s": 2,
          "note": "碰撞时在桶内用 == 逐个复核身份"
        }
      ]
    },
    "interviewQ": [
      "为什么 list 不能当 dict 的 key，而 tuple 可以？",
      "自定义类作 dict key 时，如果两个对象内容相同会怎样？"
    ],
    "keywords": [
      "dict",
      "hash",
      "哈希",
      "哈希碰撞",
      "O(1)",
      "frozen",
      "可哈希"
    ],
    "scene": [
      "排查过 `{}` 做缓存时 `d[k] = d.get(k) or []` 的性能问题，循环量大时明显卡顿。",
      "面试被问「为什么 dataclass 默认不能 hash」，答的是 frozen 的关系。"
    ],
    "related": [
      {
        "id": "py-is-vs-eq",
        "kind": "prereq",
        "note": "dict 内部同时用 hash（等价于 ==）和 eq 身份复核，先分清 == 和 is"
      },
      {
        "id": "py-list-mutation",
        "kind": "compare",
        "note": "可变对象不能当 key，根因就是 hash 会随内容变化"
      },
      {
        "id": "py-set-ops",
        "kind": "extends",
        "note": "set 是只有桶没有 value 的 dict，去重逻辑完全一样"
      }
    ]
  },
  {
    "id": "py-scope-closure",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "闭包与 LEGB"
    ],
    "tags": [
      "闭包",
      "作用域",
      "nonlocal"
    ],
    "title": "闭包为什么能记住外层的变量？",
    "oneLine": "内层函数引用的外层变量会被**编译期提升成 cell 对象**并被闭包持有 —— 所以外层函数返回后，那个变量依然活着。这也是 `nonlocal` 存在的原因。",
    "analogy": "像闭包是一个背包：你在外层函数里定义的变量被打包带走，即使外层函数已经返回退出，背包里的东西还在。",
    "why": "装饰器、回调、lambda 缓存、循环里闭包捕获变量 —— 全靠它。同时也是「循环里定义函数却全拿到最后一个值」这个经典 bug 的根。",
    "mechanism": [
      "① Python 按 **LEGB**（Local → Enclosing → Global → Builtin）顺序找变量名。",
      "② 编译内层函数时，发现它引用了外层作用域的变量 → 在外层函数的**闭包单元（cell）**里为那个变量开一个格子。",
      "③ 外层函数里对该变量的**每次读写都变成读写这个 cell**，而不是一个普通局部变量。",
      "④ 外层函数返回后，cell 还被内层函数（闭包）引用着 → 变量**不会被回收**，这就是「记住外层的变量」的机制。",
      "⑤ `nonlocal` 就是显式声明「我要改的是外层那个 cell 里的值」。只写 `x = ...` 而不加 `nonlocal` 会在内层**新建**一个同名局部变量，外层的值不变。",
      "⑥ 循环陷阱的根因：闭包捕获的是**变量**，不是**当时的值**。`for i in range(3): f = lambda: i` 里三个 lambda 共享同一个 cell，循环结束后 cell 里是 2，所以三个都返回 2。",
      "⑦ 解法有两个：① 用 `lambda i=i: ...`（默认值在定义时求值，等于把当前值拷进去）；② 换成生成器/列表推导式的独立作用域。默认参数法是常用手法。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "编译期提升",
        "cell 持有",
        "函数退出存活"
      ],
      "frames": [
        {
          "s": 0,
          "note": "编译内层函数时发现跨作用域引用 → 外层变量升级为 cell"
        },
        {
          "s": 1,
          "note": "外层所有读写都改这个 cell，闭包与它共享同一份"
        },
        {
          "s": 2,
          "note": "外层返回后 cell 仍被闭包引用，变量存活 → 这就是闭包"
        }
      ]
    },
    "interviewQ": [
      "闭包的本质是什么？为什么外层函数返回后变量还活着？",
      "循环里创建闭包为什么全拿到最后一个值？怎么修？"
    ],
    "keywords": [
      "闭包",
      "LEGB",
      "nonlocal",
      "cell",
      "作用域",
      "lambda"
    ],
    "scene": [
      "写回调注册时踩过：循环里注册三个 handler，结果事件触发时三个都执行了最后一次循环的值。",
      "面试高频。答「闭包能访问外层变量」只对一半，要能说出 cell 提升和 nonlocal 的区别。"
    ],
    "related": [
      {
        "id": "python-decorator",
        "kind": "prereq",
        "note": "装饰器是闭包最常见的应用，装饰器里的自由变量正是 cell"
      },
      {
        "id": "python-generator",
        "kind": "compare",
        "note": "生成器用帧对象保存执行状态，闭包用 cell 保存变量，两者都是「延迟保留现场」"
      },
      {
        "id": "py-mutable-default",
        "kind": "compare",
        "note": "默认参数在定义时求值、闭包在运行时捕获，时机不同但都会导致共享"
      }
    ]
  },
  {
    "id": "py-list-mutation",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "可变性与浅拷贝"
    ],
    "tags": [
      "拷贝",
      "深浅",
      "坑"
    ],
    "title": "`copy.deepcopy` 和 `[:]` 差在哪？",
    "oneLine": "切片、`dict.copy()`、`list.copy()` 都只复制**容器本身**（浅拷贝），容器里的可变元素还是同一份对象 —— 改内层会连带改原对象。",
    "analogy": "浅拷贝像复印了一份**目录**：条目名称都对，但每一条指向的还是原来那本书。改一本书的内容，两边都变。",
    "why": "这是「我明明复制了怎么还被改了」这类 bug 的标准答案，在写配置模板、快照、测试数据时高频出现。",
    "mechanism": [
      "① 不可变类型（int/str/tuple/frozenset）不需要拷贝 —— 复制也没意义，因为改不动。**浅拷贝的坑只对可变类型成立。**",
      "② 浅拷贝（`[:]` / `.copy()` / `copy.copy`）新建一个容器，但把里面每个元素**原样引用**过去。",
      "③ 所以 `a = [[1]]; b = a[:]; b[0].append(2)` 之后 `a` 也变成了 `[[1,2]]` —— 复制的只是外层那个 list 对象。",
      "④ 深拷贝（`copy.deepcopy`）递归地把所有嵌套层级都复制一遍，新旧对象彻底断开。代价是时间和内存都上去了。",
      "⑤ 深拷贝**不保证**深到所有类型：打开的文件对象、线程锁、数据库连接这类是「活资源」，deepcopy 会直接抛 `TypeError: cannot pickle '_thread.lock' object`。",
      "⑥ 更轻的做法是只拷贝你要改的那一层（`new = {**old, 'k': v}`），而不是整棵 deepcopy。",
      "⑦ 顺带一个常被搞混的点：`copy.deepcopy` 遇到**循环引用**不会死循环，它用 `memo` 字典记住已复制过的对象，保证同一个对象在结果里仍是同一个。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "新建容器",
        "元素仍引用",
        "改内层连带"
      ],
      "frames": [
        {
          "s": 0,
          "note": "浅拷贝只 new 一个外层容器"
        },
        {
          "s": 1,
          "note": "内层元素逐个原样引用，新旧指向同一对象"
        },
        {
          "s": 2,
          "note": "改任意一层的内层元素，两边一起变"
        }
      ]
    },
    "interviewQ": [
      "为什么 `copy.deepcopy` 一个含锁的对象会报错？",
      "循环引用会不会让 deepcopy 死循环？它靠什么避免？"
    ],
    "keywords": [
      "深拷贝",
      "浅拷贝",
      "deepcopy",
      "copy",
      "可变",
      "引用"
    ],
    "scene": [
      "写过「配置模板复制一份再改」的需求，用了 `[:]` 结果把原配置也改坏了。",
      "写单测时 `expected = actual[:]` 然后断言失败 —— 因为内层是同一份。"
    ],
    "related": [
      {
        "id": "py-dict-keys",
        "kind": "prereq",
        "note": "可变对象不能作 dict key，正是因为拷贝浅、哈希随内容变"
      },
      {
        "id": "py-is-vs-eq",
        "kind": "compare",
        "note": "浅拷贝后两个容器 == 但不是同一个对象，正好区分值比较与身份比较"
      },
      {
        "id": "py-mutable-default",
        "kind": "compare",
        "note": "共享可变对象的两类场景：默认参数是意外共享，浅拷贝是主动共享"
      }
    ]
  },
  {
    "id": "py-set-ops",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "集合与集合运算"
    ],
    "tags": [
      "set",
      "去重",
      "性能"
    ],
    "title": "set 的成员判断为什么是 O(1)？",
    "oneLine": "set 和 dict 同源：用 `hash(key)` 直接定位桶，所以 `x in s` 是常数时间；而 `x in [list]` 要逐个比较，O(n)。",
    "analogy": "翻字典（set）按拼音索页码直接跳；翻一叠散装名单（list）只能一张一张对。",
    "why": "判断「在不在」和「去重」这两种操作在代码里出现频率极高，选错数据结构是真实的性能损失（n=10⁵ 时差 10⁵ 倍）。",
    "mechanism": [
      "① 集合元素必须**可哈希**—— 所以 set 里不能放 list/dict（和 dict key 同一条限制）。",
      "② 存进去时如果已有相等元素，新元素**直接被丢弃** —— 这就是去重，不需要额外比较。",
      "③ `&`（交集）、`|`（并集）、`-`（差集）、`^`（对称差）四个运算符都会**新建**一个集合，不是原地修改。",
      "④ 想要原地更新要用带 `=` 的版本：`s &= other`。这个差异（`&` 新建 vs `&=` 原地）也是常见 bug：写成 `s = s & other` 才是新建，写成 `s & other` 什么也没干。",
      "⑤ 大数据量去重的标准写法是 `set(list)`，O(n)；用 `for x in l: if x in seen: ...` 仍是 O(n²)。",
      "⑥ 反过来的经典坑：需要保持**插入顺序 + 元素唯一**时，不要用 set —— 用 `dict.fromkeys(lst)`，它保留顺序且去重。",
      "⑦ set 不能排序，`sorted(s)` 返回的是新 list；想边去重边排序就直接 `sorted(set(lst))`。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "hash 定位",
        "常数查找",
        "运算新建"
      ],
      "frames": [
        {
          "s": 0,
          "note": "hash(元素) 一次算出，直接定位桶"
        },
        {
          "s": 1,
          "note": "x in set 是 O(1)，而 x in list 是 O(n)"
        },
        {
          "s": 2,
          "note": "& | - ^ 全部返回新集合，原集合不变"
        }
      ]
    },
    "interviewQ": [
      "为什么 set 里不能放可变对象？",
      "`s = s & other` 和 `s &= other` 有什么区别？"
    ],
    "keywords": [
      "set",
      "集合",
      "哈希",
      "去重",
      "并集",
      "交集",
      "O(1)"
    ],
    "scene": [
      "对比 10 万条数据 `in list` 与 `in set` 的耗时，差了几个数量级。",
      "面试被问「怎么保序去重」，答 dict.fromkeys 比 set 好。"
    ],
    "related": [
      {
        "id": "py-dict-keys",
        "kind": "prereq",
        "note": "set 就是没有 value 部分的 dict，定位逻辑完全一致"
      },
      {
        "id": "py-list-mutation",
        "kind": "compare",
        "note": "集合运算都返回新对象，不改原集合；和可变对象的引用共享问题同源"
      },
      {
        "id": "py-comprehension",
        "kind": "extends",
        "note": "推导式是 Python 里最常见的容器构造写法，理解它的作用域很关键"
      }
    ]
  },
  {
    "id": "py-exception-finally",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "异常与 finally"
    ],
    "tags": [
      "异常",
      "finally",
      "坑"
    ],
    "title": "为什么 finally 里写 return 会吃掉异常？",
    "oneLine": "`finally` 块里的 `return` / `break` / `continue` 会**覆盖**正在传播的异常或 break —— 异常被静默吞掉，程序继续往下跑。",
    "analogy": "像消防演习时有人喊「演习结束，都回岗位」，即使真着火也会被当成演习。finally 里的 return 就是这声解散令。",
    "why": "静默吞异常是最难查的一类 bug：程序不报错、日志里什么都没有、行为却是错的。",
    "mechanism": [
      "① `try` 抛异常 → 先按栈往上找匹配的 `except`；没找到就记下来准备抛出。",
      "② **无论有没有异常，finally 都会执行** —— 这是它被用来做清理（关文件、释放锁）的原因。",
      "③ 但如果 finally 块里有 `return`，Python 会**丢弃**那个待抛出的异常，直接从 finally 返回。异常就此消失，无声无息。",
      "④ `break` / `continue` 同理：会中断 `for`/`while` 的正常流程，异常也一并被吃掉。",
      "⑤ 唯一例外是 `os._exit()` / `sys.exit()` 这类**直接终止进程**的调用 —— 它们不是 return，不会被 finally 覆盖。",
      "⑥ 正确做法：finally 里**只做清理，不做流程控制**。要抑制特定异常用 `except SpecificError: pass`（显式，比 finally 里的裸 return 清楚）。",
      "⑦ 相关陷阱：`except Exception:` 会漏掉 `KeyboardInterrupt` 和 `SystemExit`（它们继承 `BaseException` 不是 `Exception`），所以真的想全拦要写 `except BaseException`，但那样连 Ctrl-C 都拦掉了，通常不该这么做。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "异常抛出",
        "finally 执行",
        "return 覆盖"
      ],
      "frames": [
        {
          "s": 0,
          "note": "try 抛异常，暂存待传播"
        },
        {
          "s": 1,
          "note": "finally 无条件执行（清理该放这儿）"
        },
        {
          "s": 2,
          "note": "finally 里的 return 丢弃异常 → 静默吞掉"
        }
      ]
    },
    "interviewQ": [
      "finally 块里写 return 会发生什么？为什么这样设计？",
      "`except Exception` 漏掉了哪两个异常？为什么？"
    ],
    "keywords": [
      "异常",
      "finally",
      "return",
      "BaseException",
      "静默吞异常",
      "finally 返回"
    ],
    "scene": [
      "排查过一个「关连接」的函数，加了 finally 后异常不再上报，错误全被吞掉。",
      "面试高频。多数人只知道 finally 会执行，不知道它还能吞异常。"
    ],
    "related": [
      {
        "id": "python-contextmanager",
        "kind": "prereq",
        "note": "with 就是把 finally 的清理能力做成了语言特性，天然不会吞异常"
      },
      {
        "id": "py-scope-closure",
        "kind": "compare",
        "note": "两处都是「看起来是语法糖，实际是控制流」的例子"
      },
      {
        "id": "py-mutable-default",
        "kind": "compare",
        "note": "都属于「基础语法里藏着一个反直觉控制行为」"
      }
    ]
  },
  {
    "id": "py-comprehension",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python基础",
      "推导式与生成器表达式"
    ],
    "tags": [
      "推导式",
      "生成器",
      "性能"
    ],
    "title": "推导式里的循环变量会泄漏到外层吗？",
    "oneLine": "列表/字典/集合推导式有**自己的作用域**，循环变量不泄漏；而 `for` 循环语句**会**泄漏 —— 所以循环结束后 `i` 还在。",
    "analogy": "推导式像一间有门的房间，进去的人在里面活动、门一关外面看不到；for 循环像在客厅里活动，人和东西都留在客厅。",
    "why": "写嵌套循环时尤其重要：外层和内层用同一个变量名，推导式里不会互相污染，`for` 里会。",
    "mechanism": [
      "① 推导式（`[f(x) for x in it]`）在编译时生成一个**独立函数体**，循环变量是这个函数的局部变量，外部看不见。",
      "② 普通 `for` 语句编译到模块/函数作用域，循环变量留在那里，循环结束后依然可读。",
      "③ 所以列表推导式天然隔离同名变量；嵌套推导式各层互不干扰，不需要起 `i`/`j` 区分。",
      "④ 但反过来 —— 想在循环后继续用 `i` 时**不能**指望推导式，只有 `for` 语句会留下。",
      "⑤ 生成器表达式（`(... for x in it)`）和推导式同源，也是独立作用域且惰性求值；区别是它不立刻算，迭代时才算。",
      "⑥ 性能上，推导式比手写 `for` + `append` 快，因为省掉了 `append` 的方法查找和调用（CPython 3.12+ 的 specializing adaptive interpreter 让差距进一步缩小）。",
      "⑦ 嵌套 `for` 的推导式对应传统写法是 `for a in A: for b in B:` 嵌套，推导式写成 `f(a,b) for a in A for b in B`（或 `for a in A for b in B`，两个 for 平级）。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "独立作用域",
        "循环求值",
        "不泄漏"
      ],
      "frames": [
        {
          "s": 0,
          "note": "推导式编译成独立函数体，循环变量是它的局部变量"
        },
        {
          "s": 1,
          "note": "外层、内层同名也不会互相污染"
        },
        {
          "s": 2,
          "note": "循环变量不出现在外层作用域里"
        }
      ]
    },
    "interviewQ": [
      "推导式的循环变量会泄漏到外面吗？和 `for` 语句有什么不同？",
      "生成器表达式和列表推导式除了惰性还有什么区别？"
    ],
    "keywords": [
      "推导式",
      "列表推导",
      "生成器表达式",
      "作用域",
      "泄漏",
      "惰性求值"
    ],
    "scene": [
      "写嵌套循环时因为内外层都用了 `i` 出过 bug，用推导式后问题消失。",
      "面试被问 Python 的作用域规则时，用它说明「哪些结构有独立作用域」最直观。"
    ],
    "related": [
      {
        "id": "py-scope-closure",
        "kind": "extends",
        "note": "LEGB 里的 E（Enclosing）就是推导式/生成器所在的那层独立作用域"
      },
      {
        "id": "python-generator",
        "kind": "extends",
        "note": "生成器表达式 = 惰性的列表推导式，底层都是生成器"
      },
      {
        "id": "py-set-ops",
        "kind": "compare",
        "note": "集合/字典推导式与列表推导式的唯一差别是外层容器类型，作用域规则一致"
      }
    ]
  }
];

if (typeof module !== "undefined" && module.exports) { module.exports = CARDS_PYTHON_BASIC; }
