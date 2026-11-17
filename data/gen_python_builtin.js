// 严格 JSON 字面量：Node(vm) 与 Python(json) 都能直接读，请勿改回单引号
// Python 常用函数与库用法（2026-10-09）
// ★ 补的缺口：原有 41 张python 卡全是「为什么/原理」向（为什么GIL、为什么闭包、
//   为什么 isinstance），**一张「这个函数怎么用」的卡片都没有**。
//   这一批按「拿到手就能用」组织：内置函数 / 标准库 / 文本与日期 / 文件与数据。
var CARDS_PY_BUILTIN = [
  {
    "id": "python-func-enumerate-zip",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": ["Python进阶", "内置函数", "enumerate 与 zip"],
    "title": "enumerate 和 zip 怎么用？循环里取下标和值哪个更快？",
    "oneLine": "enumerate 同时给下标和值，zip 并行遍历多个序列——都比你手写 range(len()) 更快更清晰。",
    "analogy": "enumerate 像发号牌（号码+人一起给你），zip 像两列名单对齐着发。",
    "why": "写 Python 最常被 review 的点就是手写计数下标，可读性差且容易出错。",
    "mechanism": [
      "① for i, x in enumerate(lst) 同时拿到下标和值，不用手动 i+=1",
      "② start= 参数可指定起始下标：enumerate(lst, start=1) 从 1 开始（贴合人类习惯）",
      "③ for a, b in zip(lst1, lst2) 并行遍历，长度不等时**以最短的为准**",
      "④ zip_longest 可以反向：短的补 None（配 fillvalue 指定填充值）",
      "⑤ 嵌套循环想「双层遍历」用 zip 比双层 range 快且不易越界",
      "⑥ ⚠️ zip 不等长会静默截断——这是隐蔽 bug，看不到报错只是少了数据"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        { "title": "enumerate", "lines": ["for i, x in enumerate(lst)", "i=下标 x=值"], "note": "一次拿两个" },
        { "title": "zip", "lines": ["for a, b in zip(l1, l2)", "不等长按最短截断"], "note": "并行遍历" }
      ],
      "frames": [
        { "s": 0, "note": "enumerate 省掉手写计数" },
        { "s": 1, "note": "zip 不等长静默截断，要留意" }
      ]
    },
    "interviewQ": [
      "zip 两个不等长列表会怎样？",
      "enumerate 的 start 参数有什么用？",
      "为什么推荐 enumerate 而不是 range(len())？"
    ],
    "keywords": ["enumerate", "zip", "内置函数", "循环", "下标"],
    "scene": [
      "打印列表带序号，用 enumerate 一行搞定，比手写 range+len 清晰。",
      "合并两个列表成字典，用 dict(zip(keys, values)) 一步完成。"
    ],
    "tags": ["内置函数", "语法", "实用"],
    "related": [
      { "id": "python-iter-yield", "kind": "extends", "note": "enumerate/zip 产出的是迭代器协议对象" },
      { "id": "python-list-comprehension", "kind": "extends", "note": "常与推导式连用" }
    ]
  },
  {
    "id": "python-func-map-filter",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": ["Python进阶", "内置函数", "map 与 filter"],
    "title": "map 和 filter 怎么用？什么时候用推导式更好？",
    "oneLine": "map 对每个元素做变换，filter 按条件筛选——都返回惰性迭代器，Python 里推导式通常更快。",
    "analogy": "map 像给每个苹果擦一遍（变换），filter 像挑出红苹果（筛选）。",
    "why": "面试常问 map/filter 与推导式的取舍，答案关系到性能与可读性。",
    "mechanism": [
      "① map(func, iterable) 对每个元素应用 func，返回惰性迭代器（不立即算）",
      "② filter(func, iterable) 保留 func 返回 True 的元素",
      "③ 两者都要转成 list 才实际计算：list(map(f, xs))",
      "④ filter(None, xs) 用 None 当假值可快速过滤掉 None/0/空串",
      "⑤ ⚠️ Python 里**推导式比 map/filter 快**（省去函数调用开销），且 map(func) 只能传单参数函数（lambda 绕着写）",
      "⑥ map 真正的优势是能传多个可迭代对象：map(lambda x,y: x+y, xs, ys)"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["取元素", "map变换/filter判断", "惰性返回", "转list触发计算"],
      "frames": [
        { "s": 0, "note": "两者都惰性" },
        { "s": 1, "note": "推导式通常更快更清晰" },
        { "s": 2, "note": "map 可传多个序列" }
      ]
    },
    "interviewQ": [
      "map/filter 和推导式选哪个？",
      "map 怎么传两个列表？",
      "什么是惰性求值？"
    ],
    "keywords": ["map", "filter", "推导式", "惰性求值", "lambda"],
    "scene": [
      "批量处理数据一开始用 map，后来发现推导式快一倍且更好读。",
      "合并两个列表对应元素，map(lambda x,y:...) 比写索引循环简洁。"
    ],
    "tags": ["内置函数", "性能", "实用"],
    "related": [
      { "id": "python-list-comprehension", "kind": "extends", "note": "Python 里优先用推导式" },
      { "id": "python-iter-yield", "kind": "extends", "note": "惰性迭代器的共同基础" }
    ]
  },
  {
    "id": "python-list-comprehension",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": ["Python进阶", "内置函数", "推导式与切片"],
    "title": "列表推导式和生成器表达式怎么区分？切片语法有哪些坑？",
    "oneLine": "推导式用 [ ] 得到列表（立即算），生成器表达式用 ( ) 得迭代器（惰性）；切片 [::step] 步长可为负。",
    "analogy": "推导式像一次性把所有菜做好装盘，生成器表达式像厨师现做现上（要一个给一个）。",
    "why": "切片和推导式是 Python 里出现频率最高的语法，写错隐蔽且不易发现。",
    "mechanism": [
      "① [x*2 for x in xs] 立即算完占内存；(x*2 for x in xs) 惰性不占内存",
      "② 条件过滤：if 在后：[x for x in xs if x>2]；条件表达式用 if/else：[x if x>0 else 0]",
      "③ 切片 xs[a:b] 含a 不含 b（左闭右开）；xs[:] 是浅拷贝",
      "④ 步长 xs[::2] 隔一个取；xs[::-1] 反转（负步长）",
      "⑤ ⚠️ 循环变量不泄漏到外层（Python3）；切片**新建列表**（xs[:] 是副本，不是视图）",
      "⑥ 嵌套推导式靠缩进对齐层级，读起来像俄罗斯套娃"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["for取值", "if过滤", "表达式变换", "[ ]列表/( )迭代器"],
      "frames": [
        { "s": 0, "note": "推导式三段结构：变换+过滤+来源" },
        { "s": 1, "note": "方括号立即算，圆括号惰性" },
        { "s": 2, "note": "切片左闭右开、负步长可反转" }
      ]
    },
    "interviewQ": [
      "推导式和生成器表达式区别？",
      "xs[::-1] 是复制还是视图？",
      "切片是左闭右开还是双闭？"
    ],
    "keywords": ["推导式", "生成器表达式", "切片", "列表推导", "步长"],
    "scene": [
      "读取百万行数据用列表推导式内存爆了，换生成器表达式解决。",
      "反转列表用 xs[::-1] 很方便，但它返回的是副本不是原列表。"
    ],
    "tags": ["内置函数", "语法", "性能"],
    "related": [
      { "id": "python-func-map-filter", "kind": "compare", "note": "推导式 vs map/filter 的取舍" },
      { "id": "python-iter-yield", "kind": "extends", "note": "生成器表达式是惰性的" }
    ]
  },
  {
    "id": "python-func-sorted-key",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": ["Python进阶", "内置函数", "sorted 与排序技巧"],
    "title": "sorted 的 key 怎么用？多级排序怎么做？",
    "oneLine": "sorted(iterable, key=func, reverse=True) 返回新列表不改动原对象；key 可返回元组实现多级排序。",
    "analogy": "像给一叠卡片按「颜色再按点数」排序——key 就是告诉它按哪个字段。",
    "why": "排序是数据处理第一步，key 的巧用能避免写一堆 if-else。",
    "mechanism": [
      "① sorted(xs) 返回**新列表**（不改动 xs），list.sort() 才是原地排序",
      "② key=len按长度排：[3,1,2]→key=len 得 ['1','2','3']",
      "③ reverse=True 降序；配合 key 使用不影响排序稳定性",
      "④ 多级排序：key 返回元组，如 key=lambda x: (x['dept'], -x['score'])",
      "⑤ operator.itemgetter('age') 比 lambda 更简洁可读；itemgetter(1) 取下标",
      "⑥稳定排序：key 相等的元素保持原顺序 → 可先按次要键排再按主要键排实现多级"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["key函数取键值", "按键排序(稳定)", "reverse反转", "返回新列表"],
      "frames": [
        { "s": 0, "note": "key 决定按什么排" },
        { "s": 1, "note": "稳定 = 键相等保原序" },
        { "s": 2, "note": "返回新列表，不改原对象" }
      ]
    },
    "interviewQ": [
      "sorted 和 list.sort 的区别？",
      "多级排序怎么写？",
      "什么是稳定排序？"
    ],
    "keywords": ["sorted", "sort", "key", "排序", "itemgetter", "多级排序"],
    "scene": [
      "按部门分组、组内按分数倒序——key 返回元组一次搞定。",
      "误用 list.sort() 直接改原列表导致后续逻辑出错，其实该用 sorted。"
    ],
    "tags": ["内置函数", "排序", "实用"],
    "related": [
      { "id": "algo-topk-sort", "kind": "extends", "note": "TopK 用堆而非全排序" },
      { "id": "algo-topk-sort", "kind": "compare", "note": "算法模块的TopK视角" }
    ]
  },
  {
    "id": "python-func-itertools",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": ["Python进阶", "内置函数", "itertools 与functools"],
    "title": "itertools 和 functools 提供了哪些现成工具？",
    "oneLine": "itertools 给惰性迭代器（chain/groupby/permutations），functools 给高阶函数包装（reduce/lru_cache/partial）。",
    "analogy": "像一箱现成的厨房工具：itertools 是各类锅，functools 是省力的小机械。",
    "why": "标准库的工具能替代大部分手写循环，写出来更短也不易错。",
    "mechanism": [
      "① itertools.chain(*lists) 串联多个可迭代对象；islice 取切片（惰性）",
      "② groupby( iterable, key) 分组——⚠️ 要求**同一key 的元素必须相邻**，先排序才能正确分组",
      "③ combinations/permutations/product 组合枚举，不用手写嵌套循环",
      "④ functools.reduce(fn, xs) 累积；lru_cache 缓存函数结果（记忆化）",
      "⑤ functools.partial(fn, a) 偏函数，固定部分参数便于复用",
      "⑥ 全部是惰性的（用完即弃），省内存但只能遍历一次"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        { "title": "itertools", "lines": ["chain/islice/slice", "groupby/combinations", "惰性迭代器"], "note": "迭代工具" },
        { "title": "functools", "lines": ["reduce/lru_cache", "partial/singledispatch", "高阶函数"], "note": "函数工具" }
      ],
      "frames": [
        { "s": 0, "note": "itertools 管迭代，functools 管函数" },
        { "s": 1, "note": "groupby 要求相邻，惰性省内存" }
      ]
    },
    "interviewQ": [
      "groupby 为什么要求元素相邻？",
      "lru_cache 的作用？",
      "itertools 的惰性有什么好处？"
    ],
    "keywords": ["itertools", "functools", "reduce", "lru_cache", "groupby", "partial"],
    "scene": [
      "写两两组合的搜索逻辑，itertools.combinations 一行替代三重循环。",
      "递归斐波那契太慢，@lru_cache 加上后瞬间变快。"
    ],
    "tags": ["标准库", "内置函数", "实用"],
    "related": [
      { "id": "python-iter-yield", "kind": "extends", "note": "itertools 全基于迭代器协议" }
    ]
  },
  {
    "id": "python-func-string",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": ["Python进阶", "内置函数", "字符串处理"],
    "title": "Python 字符串常用方法有哪些？f-string 怎么用？",
    "oneLine": "split/join/strip/replace/startswith 是最常用的一批；f-string 是格式化首选，比 % 和 format 都清晰。",
    "analogy": "像处理一段文字的工具箱：切分、拼接、修边、查找替换。",
    "why": "字符串处理在日常脚本里占比极高，方法记熟能省大量时间。",
    "mechanism": [
      "① split(sep)/join(列表) —— 切分和拼接互逆；join 比循环 += 快（避免反复拷贝）",
      "② strip() 去首尾空白；lstrip/rstrip 只去一侧",
      "③ startswith/endswith 判前后缀；in 判断子串",
      "④ replace(a,b) 全局替换；replace 次数用 count 参数",
      "⑤ f-string：f\"{name!r:>10}\" 一步搞定替换+格式+对齐+转义",
      "⑥ ⚠️ 字符串不可变，所有「修改」都产生新对象；循环里+= 是O(n²)，用 join"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["切分split", "清洗strip", "查找/替换", "拼接join/f-string"],
      "frames": [
        { "s": 0, "note": "split/join 是互逆的一对" },
        { "s": 1, "note": "字符串不可变，+= 在循环里是 O(n²)" }
      ]
    },
    "interviewQ": [
      "join 比 += 快的原因？",
      "f-string 相比 % 和 format 的优势？",
      "字符串为什么不可变？"
    ],
    "keywords": ["字符串", "f-string", "split", "join", "replace", "strip"],
    "scene": [
      "拼大字符串用循环 += 卡住，改成 ''.join(列表) 立刻快很多。",
      "日志里插值用 f-string，格式化对齐和转义不用再记 % 的写法。"
    ],
    "tags": ["内置函数", "字符串", "实用"],
    "related": [
      { "id": "python-copy-deepcopy", "kind": "extends", "note": "字符串不可变源于 Python 的可变性问题" }
    ]
  },
  {
    "id": "python-func-datetime",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": ["Python进阶", "标准库", "日期时间处理"],
    "title": "日期时间怎么处理？时区为什么会踩坑？",
    "oneLine": "用 datetime/date 处理时间，用 timezone 处理时区；⚠️ 永远存 UTC，展示时再转本地。",
    "analogy": "像寄国际快递：全程用统一时区记账，收件人当地才转译显示。",
    "why": "时区处理是后端最常见的 bug 来源之一，日志和定时任务都靠它。",
    "mechanism": [
      "① datetime.now() 返回**带本地时区**的 datetime；utcnow() 返回 naive 的 UTC 时间（易混）",
      "② 推荐用 timezone.utc / zoneinfo 处理时区，别手动加减小时",
      "③ strftime 格式化、strptime 解析字符串成 datetime",
      "④ timedelta 表示时间差：dt + timedelta(days=1) 做加减",
      "⑤ ⚠️ 坑：naive datetime（无时区信息）比较/存储会出错，跨时区部署必炸",
      "⑥ 计算时间差用时间戳相减（timedelta.total_seconds()），不用手算",
      "⑦ zoneinfo（3.9+）读系统时区库，需 tzdata；pytz 是老方案"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["存UTC时间", "展示转本地", "strftime格式化", "timedelta做差"],
      "frames": [
        { "s": 0, "note": "永远存 UTC，避免时区混乱" },
        { "s": 1, "note": "展示时才转本地时区" },
        { "s": 2, "note": "naive datetime 跨时区必出问题" }
      ]
    },
    "interviewQ": [
      "为什么时间要统一存UTC？",
      "now() 和 utcnow() 有什么区别？",
      "怎么计算两个时间的间隔？"
    ],
    "keywords": ["datetime", "timezone", "时区", "UTC", "strftime", "timedelta"],
    "scene": [
      "服务器换时区后日志时间全错位，因为存的是本地时间没转 UTC。",
      "跨时区用户看活动时间差8 小时，后端统一存 UTC 后由前端转换解决。"
    ],
    "tags": ["标准库", "日期", "实用"],
    "related": [
      { "id": "python-logging", "kind": "extends", "note": "日志的时间戳涉及时区" }
    ]
  },
  {
    "id": "python-func-json-csv",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": ["Python进阶", "标准库", "JSON 与 CSV"],
    "title": "读写 JSON 和 CSV 怎么做？中文乱码怎么避免？",
    "oneLine": "json.load/dump 处理结构化数据，csv 模块处理表格；读写文件一律指定 encoding='utf-8'。",
    "analogy": "JSON 像交换数据的通用信封，CSV 像打印好的表格，各自工具不同。",
    "why": "数据交换和导入导出是脚本最常见的任务，编码不指定就会中文乱码。",
    "mechanism": [
      "① json.loads(str) 解析字符串、json.load(file) 读文件；json.dumps(obj) 序列化",
      "② ⚠️ ensure_ascii=False 才能输出中文（默认转义成\\uXXXX）；配合 indent=2 可读",
      "③ json.load 返回 dict；拿键用 .get 更安全",
      "④ csv.DictReader/DictWriter 用字典处理每行，比 csv.reader 方便",
      "⑤ ⚠️ 读写文本文件必须 encoding='utf-8'——不指定会用系统默认（Windows 是 GBK）导致乱码",
      "⑥ 大文件用 json.JSONDecoder 的 raw_decode 流式解析，或逐行处理避免占满内存"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["读/写", "指定encoding", "解析/序列化", "处理结构"],
      "frames": [
        { "s": 0, "note": "encoding='utf-8' 是中文不乱码的关键" },
        { "s": 1, "note": "ensure_ascii=False 才能输出中文" },
        { "s": 2, "note": "CSV 用 DictReader 更方便" }
      ]
    },
    "interviewQ": [
      "json.dumps 默认会把中文转义吗？",
      "文件读写为什么要指定 encoding？",
      "CSV 和 JSON 怎么选？"
    ],
    "keywords": ["json", "csv", "编码", "encoding", "序列化", "utf-8"],
    "scene": [
      "导出带中文的 JSON 打开全是 \\uXXXX——忘记 ensure_ascii=False。",
      "读 CSV 文件中文乱码，Windows 下没指定编码默认按 GBK 解析。"
    ],
    "tags": ["标准库", "文件", "序列化"],
    "related": [
      { "id": "python-serialization", "kind": "compare", "note": "pickle vs JSON 的安全取舍" },
      { "id": "python-logging", "kind": "compare", "note": "文件编码的通用问题" }
    ]
  },
  {
    "id": "python-func-file-path",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": ["Python进阶", "标准库", "文件与路径"],
    "title": "pathlib 和 os.path 怎么选？文件操作要注意什么？",
    "oneLine": "pathlib 用面向对象的路径（/ 拼接、glob 遍历），现代 Python 推荐；os.path 是老式字符串路径。",
    "analogy": "pathlib 像给路径配了个工具箱（打开/遍历/建目录都是方法），os.path 像拿字符串拼。",
    "why": "文件批处理是自动化脚本的基础，路径写对能少一半坑。",
    "mechanism": [
      "① Path('a')/'b.txt' 用 / 拼路径更直观（跨平台统一用/，Windows 也支持）",
      "② p.read_text()/write_text() 直接读写，不用open+close",
      "③ p.glob('*.txt') / rglob('**/*.log') 递归遍历匹配文件",
      "④ mkdir(parents=True, exist_ok=True) 一次建多级目录（幂等不怕已存在）",
      "⑤ shutil.move/copy/rmtree 批量操作；shutil.copytree 拷整个目录",
      "⑥ ⚠️ 路径穿越风险：用户输入的路径要校验，不能直接拼进 open（../ 可读到项目外）",
      "⑦ os.walk 是老方式遍历目录，现在更推荐 rglob"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["Path拼路径", "glob遍历", "读写/建目录", "批量操作"],
      "frames": [
        { "s": 0, "note": "pathlib 是面向对象的现代写法" },
        { "s": 1, "note": "mkdir(exist_ok) 幂等建目录" },
        { "s": 2, "note": "用户路径要防穿越" }
      ]
    },
    "interviewQ": [
      "pathlib 相比 os.path 的优势？",
      "什么是路径穿越漏洞？",
      "怎么批量处理一个目录的所有文件？"
    ],
    "keywords": ["pathlib", "os", "文件", "路径", "glob", "shutil"],
    "scene": [
      "批量把文件夹里的 .md 转格式，用 Path.rglob 一行搞定遍历。",
      "服务里用用户传来的文件名读文件，结果读到了/etc/passwd——路径穿越。"
    ],
    "tags": ["标准库", "文件", "路径"],
    "related": [
      { "id": "python-context-manager", "kind": "extends", "note": "文件最好用 with 管理" },
      { "id": "fe-network-cache", "kind": "compare", "note": "HTTP 缓存策略与文件缓存同理" }
    ]
  },
  {
    "id": "python-func-type-hints",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": ["Python进阶", "内置函数", "类型注解与检查"],
    "title": "isinstance 和 type 有什么区别？type(x) == int 为什么不推荐？",
    "oneLine": "isinstance 支持继承（子类也算），type 是精确类型判断；判断类型优先用 isinstance。",
    "analogy": "isinstance 像问「你属于汽车吗」（轿车算），type 像问「你精确是哪个型号」。",
    "why": "这个选择影响代码是否能在子类上正常工作，是 Python 面试的经典细节题。",
    "mechanism": [
      "① isinstance(obj, int) 对 bool 也成立（bool 是 int 的子类）",
      "② type(obj) == int 是精确匹配，bool 不匹配",
      "③ isinstance 支持元组：isinstance(x, (int, str)) 判断多个类型之一",
      "④ ⚠️ type(x) == int 在有子类时失效——判断类型应该用 isinstance",
      "⑤ 检查是否可调用用 callable(x)，不是isinstance(x, type)",
      "⑥ 类型注解 + 类型别名：def f(x: int | None) 表达可选"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        { "title": "isinstance", "lines": ["子类也匹配", "支持类型元组"], "note": "按继承判断" },
        { "title": "type(x)==", "lines": ["精确匹配", "子类不匹配"], "note": "按类型判断" }
      ],
      "frames": [
        { "s": 0, "note": "isinstance 看继承链，type 看精确类型" }
      ]
    },
    "interviewQ": [
      "isinstance 和 type 的区别？",
      "为什么 isinstance(True, int) 是 True？",
      "怎么一次性判断多个类型？"
    ],
    "keywords": ["isinstance", "type", "类型判断", "继承", "callable"],
    "scene": [
      "写工具函数判断参数类型，用 isinstance 兼容了子类，用 type 导致子类传进来就报错。",
      "面试被问 isinstance(True, int) 的结果——True（bool 继承 int）。"
    ],
    "tags": ["内置函数", "类型", "实用"],
    "related": [
      { "id": "python-typing-generics", "kind": "extends", "note": "类型注解与运行时类型判断" },
      { "id": "python-oop-dunder", "kind": "extends", "note": "继承体系决定 isinstance 行为" }
    ]
  }
];
if (typeof module !== "undefined" && module.exports) {
  module.exports = CARDS_PY_BUILTIN;
}