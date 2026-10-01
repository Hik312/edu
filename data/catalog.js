// 分类树：两大领域（考研 / 工作）× 各自科目。卡片用 category + subject 两个 id 归类。
// 严格 JSON 字面量：Node(require) 与 Python(raw_decode) 都能直接读，请勿改回单引号。
// 增删科目改这里即可，导航、筛选、统计会自动跟着变。
var CATALOG = [
  {
    "id": "kaoyan",
    "name": "考研",
    "desc": "公共课与专业课的考点背诵",
    "subjects": [
      { "id": "politics", "name": "政治" },
      { "id": "english", "name": "英语" },
      { "id": "math", "name": "数学" },
      { "id": "major", "name": "专业课" }
    ]
  },
  {
    "id": "work",
    "name": "工作",
    "desc": "面试考点与技术原理拆解",
    "subjects": [
      { "id": "java", "name": "Java后端" },
      { "id": "python", "name": "Python基础" },
      { "id": "ai", "name": "AI工程" },
      { "id": "cs", "name": "计算机基础" },
      { "id": "fe", "name": "前端" }
    ]
  }
];
if (typeof module !== "undefined" && module.exports) {
  module.exports = CATALOG;
}
