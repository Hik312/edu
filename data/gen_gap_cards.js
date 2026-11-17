// 补缺卡：岗位对账实测出的真缺口。
//   1. fe-cors       —— 全库 0 张「跨域/CORS」，但它在 java-backend / fullstack 岗位里是必需技能词
//   2. python-mro    —— 全库 0 张「MRO」，python-backend 岗位列了它
// 这两张不是「凑数」，是对账逻辑实测报出来的缺口（没有它们，岗位覆盖率永远上不满）。
var CARDS_GAP_2026_10 = [
  {
    "id": "fe-cors",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "浏览器机制",
      "同源与跨域"
    ],
    "title": "跨域是怎么被浏览器拦住的？CORS 为什么「简单请求」不用预检？",
    "oneLine": "浏览器同源策略拦的是「读取结果」而不是「发出请求」，所以服务端必须用响应头显式授权，而预检只是复杂请求多走的一次确认。",
    "analogy": "同源像自家人进自家院子（门都开着）；跨域像客人来串门（能敲院门，但进院子要主人家同意，否则院子里的东西他看不见也拿不走）。",
    "why": "很多开发第一次遇到跨域会误以为是「请求没发出去」，实际请求已经到服务端并执行了，只是浏览器不让JS 读到响应。这就是为什么排查时要先看服务端日志——日志里有记录说明请求到了，是浏览器拦的响应。",
    "mechanism": [
      "① 同源策略限制的是**读取**：JS 可以发跨域请求（img/script 标签甚至不需要 CORS），但拿不到响应体",
      "② 简单请求（GET/HEAD/POST +仅 Content-Type 为 text/plain/form-urlencoded/multipart + Accept 等简单头）直接发，响应若要JS 读取，服务端必须回Access-Control-Allow-Origin",
      "③ 复杂请求（带 Authorization、Content-Type: application/json、PUT/DELETE 等）会先发一个 OPTIONS 预检，问「我能不能发这个请求、带你什么头」",
      "④ 预检通过条件：Allow-Origin 命中 + Allow-Methods 含方法 + Allow-Headers 含请求头，三者任一不过就停在预检",
      "⑤ 带凭证的请求（fetch credentials: include / axios withCredentials）不能用通配符 *，必须回具体来源且加 Access-Control-Allow-Credentials: true",
      "⑥ 响应头只在服务端生效，前端代理/nginx 补头也算；最省事的做法是同源部署 + 反向代理，彻底不产生跨域"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "JS 发跨域请求",
        "浏览器查是否简单",
        "复杂：先发 OPTIONS 预检",
        "服务端回 CORS 头",
        "浏览器校验通过才给JS"
      ],
      "frames": [
        {
          "s": 0,
          "note": "请求已发出，服务端其实已执行"
        },
        {
          "s": 1,
          "note": "简单请求：直接等响应"
        },
        {
          "s": 2,
          "note": "复杂请求：先预检问权限"
        },
        {
          "s": 3,
          "note": "Allow-Origin/Methods/Headers 三项都要对"
        },
        {
          "s": 4,
          "note": "通过才把响应体交给 JS，否则拦截"
        }
      ]
    },
    "interviewQ": [
      "跨域请求到底有没有发出去？",
      "什么请求会触发预检？带自定义头算简单请求吗？",
      "为什么带 credentials 时 Access-Control-Allow-Origin 不能写 *？",
      "预检响应被浏览器缓存了怎么办？"
    ],
    "keywords": [
      "跨域",
      "CORS",
      "同源策略",
      "预检",
      "OPTIONS",
      "Access-Control-Allow-Origin",
      "简单请求",
      "同源部署",
      "反向代理"
    ],
    "scene": [
      "前端 5173 端口调后端 8000，浏览器控制台报 CORS，但 Network 里请求是 200 —— 典型 misunderstand：请求到了，是浏览器不让 JS 读。",
      "带 token 的 fetch 报错，调试发现服务端写的 Access-Control-Allow-Origin: *，而请求带了 credentials，浏览器直接拒绝这种组合。"
    ],
    "tags": [
      "HTTP",
      "安全",
      "浏览器机制"
    ],
    "related": [
      {
        "id": "fe-storage-cookie",
        "kind": "extends",
        "note": "JWT 放哪决定了这个请求要不要带 credentials"
      },
      {
        "id": "fe-network-cache",
        "kind": "compare",
        "note": "两者都是浏览器强加的策略，一个管读取一个管缓存"
      },
      {
        "id": "cs-http-versions",
        "kind": "compare",
        "note": "同属HTTP 层机制，一个在浏览器策略一个在协议版本演进"
      },
      {
        "id": "fe-browser-rendering",
        "kind": "compare",
        "note": "相关：fe-browser-rendering"
      }
    ]
  },
  {
    "id": "python-mro",
    "domain": "Python基础",
    "category": "work",
    "subject": "python",
    "topicPath": [
      "Python进阶",
      "面向对象",
      "继承与 MRO"
    ],
    "title": "MRO 是什么？C3 线性化为什么用菱形继承就会算不出唯一顺序？",
    "oneLine": "MRO 是「方法查找顺序」，C3 线性化用「子类优先 + 局部保留单调」两条规则合并各父类的线性序列，多继承时如果违反单调性就只能报错。",
    "analogy": "MRO 是一张「找谁帮忙」的名单。遇到方法调用就按名单从左到右找，找到就用。问题是继承有分叉时，这张名单必须既公平又稳定，否则同一个类在不同文件里顺序不一样。",
    "why": "MRO 不是「Python 规定的固定顺序」而是一套算法算出来的。理解它能解释两件面试常问的事：super() 到底调谁、以及为什么 mixin 类永远要放在右边。",
    "mechanism": [
      "① 单继承链的 MRO 就是自己→父→祖父，线性的一眼能看出来",
      "② 多继承时每个父类又各有自己的 MRO，需要合并成一个列表：C3 线性化",
      "③ C3 第一原则：子类永远排在自己的父类前面（否则父类会先于子类被搜到，覆写失效）",
      "④ C3 第二原则：合并必须保持每个父类链的相对顺序单调不降（A→B→C 的顺序不能被拆开重排）",
      "⑤ 两条规则冲突时无法同时满足，就说明这个继承体系设计有问题 —— Python 直接抛 TypeError: Cannot create a consistent method resolution order",
      "⑥ 菱形继承（D 同时继承 B 和 C，B/C 又都继承 A）就是典型冲突：A 必须同时排在 B、C 之后，但 B 和 C 的顺序一旦定了就无法满足A 的单调性",
      "⑦ 所以 mixin 类永远写在最右侧（如 class S(Concrete, Mixin)），它只提供方法、不参与 MRO 决策",
      "⑧ super() 不是「调父类」而是「调 MRO 里的下一个」，cooperative multiple inheritance 里每个类都super() 才能把链条走完"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "D(Child)",
        "B(Left)",
        "C(Right)",
        "A(Base)"
      ],
      "frames": [
        {
          "s": 0,
          "note": "自己排最前（规则一）"
        },
        {
          "s": 1,
          "note": "B 先于它的父类 A"
        },
        {
          "s": 2,
          "note": "C 也必须先于 A"
        },
        {
          "s": 3,
          "note": "A 在 B、C 之后才是合法顺序"
        }
      ]
    },
    "interviewQ": [
      "super() 调的是父类还是 MRO 里的下一个？",
      "为什么 mixin 类必须写在继承列表最右边？",
      "C3 线性化的两条约束分别是什么？",
      "class D(B, C): B 和 C 都继承 A，能建成功吗？为什么？"
    ],
    "keywords": [
      "MRO",
      "方法解析顺序",
      "C3线性化",
      "多继承",
      "mixin",
      "super",
      "TypeError",
      "继承",
      "多态"
    ],
    "scene": [
      "class D(B, C)，B 和 C 都继承 A，报 TypeError: Cannot create a consistent MRO —— 因为 A 无法既在 B 之后又在 C 之后还满足单调性。",
      "调试时发现 f() 明明在父类里却没被调到，打印 cls.__mro__ 才看出来中间某个类写了 super() 但没调cooperative 链。"
    ],
    "tags": [
      "面向对象",
      "继承",
      "算法",
      "Python进阶"
    ],
    "related": [
      {
        "id": "python-abc-protocol",
        "kind": "extends",
        "note": "同为「怎么定义行为契约」，ABC 走继承、Protocol 走结构化子类型"
      },
      {
        "id": "python-descriptor",
        "kind": "extends",
        "note": "属性查找走 MRO 时会触发 __getattr__ 与描述符 __get__"
      },
      {
        "id": "python-oop-dunder",
        "kind": "extends",
        "note": "dunder 方法也在 MRO 里被查找，是实现运算重载的基础"
      }
    ]
  }
];
if (typeof module !== "undefined" && module.exports) { module.exports = CARDS_GAP_2026_10; }
