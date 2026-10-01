// 【一次性脚本 · 已执行完毕，留档】给现有卡片加 category + subject，替换笼统的 domain
//
// 注意：本文件 2026-09-26 从 scripts/ 挪进了 scripts/_oneoff/，
// __dirname 多了一层，下面的路径已同步改成三个 '..'。
// 旧值 "求职·Java" -> category="work"(工作) subject="java"(Java后端)
// domain 字段保留不删，避免旧代码/旧缓存炸掉，但新代码一律用 category + subject。
const fs = require('fs');
const path = require('path');

const MAP = {
  '求职·Java': { category: 'work', subject: 'java' },
  '求职·AI': { category: 'work', subject: 'ai' },
  '考研·政治': { category: 'kaoyan', subject: 'politics' },
  '考研·英语': { category: 'kaoyan', subject: 'english' },
  '考研·数学': { category: 'kaoyan', subject: 'math' },
  '考研·专业课': { category: 'kaoyan', subject: 'major' }
};

const dir = path.join(__dirname, '..', '..', '..', 'data');
let total = 0;
fs.readdirSync(dir).filter(function (f) { return f.endsWith('.js'); }).forEach(function (f) {
  if (f === 'catalog.js') return;
  const p = path.join(dir, f);
  const src = fs.readFileSync(p, 'utf8');
  const m = src.match(/var\s+(CARDS_[A-Za-z0-9_]+)/);
  if (!m) return;
  const sandbox = {};
  require('vm').runInNewContext(src, sandbox);
  const arr = sandbox[m[1]];
  if (!Array.isArray(arr)) return;

  let changed = 0;
  arr.forEach(function (c) {
    if (c.category && c.subject) return;              // 已迁移过就跳过
    const hit = MAP[c.domain] || { category: 'work', subject: 'java' };
    // 插到 domain 后面，保持字段顺序可读
    const out = {};
    Object.keys(c).forEach(function (k) {
      out[k] = c[k];
      if (k === 'domain') { out.category = hit.category; out.subject = hit.subject; }
    });
    Object.keys(out).forEach(function (k) { c[k] = out[k]; });
    changed++;
  });

  const body = JSON.stringify(arr, null, 2);
  const out = '// 严格 JSON 字面量：Node(vm) 与 Python(json) 都能直接读，请勿改回单引号\n'
    + 'var ' + m[1] + ' = ' + body + ';\n'
    + 'if (typeof module !== "undefined" && module.exports) {\n  module.exports = ' + m[1] + ';\n}\n';
  fs.writeFileSync(p, out, 'utf8');
  console.log(f + ' -> 迁移 ' + changed + ' 张（共 ' + arr.length + '）');
  total += changed;
});
console.log('共迁移 ' + total + ' 张卡。之后跑 back_study/scripts/check.js 复验。');
