// 分类树：两大领域（考研 / 工作）× 各自科目。卡片用 category + subject 两个 id 归类。
// 严格 JSON 字面量：Node(require) 与 Python(raw_decode) 都能直接读，请勿改回单引号。
// 增删科目改这里即可，导航、筛选、统计会自动跟着变。
// emoji 给小程序首页的分类卡/科目 chip 当图标，后端原样透传，网页端不显示也无害。
var CATALOG = [
  {
    "id": "kaoyan",
    "name": "考研",
    "emoji": "🎓",
    "desc": "公共课与专业课的考点背诵",
    "subjects": [
      { "id": "politics", "name": "政治", "emoji": "📜" },
      { "id": "english", "name": "英语", "emoji": "🔤" },
      { "id": "math", "name": "数学", "emoji": "📐" },
      { "id": "major", "name": "专业课", "emoji": "🧩" }
    ]
  },
  {
    "id": "work",
    "name": "工作",
    "emoji": "💼",
    "desc": "面试考点与技术原理拆解",
    "subjects": [
      { "id": "java", "name": "Java后端", "emoji": "☕" },
      { "id": "python", "name": "Python基础", "emoji": "🐍" },
      { "id": "ai", "name": "AI工程", "emoji": "🤖" },
      { "id": "cs", "name": "计算机基础", "emoji": "🌐" },
      { "id": "fe", "name": "前端", "emoji": "🎨" },
      { "id": "algorithm", "name": "算法", "emoji": "🧮" },
      { "id": "middleware", "name": "中间件", "emoji": "🧱" }
    ]
  }
];
if (typeof module !== "undefined" && module.exports) {
  module.exports = CATALOG;
}
