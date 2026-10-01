// 【一次性脚本 · 已执行完毕，留档】给卡片写入带语义的关联关系 related
// 用对象数组而不是裸 id 数组：每条关联必须说清「为什么连」，否则就变成关键词乱连的毛线球
//
// 注意：本文件 2026-09-26 从 scripts/ 挪进了 scripts/_oneoff/，
// 所以 __dirname 多了一层，下面的路径已同步改成三个 '..'。别照抄旧笔记里的两层写法。
const fs = require('fs');
const path = require('path');

const FILE = path.join(__dirname, '..', '..', '..', 'data', 'springboot.js');
const cards = require(FILE);

// kind: prereq=先懂这个 / extends=延伸出去 / compare=对比辨析
const REL = {
  'sb-autoconfig': [
    { id: 'sb-condition', kind: 'prereq', note: '自动装配逐个过闸靠的就是条件注解，不看这个只记住流程' },
    { id: 'sb-bean-lifecycle', kind: 'extends', note: '装配通过后注册成 BeanDefinition，接着走完整生命周期' },
    { id: 'sb-startup', kind: 'compare', note: '自动装配发生在 refresh 里，是启动流程的一个阶段而非并列关系' }
  ],
  'sb-startup': [
    { id: 'sb-embedded-tomcat', kind: 'extends', note: 'onRefresh 阶段拉起内嵌容器，是启动流程的第 8 步' },
    { id: 'sb-autoconfig', kind: 'extends', note: 'refresh 里由 ConfigurationClassPostProcessor 触发自动装配' }
  ],
  'sb-bean-lifecycle': [
    { id: 'sb-circular', kind: 'extends', note: '循环依赖是生命周期中「属性填充」这一卡住时的解法' },
    { id: 'sb-aop-proxy', kind: 'extends', note: '代理生成发生在初始化之后，这一步决定了你拿到的是不是原对象' }
  ],
  'sb-circular': [
    { id: 'sb-bean-lifecycle', kind: 'prereq', note: '先有生命周期的分步，才知道三级缓存卡在哪一步' },
    { id: 'sb-aop-proxy', kind: 'compare', note: '早期引用暴露的是代理对象，AOP 会让循环依赖更容易踩坑' }
  ],
  'sb-aop-proxy': [
    { id: 'sb-transactional', kind: 'extends', note: '事务就是靠代理实现的，自调用失效的根因在这里' },
    { id: 'sb-circular', kind: 'compare', note: '两者都涉及「你拿到的对象是不是原对象」这个问题' }
  ],
  'sb-mvc-flow': [
    { id: 'sb-filter-levels', kind: 'extends', note: '请求链路里具体在哪几层被拦，拆开单独看' },
    { id: 'sb-embedded-tomcat', kind: 'prereq', note: 'DispatcherServlet 要先注册进容器，链路才跑得起来' }
  ],
  'sb-transactional': [
    { id: 'sb-aop-proxy', kind: 'prereq', note: '不先懂代理，六种失效只能靠背，换种写法就认不出' },
    { id: 'sb-bean-lifecycle', kind: 'compare', note: '两者都讲究「哪个时机做哪件事」' }
  ],
  'sb-condition': [
    { id: 'sb-autoconfig', kind: 'extends', note: '条件注解是自动装配的执行单元，最终服务于装配决策' }
  ],
  'sb-filter-levels': [
    { id: 'sb-mvc-flow', kind: 'prereq', note: '先有完整链路，才知道这三层各自插在哪' },
    { id: 'sb-aop-proxy', kind: 'compare', note: 'AOP 是三层里最靠内的那一层，粒度最细' }
  ],
  'sb-embedded-tomcat': [
    { id: 'sb-startup', kind: 'prereq', note: '容器的启动是启动流程的一步，脱离流程看没有意义' },
    { id: 'sb-mvc-flow', kind: 'extends', note: '容器起来后才有请求链路可走' }
  ]
};

let n = 0;
for (const c of cards) {
  if (REL[c.id]) { c.related = REL[c.id]; n++; }
}

// 严格 JSON 字面量输出，保持 JS/Python 双可读
const out = '// 严格 JSON 字面量：Node(vm) 与 Python(json) 都能直接读，请勿改回单引号\n'
  + 'var CARDS_SPRINGBOOT = ' + JSON.stringify(cards, null, 2) + ';\n\n'
  + 'if (typeof module !== "undefined") { module.exports = CARDS_SPRINGBOOT; }\n';
fs.writeFileSync(FILE, out, 'utf8');
console.log('已写入 related 的卡片数: ' + n + ' / ' + cards.length);
console.log('关联总条数: ' + cards.reduce((s, c) => s + ((c.related || []).length), 0));
