// 【一次性脚本 · 已执行完毕，留档】把 data/*.js 里的 JS 字面量改成严格 JSON 字面量
//
// 注意：本文件 2026-09-26 从 scripts/ 挪进了 scripts/_oneoff/，
// __dirname 多了一层，下面的路径已同步改成三个 '..'。
// 原因：原文件用单引号，Python 的 json.loads 读不了；改成双引号后 Node(vm) 和 Python(json) 都能直接读。
// 保留 `var CARDS_X = [...]` 外壳，网页 <script src> 直接加载的方式不变。
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const dir = path.join(__dirname, '..', '..', '..', 'data');
let n = 0;
fs.readdirSync(dir).filter(function (f) { return f.endsWith('.js'); }).forEach(function (f) {
  const p = path.join(dir, f);
  const src = fs.readFileSync(p, 'utf8');
  const m = src.match(/var\s+(CARDS_[A-Za-z0-9_]+)/);
  if (!m) { console.log('跳过（未找到卡片变量）: ' + f); return; }
  const sandbox = {};
  vm.runInNewContext(src, sandbox);
  const arr = sandbox[m[1]];
  if (!Array.isArray(arr)) { console.log('跳过（不是数组）: ' + f); return; }
  // 末尾的 module.exports 必须保留：back_study/scripts/check.js 用 require() 读卡做字段校验。
  // 浏览器里 module 未定义，typeof 判断会跳过，不影响 <script src> 直接加载。
  const out = '// 严格 JSON 字面量：Node(vm) 与 Python(json) 都能直接读，请勿改回单引号\n'
    + 'var ' + m[1] + ' = ' + JSON.stringify(arr, null, 2) + ';\n'
    + 'if (typeof module !== "undefined" && module.exports) {\n  module.exports = ' + m[1] + ';\n}\n';
  fs.writeFileSync(p, out, 'utf8');
  console.log(f + ' -> ' + arr.length + ' 张，已规范化');
  n += arr.length;
});
console.log('共 ' + n + ' 张卡。规范化后请用 back_study/scripts/check.js 复验。');
