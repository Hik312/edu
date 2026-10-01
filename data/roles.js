// 目标岗位定义：选一个岗位 → 推出它要的知识点（科目 + 技能词），跟卡片库对账。
// 严格 JSON 字面量：Python(raw_decode) 与 Node(require) 都能读。
//
// ★ 导出的是**对象**不是数组 —— check.js 扫 data/*.js 时只收 Array.isArray 的模块当卡片，
//   导出数组会被当成卡片文件校验、报一堆 MISSING field。改这个文件别把 ROLES 直接导出。
// ★ 后端 core/db.py 只认 `var CARDS_*` 正则，本文件的 var ROLES 不会被当卡片加载。
//
// 每个岗位的 skills：
//   subject   科目 id（必须在 catalog.js 里登记）
//   weight    该科目在这个岗位里的分量 1~3，前端按它排组顺序
//   keywords  这个岗位最看重的技能词 —— 用来对账「库里有没有这块的卡」
var ROLES = [
  {
    "id": "agent-dev",
    "name": "Java+Python Agent 开发",
    "desc": "大模型应用方向：Java 后端底子 + AI 工程 + Python 脚手架，计算机基础兜底。",
    "skills": [
      { "subject": "ai", "weight": 3,
        "keywords": ["RAG", "向量", "Agent", "提示词", "LangGraph", "Function Calling", "embedding"] },
      { "subject": "java", "weight": 3,
        "keywords": ["JVM", "并发", "线程池", "Spring", "MySQL", "索引", "事务"] },
      { "subject": "python", "weight": 2,
        "keywords": ["GIL", "异步", "asyncio", "装饰器", "生成器", "垃圾回收"] },
      { "subject": "cs", "weight": 1,
        "keywords": ["网络", "TCP", "缓存", "进程", "线程", "操作系统"] }
    ]
  },
  {
    "id": "java-backend",
    "name": "Java 后端开发",
    "desc": "传统后端主力岗：JVM、并发、框架原理 + 数据库与计算机基础。",
    "skills": [
      { "subject": "java", "weight": 3,
        "keywords": ["JVM", "垃圾回收", "并发", "synchronized", "线程池", "Spring", "IoC", "AOP", "类加载"] },
      { "subject": "cs", "weight": 2,
        "keywords": ["MySQL", "索引", "B+树", "事务", "缓存", "TCP", "一致性哈希"] },
      { "subject": "fe", "weight": 1,
        "keywords": ["跨域", "浏览器渲染", "Web 缓存"] }
    ]
  },
  {
    "id": "python-backend",
    "name": "Python 开发",
    "desc": "以 Python 为主的后端与脚手架岗，异步与并发是必考。",
    "skills": [
      { "subject": "python", "weight": 3,
        "keywords": ["GIL", "asyncio", "协程", "装饰器", "生成器", "垃圾回收", "上下文管理器", "MRO"] },
      { "subject": "cs", "weight": 2,
        "keywords": ["网络", "TCP", "缓存", "数据库", "进程"] },
      { "subject": "ai", "weight": 1,
        "keywords": ["RAG", "向量", "LangChain"] }
    ]
  },
  {
    "id": "ai-engineer",
    "name": "AI 工程 / 大模型应用",
    "desc": "模型应用层：RAG、Agent 编排、微调与部署，Python 是地基。",
    "skills": [
      { "subject": "ai", "weight": 3,
        "keywords": ["Transformer", "RAG", "向量", "Agent", "LangGraph", "微调", "LoRA", "量化"] },
      { "subject": "python", "weight": 2,
        "keywords": ["异步", "asyncio", "装饰器", "生成器"] },
      { "subject": "cs", "weight": 2,
        "keywords": ["缓存", "网络", "并发", "GPU"] }
    ]
  },
  {
    "id": "fullstack",
    "name": "全栈工程师",
    "desc": "前端 + 后端都要能扛，重在打通链路而非单点深挖。",
    "skills": [
      { "subject": "fe", "weight": 3,
        "keywords": ["浏览器渲染", "Event Loop", "Vue", "响应式", "Virtual DOM", "跨域", "Web 缓存"] },
      { "subject": "java", "weight": 2,
        "keywords": ["Spring", "MySQL", "索引", "事务", "并发"] },
      { "subject": "cs", "weight": 1,
        "keywords": ["HTTP", "TCP", "缓存"] }
    ]
  },
  {
    "id": "cs-base",
    "name": "计算机基础 / 算法岗",
    "desc": "笔试面试重基础：数据结构、操作系统、网络、数据库。",
    "skills": [
      { "subject": "cs", "weight": 3,
        "keywords": ["B+树", "排序", "动态规划", "死锁", "虚拟内存", "TCP", "CAP", "一致性哈希"] },
      { "subject": "python", "weight": 1,
        "keywords": ["复杂度", "数据结构"] },
      { "subject": "java", "weight": 1,
        "keywords": ["JVM", "并发"] }
    ]
  }
];

if (typeof module !== "undefined" && module.exports) { module.exports = { ROLES: ROLES }; }
