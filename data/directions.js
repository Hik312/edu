// 学习方向预设：复习队列页选一个方向 → 今日队列只推这个方向的卡。
// 严格 JSON 字面量：Python(raw_decode) 与 Node(require) 都能读，请勿改回单引号。
//
// ★ 导出的是**对象**不是数组 —— check.js 扫 data/*.js 时只收 Array.isArray 的模块当卡片，
//   导出数组会被当成卡片文件校验、报一堆 MISSING field。别把 DIRECTIONS 直接导出。
// ★ 后端 core/db.py 只认 `var CARDS_*` 正则，本文件的 var DIRECTIONS 不会被当卡片加载。
//
// keywords 是**子串匹配**（大小写不敏感），命中卡片的 keywords / title / topicPath
// 任意一处即算 —— 和岗位对账用的是同一套口径（db._card_hit）。
// 所以优先写 topicPath 段名（「Python基础」「政治」「SpringBoot」）：它对整组卡
// 一命中就是一组，比罗列标题里的原句稳。
// 多个方向命中同一张卡是**允许的**（一张「RAG / Agent 评估」卡本就属于两个方向）。
var DIRECTIONS = [
  { "id": "agent", "name": "Agent 开发",
    "desc": "智能体、工具调用、LangGraph、记忆与多智能体、提示词",
    "keywords": ["Agent", "ReAct", "Tool Calling", "Function Calling", "LangGraph",
                 "多智能体", "记忆", "状态图", "提示词", "评估"] },
  { "id": "rag", "name": "RAG 与向量检索",
    "desc": "检索增强、Embedding、向量数据库、分块与重排",
    "keywords": ["RAG", "Embedding", "向量", "Chunking", "重排", "语义检索"] },
  { "id": "llm", "name": "大模型原理与微调",
    "desc": "Transformer、自注意力、位置编码、LoRA 微调",
    "keywords": ["Transformer", "自注意力", "位置编码", "LoRA", "微调", "大模型"] },
  { "id": "spring", "name": "Spring 原理",
    "desc": "自动装配、IoC、AOP、事务、请求链路",
    "keywords": ["SpringBoot", "自动装配", "Bean", "IoC", "AOP", "事务", "代理",
                 "DispatcherServlet"] },
  { "id": "jvm", "name": "JVM 与并发",
    "desc": "内存模型、垃圾回收、synchronized 锁升级",
    "keywords": ["JVM", "垃圾回收", "堆", "方法区", "synchronized", "锁升级", "分代"] },
  { "id": "python", "name": "Python 基础",
    "desc": "GIL、装饰器、生成器、asyncio、内存管理",
    "keywords": ["Python", "GIL", "asyncio", "装饰器", "生成器", "引用计数", "yield"] },
  { "id": "cs", "name": "计算机基础",
    "desc": "网络协议、进程线程协程",
    "keywords": ["计算机基础", "TCP", "HTTP", "进程", "协程"] },
  { "id": "fe", "name": "前端基础",
    "desc": "浏览器渲染、Event Loop、闭包作用域",
    "keywords": ["前端", "闭包", "Event Loop", "渲染树", "作用域"] },
  { "id": "politics", "name": "考研政治",
    "desc": "马原、毛中特、哲分",
    "keywords": ["政治"] },
  { "id": "english", "name": "考研英语",
    "desc": "长难句、虚拟语气、非谓语",
    "keywords": ["英语"] },
  { "id": "math", "name": "考研数学",
    "desc": "极限、中值定理、定积分",
    "keywords": ["数学"] },
  { "id": "major", "name": "专业课",
    "desc": "复杂度、动态规划、图论",
    "keywords": ["专业课"] }
];
if (typeof module !== "undefined") {
  module.exports = { DIRECTIONS };
}
