// 严格 JSON 字面量：Node(vm) 与 Python(json) 都能直接读，请勿改回单引号
// 前端知识点补齐（2026-10-09）：原来只有 4 张（渲染流程 / Event Loop / 闭包），
// 补齐到 24 张 —— 覆盖 CSS 原理、浏览器机制、框架原理、工程化、可访问性。
var CARDS_FE_2 = [
  {
    "id": "fe-css-specificity",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "CSS 原理",
      "选择器优先级与层叠"
    ],
    "title": "CSS 优先级怎么算？为什么「内联 > id > class」不是铁律？",
    "oneLine": "优先级由三元组 (id, class/属性/伪类, 标签) 逐位比较得出，加!important 直接置顶。",
    "analogy": "像比赛打分：三个赛道分别记分（id 赛道、class 赛道、标签赛道），先比第一赛道，平了才看第二赛道——不是简单加总。",
    "why": "没有优先级规则，网页端任何一处样式改动都会被别处意外覆盖，改一处崩一片。",
    "mechanism": [
      "① 每个选择器算出一个三元组 (a,b,c)：a=id 数、b=class/属性/伪类数、c=标签/伪元素数",
      "② 逐位比较：先比 a，相同才比 b，相同才比 c——所以 id=1 的 class=99 依然赢过 id=0 的 class=999",
      "③ !important 在进入比较前就把该条标记为最高优先级（important 内部再按三元组比）",
      "④ 层叠上下文（transform/filter/z-index 非auto 等）会创建新的「作用域」，外部样式一律进不来",
      "⑤ 优先级相同则看「层叠顺序」：行内样式 > 浏览器默认 > 用户自定义"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "n1",
          "label": "匹配选择器"
        },
        {
          "id": "n2",
          "label": "算三元组"
        },
        {
          "id": "n3",
          "label": "!important?"
        },
        {
          "id": "n4",
          "label": "层叠上下文内比"
        },
        {
          "id": "n5",
          "label": "层叠顺序兜底"
        }
      ],
      "edges": [
        {
          "from": "n1",
          "to": "n2",
          "label": "逐位"
        },
        {
          "from": "n2",
          "to": "n3",
          "label": "检查"
        },
        {
          "from": "n3",
          "to": "n4",
          "label": "同一作用域内"
        },
        {
          "from": "n4",
          "to": "n5",
          "label": "相同"
        }
      ],
      "frames": [
        {
          "note": "选择器匹配后，每个都算出 (id, class, 标签) 三元组",
          "n": "n1"
        },
        {
          "note": "逐位比较而非加总：id 数优先，相同才看 class 数",
          "n": "n2"
        },
        {
          "note": "!important 不是最高，它只比普通声明优先",
          "n": "n3"
        },
        {
          "note": "层叠上下文会隔离外部样式（transform/filter 会创建新上下文）",
          "n": "n4"
        }
      ]
    },
    "interviewQ": [
      "为什么 .a.b.c 比 #x 优先级低？",
      "transform 为什么会意外让 z-index 失效？",
      "!important 和 specificity 谁先算？"
    ],
    "keywords": [
      "优先级",
      "specificity",
      "层叠",
      "important",
      "层叠上下文",
      "z-index"
    ],
    "scene": [
      "写业务组件时被全局样式覆盖，排查半天最后发现是选择器写得不够具体。",
      "第三方 UI 库样式改不动，用!important 强压——于是又制造了新的优先级冲突。"
    ],
    "tags": [
      "CSS",
      "优先级",
      "层叠"
    ],
    "related": [
      {
        "id": "fe-bfc",
        "kind": "compare",
        "note": "BFC 解决的是布局外溢，与优先级是两套正交机制"
      },
      {
        "id": "fe-flex-layout",
        "kind": "compare",
        "note": "布局属性之间也遵循优先级规则"
      }
    ]
  },
  {
    "id": "fe-bfc",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "CSS 原理",
      "BFC 与包含块"
    ],
    "title": "BFC 是什么？为什么清浮动、父元素塌陷都靠它？",
    "oneLine": "BFC 是一个「独立的排版上下文」，内部元素的浮动不会影响外部，外部浮动也不会影响内部。",
    "analogy": "像给房间拉一道帘子：帘子里的布局怎么折腾都不影响帘子外，帘子外的也不飘进里面。",
    "why": "浮动元素会脱离文档流，导致父元素高度塌陷、子元素重叠——BFC 是最标准的解法。",
    "mechanism": [
      "① 触发条件：overflow 非 visible、float 非 none、position 为 absolute/fixed、display:flex/grid、contain:content 等",
      "② 形成后，内部元素的浮动被限制在内部，外部浮动不会「飘进来」干扰",
      "③ BFC 元素的高度会自动包含内部浮动元素（因为它计算高度时会把浮动算进去）→ 解决父元素塌陷",
      "④ margin 不再与子元素外边距折叠（两个 BFC 之间不折叠）",
      "⑤ 注意：overflow:hidden 虽能触发 BFC，但会裁切内容，慎用来「顺手清浮动」"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "建立 BFC",
        "限制浮动外溢",
        "包含内部浮动",
        "阻止外边距折叠"
      ],
      "frames": [
        {
          "s": 0,
          "note": "overflow:hidden / display:flex 等都能触发"
        },
        {
          "s": 1,
          "note": "内部浮动不外泄，外部浮动不进入"
        },
        {
          "s": 2,
          "note": "高度自动包含浮动 → 父元素不再塌陷"
        },
        {
          "s": 3,
          "note": "相邻 BFC 的 margin 不折叠"
        }
      ]
    },
    "interviewQ": [
      "overflow:hidden 有什么副作用？",
      "BFC 和包含块（containing block）有什么区别？",
      "为什么 display:flex 会成为 BFC？"
    ],
    "keywords": [
      "BFC",
      "包含块",
      "浮动",
      "外边距折叠",
      "塌陷"
    ],
    "scene": [
      "父元素包着 float 子元素，页面结构突然塌成一团，加 overflow:hidden 立刻好了。",
      "两列布局之间莫名多出一段空隙，其实是相邻 margin 折叠被 BFC 阻止了。"
    ],
    "tags": [
      "CSS",
      "布局",
      "BFC"
    ],
    "related": [
      {
        "id": "fe-css-specificity",
        "kind": "compare",
        "note": "BFC 管布局隔离，优先级管谁生效"
      }
    ]
  },
  {
    "id": "fe-margin-collapse",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "CSS 原理",
      "外边距折叠"
    ],
    "title": "垂直方向两个 margin 为什么会合并成一个？",
    "oneLine": "块级布局中相邻的两个垂直 margin 只取最大值，不会相加——这是为了避免空白过大。",
    "analogy": "两张纸叠在一起，它们之间的缝是上面那张的下边距和下面那张的上边距里**较大**的那个，不是相加。",
    "why": "如果相加，段落间空隙会随嵌套层数指数级膨胀，排版完全失控。",
    "mechanism": [
      "① 只发生在**块级**元素的**垂直**方向（水平方向不折叠）",
      "② 相邻兄弟元素的 margin-bottom 与 margin-top 折叠，取 max(|a|,|b|)",
      "③ 父子元素之间：子元素没有 border/padding/overflow:hidden 隔开时，子的 margin-top 会与父的合并（塌陷出去）",
      "④ 空元素的上下 margin 也折叠",
      "⑤ BFC 内部的 margin 不与外部折叠，flex/grid 容器内子项 margin 也不折叠"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "折叠前",
          "lines": [
            "20px",
            "30px",
            "20px"
          ],
          "note": "三个 margin"
        },
        {
          "title": "折叠后",
          "lines": [
            "30px",
            "20px"
          ],
          "note": "取最大值 30"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "上下两个 20px 和一个 30px"
        },
        {
          "s": 1,
          "note": "相邻折叠取 max，结果是 30 和 20"
        }
      ]
    },
    "interviewQ": [
      "如何阻止父子 margin 折叠？",
      "为什么 flex 容器的子项 margin 不会折叠？",
      "折叠和 BFC 的关系是什么？"
    ],
    "keywords": [
      "外边距折叠",
      "margin",
      "塌陷",
      "布局"
    ],
    "scene": [
      "给父元素加 padding 后子元素不再顶出去，一验证就是 margin 折叠在作怪。",
      "两个卡片竖排时只改了 margin-bottom，结果间距被上面那个更大的 margin-top 顶开。"
    ],
    "tags": [
      "CSS",
      "margin",
      "布局"
    ],
    "related": [
      {
        "id": "fe-bfc",
        "kind": "extends",
        "note": "BFC 是阻止折叠最常用的手段"
      }
    ]
  },
  {
    "id": "fe-flex-layout",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "CSS 布局",
      "Flex 布局"
    ],
    "title": "Flex 为什么能省掉那么多代码？主轴副轴是怎么算的？",
    "oneLine": "Flex 把「谁在剩余空间里分配」交给 justify-content 和 align-items，一条轴向布局彻底不用算宽度。",
    "analogy": "像分配一排插座：主轴方向决定插几个、怎么排，副轴方向决定每个插座上下的东西怎么摆。",
    "why": "垂直居中在 Flex 之前需要绝对定位 + 负 margin，现在三行搞定。",
    "mechanism": [
      "① 父容器 display:flex 后，子项成为 flex item，主轴由 flex-direction 决定（默认 row 水平）",
      "② 剩余空间分配由 justify-content 控制（flex-start/center/space-between/space-around）",
      "③ 交叉轴上的对齐由 align-items 控制（stretch/center/baseline 等）",
      "④ flex: 1 = flex-grow:1 + flex-shrink:1 + flex-basis:0%，**basis 为 0 才是等分的关键**",
      "⑤ gap 比 margin 好在：不会在首尾也产生间距，overflow 滚动时也不会有「最后一个多一个 margin」的坑",
      "⑥ min-width:auto 是 flex item 的隐式最小尺寸，内容过宽时会撑破容器，需用 min-width:0 覆盖"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "定主轴",
        "分配剩余空间",
        "交叉轴对齐",
        "计算 flex"
      ],
      "frames": [
        {
          "s": 0,
          "note": "flex-direction 决定主轴方向，默认 row"
        },
        {
          "s": 1,
          "note": "justify-content 分配剩余空间"
        },
        {
          "s": 2,
          "note": "align-items 管交叉轴对齐"
        },
        {
          "s": 3,
          "note": "flex:1 的 basis 是 0%，所以等分"
        }
      ]
    },
    "interviewQ": [
      "flex:1 到底等价于哪三个属性？",
      "为什么 flex 子项内容过宽会撑破容器？",
      "gap 和 margin 哪个更适合 flex？"
    ],
    "keywords": [
      "Flex",
      "flexbox",
      "justify-content",
      "align-items",
      "flex:1",
      "gap"
    ],
    "scene": [
      "做等分三栏布局，flex:1 一行搞定，Grid 出来后就换了 grid-template-columns。",
      "横向滚动列表用 margin 排间距，结果最后一个元素右侧多出一截空白，改成 gap 立刻干净。"
    ],
    "tags": [
      "CSS",
      "Flex",
      "布局"
    ],
    "related": [
      {
        "id": "fe-grid-layout",
        "kind": "compare",
        "note": "Grid 是二维、Flex 是一维，选择看布局维度"
      },
      {
        "id": "fe-bfc",
        "kind": "compare",
        "note": "Flex 容器会自动成为 BFC"
      }
    ]
  },
  {
    "id": "fe-grid-layout",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "CSS 布局",
      "Grid 布局"
    ],
    "title": "Grid 和 Flex 怎么选？为什么 Grid 能做「真正的等高」？",
    "oneLine": "Grid 是二维布局（行+列同时控制），Flex 是一维；Grid 的行高由最高项决定，天然等高。",
    "analogy": "Flex 像排队 horizontally，一维一列；Grid 像填 Excel 表格，可以同时定行和列。",
    "why": "卡片列表要求每行等高对齐，Flex 要靠 align-items 妥协，Grid 直接用行定义就解决。",
    "mechanism": [
      "① display:grid 后用 grid-template-columns/rows 定义轨道（track）",
      "② fr 单位表示「剩余空间的比例分配」，1fr 1fr 即两等分",
      "③ auto-fit / auto-fill + minmax() 实现响应式：不用写媒体查询就自动换行",
      "④ 行高由该行最高元素决定 → 同一行的卡片自动等高（Flex 做不到）",
      "⑤ 子项可用 grid-column/grid-row 显式放到指定区域，做复杂的杂志式排版",
      "⑥ gap 同时支持行和列，比 margin 干净"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "Grid",
          "lines": [
            "┌──┬──┬──┐",
            "├──┼──┼──┤",
            "└──┴──┴──┘"
          ],
          "note": "行列表同时定义"
        },
        {
          "title": "Flex",
          "lines": [
            "[ ] [ ] [ ]"
          ],
          "note": "只有一维方向"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "Grid 同时控制行和列"
        },
        {
          "s": 1,
          "note": "Flex 只能控制一个方向"
        }
      ]
    },
    "interviewQ": [
      "auto-fit 和 auto-fill 的区别是什么？",
      "为什么 Grid 能等高而 Flex 不能？",
      "fr 和百分比的区别？"
    ],
    "keywords": [
      "Grid",
      "grid-template",
      "fr",
      "auto-fit",
      "minmax",
      "等高"
    ],
    "scene": [
      "做卡片墙要求每行等高，Flex 方案需要 flex-wrap + 各种 hack，Grid 一行搞定。",
      "响应式列数用 auto-fit + minmax(250px, 1fr)，省掉一堆媒体查询。"
    ],
    "tags": [
      "CSS",
      "Grid",
      "布局"
    ],
    "related": [
      {
        "id": "fe-flex-layout",
        "kind": "compare",
        "note": "二维 vs 一维，最常被问的对比题"
      }
    ]
  },
  {
    "id": "fe-reflow-repaint",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "浏览器机制",
      "重排重绘与合成"
    ],
    "title": "重排、重绘、合成有什么区别？哪个最贵？",
    "oneLine": "重排(Layout)最贵→重绘(Paint)次之→合成(Composite)最便宜，动画尽量只走合成。",
    "analogy": "重排像重新排版整个房间的家具，重绘像换墙纸（布局没动），合成像只换了一张贴图。",
    "why": "性能优化的本质就是「避开重排」，把动画约束在合成层。",
    "mechanism": [
      "① 重排：几何属性（宽高位置 margin padding）变化 → 重新计算布局，牵连整个文档树，代价最高",
      "② 重绘：颜色/背景/阴影等绘制属性变化 → 布局没变，但要重新画像素",
      "③ 合成：transform / opacity 变化 → 不需要重排重绘，只是把已有图层重新组合，最快",
      "④ 浏览器的优化：批量修改样式只触发一次重排（读写分离，避免 layout thrashing）",
      "⑤ will-change: transform 提示浏览器提前提升为合成层，但**滥用会反噬**（图层过多显存爆炸）",
      "⑥ 用 Performance 面板看 Layout / Paint 的耗时，而不是凭感觉猜"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "修改样式",
        "重排 Layout",
        "重绘 Paint",
        "合成 Composite"
      ],
      "frames": [
        {
          "s": 0,
          "note": "改 width 触发重排——最贵"
        },
        {
          "s": 1,
          "note": "重排要重新计算几何信息"
        },
        {
          "s": 2,
          "note": "改 background 只重绘"
        },
        {
          "s": 3,
          "note": "transform/opacity 只合成——最便宜"
        }
      ]
    },
    "interviewQ": [
      "什么是 layout thrashing？怎么避免？",
      "为什么 transform 做动画比 left/top 快？",
      "will-change 用的越多越好吗？"
    ],
    "keywords": [
      "重排",
      "重绘",
      "合成",
      "reflow",
      "repaint",
      "composite",
      "性能"
    ],
    "scene": [
      "做滚动联动动画时用了 top/left，页面卡成幻灯片——改成 transform 后瞬间流畅。",
      "循环里读 offsetTop 又写 style，触发强制同步重排，帧率直接掉一半。"
    ],
    "tags": [
      "性能",
      "浏览器",
      "动画"
    ],
    "related": [
      {
        "id": "fe-browser-rendering",
        "kind": "extends",
        "note": "这几个阶段就在渲染流水线里"
      },
      {
        "id": "fe-event-loop",
        "kind": "compare",
        "note": "JS 执行与渲染的时序协作"
      }
    ]
  },
  {
    "id": "fe-long-task",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "浏览器机制",
      "长任务与渲染阻塞"
    ],
    "title": "为什么 JS 执行久了页面会卡住甚至假死？",
    "oneLine": "主线程是单线程，长任务会阻塞渲染和输入处理，所以超过 50ms 就要拆分或让出。",
    "analogy": "只有一名厨师（主线程），做菜期间没人能点单上菜（渲染和交互都排队）。",
    "why": "用户感觉「卡」的直接原因不是计算慢，而是长时间占着主线程不让它响应。",
    "mechanism": [
      "① 浏览器主线程同时负责 JS 执行、样式计算、布局、绘制、事件处理",
      "② 一段超过 50ms 的任务就是「长任务」，期间浏览器无法响应用户输入也无法出帧",
      "③ 超过 200ms 的长任务会显著拖垮交互体验（Long Tasks API 定义）",
      "④ 拆分方案：大计算分片 + await 让出主线程，或放进 Web Worker",
      "⑤ requestIdleCallback 用于在空闲时间做低优先级任务",
      "⑥ 可用 PerformanceObserver('longtask') 埋点监控真实长任务"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "长任务开始",
        "阻塞渲染",
        "阻塞输入",
        "结束后恢复"
      ],
      "frames": [
        {
          "s": 0,
          "note": "单段JS 持续占用主线程"
        },
        {
          "s": 1,
          "note": "无法出帧 → 画面卡住"
        },
        {
          "s": 2,
          "note": "输入事件排队 → 点击无响应"
        },
        {
          "s": 3,
          "note": "任务结束才恢复"
        }
      ]
    },
    "interviewQ": [
      "怎么拆分长任务？",
      "Web Worker 适合什么场景？",
      "如何监控长任务？"
    ],
    "keywords": [
      "长任务",
      "主线程",
      "阻塞",
      "Worker",
      "requestIdleCallback"
    ],
    "scene": [
      "点击按钮后页面卡住两秒——for 循环里做了同步的大数据处理。",
      "表格渲染 5000 行卡死，后来改虚拟滚动 + 分片渲染才顺。"
    ],
    "tags": [
      "性能",
      "主线程",
      "异步"
    ],
    "related": [
      {
        "id": "fe-event-loop",
        "kind": "extends",
        "note": "任务与微任务的调度顺序决定何时能出帧"
      }
    ]
  },
  {
    "id": "fe-xss-csp",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "安全",
      "XSS 与 CSP"
    ],
    "title": "XSS 是怎么发生的？CSP 为什么能防住它？",
    "oneLine": "XSS 是把可执行脚本当成数据注入页面，CSP 通过白名单限制资源来源与执行。",
    "analogy": "XSS 像是有人在你家门上贴了张纸说「照这上面写的做」，而 CSP 就是门卫，只放行登记过的内容。",
    "why": "前端渲染不可信数据时，XSS 能偷 Cookie、劫持会话、改页面内容。",
    "mechanism": [
      "① 三类 XSS：存储型（数据入库后影响所有用户）、反射型（URL 参数即触发）、DOM 型（前端拼接后触发）",
      "② 根本原因是**把不可信数据当代码执行**——innerHTML、eval、字符串拼 script",
      "③ 防御第一原则：输出编码 + 用 textContent 代替 innerHTML",
      "④ CSP 通过 script-src 白名单限制脚本来源，'unsafe-inline' 会让内联脚本全放行",
      "⑤ 配合 Trusted Types，从类型层面杜绝字符串注入 HTML",
      "⑥ HttpOnly cookie 能防住 XSS 偷 token，但防不住 XSS 代替用户发请求"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "注入脚本",
        "执行任意 JS",
        "窃取凭据",
        "发起恶意请求"
      ],
      "frames": [
        {
          "s": 0,
          "note": "输入未经编码进入 innerHTML"
        },
        {
          "s": 1,
          "note": "脚本被当作代码执行"
        },
        {
          "s": 2,
          "note": "Cookie/token 被读走"
        },
        {
          "s": 3,
          "note": "以用户身份发起操作"
        }
      ]
    },
    "interviewQ": [
      "存储型 XSS 和反射型的区别？",
      "CSP 能防住所有 XSS 吗？",
      "为什么 HttpOnly cookie 不能完全防住 XSS？"
    ],
    "keywords": [
      "XSS",
      "CSP",
      "innerHTML",
      "安全",
      "TrustedTypes"
    ],
    "scene": [
      "富文本编辑器渲染用户评论，昵称里塞 <script> 直接被执行了。",
      "接入第三方脚本后担心供应链风险，用 CSP 白名单限制了来源。"
    ],
    "tags": [
      "安全",
      "XSS",
      "CSP"
    ],
    "related": [
      {
        "id": "fe-storage-cookie",
        "kind": "compare",
        "note": "Token 存哪决定了 XSS 的危害面"
      }
    ]
  },
  {
    "id": "fe-storage-cookie",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "安全",
      "存储与 Cookie"
    ],
    "title": "localStorage 和 Cookie 有什么区别？JWT 该放哪？",
    "oneLine": "localStorage 大但能被 JS 读走，Cookie 有 HttpOnly 保护但只有 4KB 且每次请求都带。",
    "analogy": "localStorage 是抽屉里的明文日记，Cookie 是带锁的保险箱钥匙——但钥匙可以配「只进不出」。",
    "why": "这决定了 XSS 能偷到什么，也决定了跨域和 CSRF 的风险面。",
    "mechanism": [
      "① localStorage/sessionStorage：5~10MB、无过期（sessionStorage 关标签页即清）、**JS 可读**",
      "② Cookie：每条≤4KB、可设 HttpOnly/Secure/SameSite/Domain/Path、有过期",
      "③ HttpOnly 的 cookie JS 读不到 → XSS 偷不走，但**依然会被浏览器自动带上发送**",
      "④ SameSite=Lax/Strict 是防 CSRF 的关键（跨站请求不带 cookie）",
      "⑤ token 存 localStorage → XSS 可直接拿走；存 HttpOnly cookie → XSS 偷不走但仍可代替用户发请求",
      "⑥ 刷新页面时内存态（Pinia/Vuex）会丢，需要「首屏从存储恢复 → 再调 me 接口校验」"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "s1",
          "label": "存 token"
        },
        {
          "id": "s2",
          "label": "HttpOnly?"
        },
        {
          "id": "s3",
          "label": "XSS 可读"
        },
        {
          "id": "s4",
          "label": "CSRF 风险"
        }
      ],
      "edges": [
        {
          "from": "s1",
          "to": "s2",
          "label": "看方案"
        },
        {
          "from": "s2",
          "to": "s3",
          "label": "否"
        },
        {
          "from": "s2",
          "to": "s4",
          "label": "是但依赖SameSite"
        }
      ],
      "frames": [
        {
          "note": "两种方案风险面完全不同",
          "n": "s1"
        },
        {
          "note": "HttpOnly 让 JS 读不到",
          "n": "s2"
        },
        {
          "note": "但仍会被浏览器自动带上",
          "n": "s3"
        },
        {
          "note": "需要 SameSite 挡 CSRF",
          "n": "s4"
        }
      ]
    },
    "interviewQ": [
      "JWT 存 localStorage 还是 Cookie？为什么？",
      "SameSite 怎么防 CSRF？",
      "为什么刷新后要调 me 接口？"
    ],
    "keywords": [
      "localStorage",
      "Cookie",
      "HttpOnly",
      "SameSite",
      "JWT",
      "CSRF"
    ],
    "scene": [
      "刷新页面后用户被踢回登录——token 存在内存里没持久化到存储。",
      "跨域请求带不上 cookie，查了一圈是 SameSite 默认值在挡。"
    ],
    "tags": [
      "安全",
      "存储",
      "Cookie",
      "JWT"
    ],
    "related": [
      {
        "id": "fe-xss-csp",
        "kind": "compare",
        "note": "XSS 的危害面取决于 token 存在哪"
      },
      {
        "id": "cs-netq13",
        "kind": "compare",
        "note": "相关：cs-netq13"
      }
    ]
  },
  {
    "id": "fe-component-render",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "框架原理",
      "组件渲染与更新"
    ],
    "title": "Vue 的响应式是怎么做到「数据变了视图自动更新」的？",
    "oneLine": "用 Proxy 拦截属性读写，读取时收集依赖，写入时触发依赖重跑，实现细粒度更新。",
    "analogy": "像给每个数据项装了报警器：谁读了谁被登记（依赖收集），一改就通知登记过的人（触发更新）。",
    "why": "理解这一套，才知道为什么「直接改对象深层属性也能更新」而有些情况不会。",
    "mechanism": [
      "① reactive(obj) 返回 Proxy，get 拦截里把当前正在求值的组件（effect）记进该属性的依赖集合",
      "② set 拦截里从依赖集合取出所有 effect 并执行 → 组件重新渲染",
      "③ 依赖是「按属性」细粒度记录的：只改了 a 就只重渲用到 a 的组件，不是整页重渲",
      "④ ref 是包装类型，通过 .value 访问，单值场景更方便（能用于基本类型）",
      "⑤ 丢失响应式的典型：解构（const {a} = reactive(obj)）、把 Proxy 赋给普通变量、数组用 length赋值",
      "⑥ ref 的响应式是「自动解包」的，模板里直接写 count 而非 count.value"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "读取属性",
        "收集依赖(effect)",
        "修改属性",
        "触发更新"
      ],
      "frames": [
        {
          "s": 0,
          "note": "组件渲染时读取 obj.a"
        },
        {
          "s": 1,
          "note": "get 拦截里把当前 effect 存进 dep"
        },
        {
          "s": 2,
          "note": "改 obj.a 触发 set 拦截"
        },
        {
          "s": 3,
          "note": "取出 dep 里的 effect 重跑"
        }
      ]
    },
    "interviewQ": [
      "为什么解构会丢失响应式？",
      "Vue2 和 Vue3 响应式的区别？",
      "computed 和 watch 的区别？"
    ],
    "keywords": [
      "响应式",
      "Proxy",
      "依赖收集",
      "effect",
      "ref",
      "reactive"
    ],
    "scene": [
      "const { a } = reactive(data) 之后改 data.a，界面不更新——依赖收集时的解构已经断了链。",
      "面试被问「Vue3 为什么比 Vue2 快」，答核心是 Proxy 替代 defineProperty。"
    ],
    "tags": [
      "Vue",
      "响应式",
      "框架原理"
    ],
    "related": [
      {
        "id": "fe-vdom-diff",
        "kind": "extends",
        "note": "数据变了之后，视图怎么最小化更新"
      },
      {
        "id": "fe-closure-scope",
        "kind": "compare",
        "note": "响应式本质是语言机制上的依赖追踪"
      }
    ]
  },
  {
    "id": "fe-vdom-diff",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "框架原理",
      "虚拟 DOM 与 Diff"
    ],
    "title": "虚拟 DOM 存在的意义是什么？Diff 为什么用双端比较？",
    "oneLine": "用 JS 对象描述 DOM，让「先算差异再改」比直接操作 DOM 便宜；Diff 假设同层结构不变来剪枝。",
    "analogy": "像装修前先在图纸上比一遍，改动少才开工——而不是一上来就砸墙。",
    "why": "直接改 DOM 频繁触发重排重绘，而批量对比后只改真正变了的节点。",
    "mechanism": [
      "① 虚拟 DOM 是纯 JS 对象树，创建成本远低于真实 DOM 操作（后者跨 C++ 边界）",
      "② Diff 同层比较，复杂度 O(n)；跨层比较成本太高所以直接放弃（现实页面结构通常稳定）",
      "③ 四步流程：同 key 比较 → 类型不同则重建 → key 相同则复用 → 更新属性",
      "④ key 是复用的依据：用 index 做 key 时，列表头部插入会导致后面全部重建",
      "⑤ Vue3 用 patchFlag 标记静态/动态节点，跳过无变化的部分",
      "⑥ 虚拟 DOM 不是银弹：极小范围内直接改 DOM 反而更快"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "生成 vnode",
        "同层比较",
        "key 匹配",
        "最小 patch"
      ],
      "frames": [
        {
          "s": 0,
          "note": "状态变化 → 重新生成 vnode"
        },
        {
          "s": 1,
          "note": "只比同一层，不跨层"
        },
        {
          "s": 2,
          "note": "key 决定能否复用 DOM"
        },
        {
          "s": 3,
          "note": "只把差异应用到真实 DOM"
        }
      ]
    },
    "interviewQ": [
      "为什么列表要用 key？index 行不行？",
      "虚拟 DOM 为什么不一定更快？",
      "Vue3 的 diff 做了哪些优化？"
    ],
    "keywords": [
      "虚拟DOM",
      "VDOM",
      "diff",
      "key",
      "patch",
      "复用"
    ],
    "scene": [
      "列表头部插入一条数据，整列表项重建导致输入框失焦——因为 key 用了 index。",
      "面试被问「虚拟 DOM 一定比直接操作快吗」，答：小范围直接操作更快。"
    ],
    "tags": [
      "框架原理",
      "虚拟DOM",
      "Diff"
    ],
    "related": [
      {
        "id": "fe-component-render",
        "kind": "extends",
        "note": "组件更新最终落到 diff + patch"
      },
      {
        "id": "fe-reflow-repaint",
        "kind": "compare",
        "note": "虚拟 DOM 的价值就是把重排次数降下来"
      },
      {
        "id": "fe-browser-rendering",
        "kind": "compare",
        "note": "相关：fe-browser-rendering"
      }
    ]
  },
  {
    "id": "fe-webpack-vite",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "工程化",
      "构建工具与打包"
    ],
    "title": "Vite 为什么比 Webpack 快？ESM 和预构建是关键",
    "oneLine": "Webpack 打包全部后再启动（冷启动慢），Vite 依赖预构建 + 按需转译（启动快）。",
    "analogy": "Webpack 像先把整本书排完版再给你读；Vite 像先给你目录，你翻到哪页才排那页。",
    "why": "开发时每次改代码都要重新构建，打包速度直接决定开发体验。",
    "mechanism": [
      "① Webpack 冷启动要先遍历整个依赖图构建产物，启动才能开始",
      "② Vite 用浏览器原生 ESM：源码按需通过 HTTP 直接给浏览器，不预打包",
      "③ 但裸模块导入（import x from 'lodash'）浏览器不认识 → Vite 把它们预构建成单个 ESM 文件（esbuild）",
      "④ 新依赖被改到时才重新预构建（按需 + 缓存）",
      "⑤ HMR 时 Vite 只把「变更模块 + 其接受方」推给浏览器，不必全量刷新",
      "⑥ 生产构建 Rollup 打包（Vite 用 esbuild 打包依赖、Rollup 处理产物）"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "b1",
          "label": "启动"
        },
        {
          "id": "b2",
          "label": "依赖预构建(esbuild)"
        },
        {
          "id": "b3",
          "label": "源码原生ESM"
        },
        {
          "id": "b4",
          "label": "按需转译"
        }
      ],
      "edges": [
        {
          "from": "b1",
          "to": "b2",
          "label": "只处理裸模块"
        },
        {
          "from": "b2",
          "to": "b3",
          "label": "源码不走打包"
        },
        {
          "from": "b3",
          "to": "b4",
          "label": "用到才转"
        }
      ],
      "frames": [
        {
          "note": "启动不打包业务源码",
          "n": "b1"
        },
        {
          "note": "只预构建 node_modules 裸模块",
          "n": "b2"
        },
        {
          "note": "源码保持 ESM 直接给浏览器",
          "n": "b3"
        },
        {
          "note": "首次访问时才转译，所以启动快",
          "n": "b4"
        }
      ]
    },
    "interviewQ": [
      "Vite 的依赖预构建解决了什么问题？",
      "生产构建为什么 Vite 又用 Rollup？",
      "HMR 怎么做到不刷新页面？"
    ],
    "keywords": [
      "Vite",
      "Webpack",
      "ESM",
      "HMR",
      "预构建",
      "构建"
    ],
    "scene": [
      "换到 Vite 后冷启动从几十秒降到一秒内——差别就在「启动前是否全量打包」。",
      "遇到某个新装的库在开发时不生效，报错提示要用 optimizeDeps.include 强制预构建。"
    ],
    "tags": [
      "工程化",
      "Vite",
      "构建"
    ],
    "related": [
      {
        "id": "fe-code-split",
        "kind": "extends",
        "note": "按需加载是构建工具的另一核心能力"
      }
    ]
  },
  {
    "id": "fe-code-split",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "工程化",
      "代码分割与懒加载"
    ],
    "title": "代码分割怎么做？动态 import 为什么能减小首屏体积？",
    "oneLine": "把大包拆成多个 chunk，按需 import 时才下载对应文件，首屏只加载必需的。",
    "analogy": "像超市按品类进货：你要什么才拿什么，不是一次把整个仓库搬进家。",
    "why": "首屏加载时间是用户感知性能的第一指标，路由级分割收益最大。",
    "mechanism": [
      "① 动态 import() 返回 Promise，Webpack/Vite 会自动把它切成独立 chunk",
      "② 路由级分割：每个页面组件单独一个 chunk，配合 loading 态",
      "③ 库级分割：React/Vue 等大库抽成 vendor chunk，利用长期缓存",
      "④ ⚠️ 注意：动态 import 是「按需下载」，不是「不打包」——体积仍在总包里，只是分批下",
      "⑤ 预加载：路由 hover 时 <link rel=prefetch> 提前拉取，切换瞬间可用",
      "⑥ 配合 gzip/brotli 与 tree shaking 才有最大收益（分割解决「何时下」，tree shaking 解决「下多少」）"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "构建分包",
        "首屏加载main",
        "触发动态import",
        "下载对应chunk"
      ],
      "frames": [
        {
          "s": 0,
          "note": "构建期切成多个 chunk"
        },
        {
          "s": 1,
          "note": "首屏只下必需的部分"
        },
        {
          "s": 2,
          "note": "切换路由时才触发下载"
        },
        {
          "s": 3,
          "note": "用户几乎无感知等待"
        }
      ]
    },
    "interviewQ": [
      "代码分割和 tree shaking 的区别？",
      "动态 import 什么时候执行？",
      "首屏体积怎么进一步优化？"
    ],
    "keywords": [
      "代码分割",
      "懒加载",
      "动态import",
      "chunk",
      "tree shaking"
    ],
    "scene": [
      "首屏 2MB 白屏时间 6 秒，改成路由级分割后降到 800KB、白屏 1.5 秒。",
      "图表库整包引入太重，改成按需 import 后包体降了 700KB。"
    ],
    "tags": [
      "性能",
      "工程化",
      "打包"
    ],
    "related": [
      {
        "id": "fe-webpack-vite",
        "kind": "extends",
        "note": "打包工具提供分割能力"
      }
    ]
  },
  {
    "id": "fe-closure-memory-leak",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "JavaScript 核心",
      "闭包与作用域链"
    ],
    "title": "闭包为什么能「记住」外层变量？它有什么代价？",
    "oneLine": "函数保留了对外层作用域的引用，所以变量不会被回收；代价是内存常驻与可能的泄漏。",
    "analogy": "像把房间的钥匙带走——只要钥匙在（函数存在），房间（变量）就不能当垃圾扔掉。",
    "why": "事件监听、定时器、缓存都用它；但不控制好就会内存泄漏。",
    "mechanism": [
      "① 函数创建时会记住它的「词法环境」（作用域链），即使外层函数已返回",
      "② 外层变量被闭包引用 → 引用计数不归零 → 无法被 GC 回收",
      "③ 模块模式（IIFE / 模块作用域）用它实现私有变量，只暴露必要接口",
      "④ 循环里 var 定义函数会拿到「最后一个」值（同一个变量），需要用 let 或 IIFE 隔离",
      "⑤ 泄漏典型：事件监听解绑、闭包持有大对象、定时器未 clear",
      "⑥ 内存快照（Memory 面板）能看到 detach 的 DOM 节点数量异常"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "外层函数返回后",
          "lines": [
            "变量 x",
            "↑ 引用",
            "闭包函数"
          ],
          "note": "引用仍在"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "闭包持有外层变量引用 → 不被回收"
        }
      ]
    },
    "interviewQ": [
      "闭包的代价是什么？",
      "循环里 var 和 let 的闭包行为差异？",
      "怎么排查内存泄漏？"
    ],
    "keywords": [
      "闭包",
      "作用域链",
      "词法环境",
      "内存泄漏",
      "GC"
    ],
    "scene": [
      "定时器里引用了大数组，页面关闭后内存不降——闭包把数组锁住了。",
      "for 循环里注册监听，拿到的是最后一个变量的值，不是当轮的。"
    ],
    "tags": [
      "JavaScript",
      "闭包",
      "内存"
    ],
    "related": [
      {
        "id": "fe-event-loop",
        "kind": "extends",
        "note": "闭包 + 定时器是经典组合题"
      },
      {
        "id": "fe-component-render",
        "kind": "compare",
        "note": "响应式本质是语言级的依赖追踪"
      },
      {
        "id": "fe-closure-scope",
        "kind": "compare",
        "note": "相关：fe-closure-scope"
      }
    ]
  },
  {
    "id": "fe-weakref",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "JavaScript 核心",
      "垃圾回收机制"
    ],
    "title": "JS 的垃圾回收怎么工作？循环引用为什么能被回收？",
    "oneLine": "基于「可达性」而非「有没有引用计数」，从根对象不可达的就被回收，循环引用也不影响。",
    "analogy": "像清仓库：不是数每件东西被谁引用，而是问「从大门出发能不能走到它」，走不到就清掉。",
    "why": "理解可达性才能解释为什么 WeakMap 适合做缓存、为什么闭包会泄漏。",
    "mechanism": [
      "① 可达性算法：从根（window/document/全局变量）出发遍历引用图，到不了的回收",
      "② 循环引用（A 引 B、B 引 A 但都不可达）能被回收，因为从根走不到它们",
      "③ 分代假说：新生代多且短命（Scavenge），老生代少而长寿（标记整理）",
      "④ 增量标记（incremental marking）把长任务拆分，避免一次 GC 卡住主线程",
      "⑤ WeakMap/WeakRef 的 key 是弱引用，不阻止 GC——适合缓存与 DOM 关联数据",
      "⑥ 开发中内存问题多半是「意外变可达」而非算法失效：全局数组堆积、定时器未清"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "标记根对象",
        "遍历引用图",
        "不可达→回收",
        "整理碎片"
      ],
      "frames": [
        {
          "s": 0,
          "note": "从 window 等根出发"
        },
        {
          "s": 1,
          "note": "顺着引用标记可达节点"
        },
        {
          "s": 2,
          "note": "没被标记的才回收"
        },
        {
          "s": 3,
          "note": "循环引用不可达照样回收"
        }
      ]
    },
    "interviewQ": [
      "循环引用为什么能被 GC？",
      "WeakMap 适合什么场景？",
      "怎么定位内存泄漏？"
    ],
    "keywords": [
      "垃圾回收",
      "GC",
      "可达性",
      "WeakMap",
      "内存泄漏"
    ],
    "scene": [
      "把 DOM 节点放进全局数组后移除节点，内存不降——它仍然可达。",
      "用 WeakMap 缓存 DOM 节点的附加数据，节点被移除后缓存自动释放。"
    ],
    "tags": [
      "JavaScript",
      "GC",
      "内存"
    ],
    "related": [
      {
        "id": "fe-closure-scope",
        "kind": "extends",
        "note": "闭包是让对象意外可达的常见原因"
      }
    ]
  },
  {
    "id": "fe-proxy-reflect",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "JavaScript 核心",
      "Proxy 与 Reflect"
    ],
    "title": "Proxy 相比 Object.defineProperty 好在哪？Reflect 有什么用？",
    "oneLine": "Proxy 拦截整个对象的读写删除，defineProperty 只能逐个属性改；Reflect 提供统一的操作反射。",
    "analogy": "defineProperty 像逐个房间换锁，Proxy 像给整栋楼装智能门禁。",
    "why": "Vue3 用 Proxy 替代 defineProperty，正是因为后者无法拦截新增/删除属性。",
    "mechanism": [
      "① Proxy(obj, handler) 返回新代理，handler 里定义 get/set/deleteProperty/has 等陷阱",
      "② Object.defineProperty 只能一个个属性定义，且**新增属性无法被拦截**（响应式就漏了）",
      "③ Reflect 提供与 trap 对应的标准方法（Reflect.get/set/has/deleteProperty），避免重复写逻辑",
      "④ Reflect 的接收者语义正确——在 Proxy 里用 Reflect.get(target, key, receiver) 不会丢失 this",
      "⑤ 常用拦截：get 埋点、has 权限判断、deleteProperty 做禁止删除",
      "⑥ 陷阱必须遵守不变量：get 不能把不可变属性变成可写，否则 TypeError"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "x1",
          "label": "读 obj.a"
        },
        {
          "id": "x2",
          "label": "Proxy.get 陷阱"
        },
        {
          "id": "x3",
          "label": "Reflect.get"
        },
        {
          "id": "x4",
          "label": "返回结果"
        }
      ],
      "edges": [
        {
          "from": "x1",
          "to": "x2"
        },
        {
          "from": "x2",
          "to": "x3",
          "label": "标准实现"
        },
        {
          "from": "x3",
          "to": "x4"
        }
      ],
      "frames": [
        {
          "note": "所有属性访问都经过代理",
          "n": "x1"
        },
        {
          "note": "陷阱里可以自定义行为",
          "n": "x2"
        },
        {
          "note": "Reflect 避免重复实现、保持 receiver 正确",
          "n": "x3"
        }
      ]
    },
    "interviewQ": [
      "defineProperty 的局限在哪？",
      "Reflect 存在的意义是什么？",
      "Proxy 陷阱的不变量是什么？"
    ],
    "keywords": [
      "Proxy",
      "Reflect",
      "defineProperty",
      "拦截",
      "元编程"
    ],
    "scene": [
      "面试被问 Vue3 为什么不用 Object.defineProperty，答新增属性无法拦截导致响应式漏掉。",
      "用 Proxy 写权限控制：has 陷阱判断能否访问某个键。"
    ],
    "tags": [
      "JavaScript",
      "Proxy",
      "Reflect"
    ],
    "related": [
      {
        "id": "fe-component-render",
        "kind": "extends",
        "note": "Vue3 响应式就是基于 Proxy 实现"
      }
    ]
  },
  {
    "id": "fe-promise",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "JavaScript 核心",
      "Promise 与异步"
    ],
    "title": "Promise 的 then 回调是微任务，为什么 setTimeout 是宏任务？",
    "oneLine": "微任务在当前宏任务结束后立刻清空，宏任务排队逐个执行——这决定了两者的执行顺序。",
    "analogy": "微任务像「结账时顺手补上的零钱」，宏任务像「排队处理的正式业务」，前者先插队处理完。",
    "why": "宏/微任务的顺序是理解事件循环、定时器、Promise、Node 微任务队列的基础。",
    "mechanism": [
      "① 同步代码执行完 → 清空**所有**微任务（process.nextTick / Promise.then / MutationObserver）→ 再取一个宏任务",
      "② 微任务每次清空到空为止，宏任务一次只取一个 → 所以连续 then 会在 setTimeout 前全部跑完",
      "③ Promise 状态一旦被 pending 锁定，resolve/reject 只生效第一次（只能settle 一次）",
      "④ then 返回新 Promise，值会被 resolve（thenable 则展开），reject 状态直接透传",
      "⑤ Promise.all 等全部成功才成功（一个 reject 就全reject），Promise.allSettled 永不 reject",
      "⑥ async 函数返回 Promise，await 相当于挂起并把控制权交还事件循环"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "同步代码",
        "清空微任务",
        "取宏任务",
        "循环"
      ],
      "frames": [
        {
          "s": 0,
          "note": "同步代码先跑完"
        },
        {
          "s": 1,
          "note": "then 回调属于微任务，优先于定时器"
        },
        {
          "s": 2,
          "note": "setTimeout/IO 属于宏任务，一次一个"
        },
        {
          "s": 3,
          "note": "不断循环直到队列都空"
        }
      ]
    },
    "interviewQ": [
      "宏任务和微任务的执行顺序？",
      "Promise 只能 resolve 一次吗？",
      "async/await 和 then 的关系？"
    ],
    "keywords": [
      "Promise",
      "微任务",
      "宏任务",
      "then",
      "async",
      "await"
    ],
    "scene": [
      "面试经典题：setTimeout(()=>log(1), 0) + Promise.resolve().then(()=>log(2)) + log(3)，输出 3 2 1。",
      "接口请求偶尔被 setTimeout 抢先执行，查出来是宏微任务顺序问题。"
    ],
    "tags": [
      "JavaScript",
      "Promise",
      "异步"
    ],
    "related": [
      {
        "id": "fe-event-loop",
        "kind": "extends",
        "note": "微任务宏任务在事件循环中的位置"
      }
    ]
  },
  {
    "id": "fe-prototype",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "JavaScript 核心",
      "原型与继承"
    ],
    "title": "原型链是什么？为什么改构造函数的 prototype 能影响已有实例？",
    "oneLine": "实例查找属性时沿 [[Prototype]] 一路上溯，构造函数的 prototype 是实例的原型。",
    "analogy": "像查族谱：自己没有就问爸爸，再问爷爷，一直问到没有为止。",
    "why": "理解原型链才能解释 class extends、instanceof、以及为什么改原型会「污染」已有对象。",
    "mechanism": [
      "① 每个对象内部有 [[Prototype]] 内部属性，指向其构造函数的 prototype",
      "② 属性查找先看自有属性，没有则沿原型链上溯，直到 null",
      "③ prototype 有两个作用：① 给实例提供方法 ② constructor 指回构造函数",
      "④ class 只是语法糖，底层仍是「构造函数 + prototype 挂方法」",
      "⑤ class 支持 extends/super，super 是「以父类为 this 调用构造函数」的语法糖",
      "⑥ ⚠️ 运行时改 prototype.xxx 会**影响所有已有实例**——不是只影响新实例，这是最常见的坑"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "访问 obj.prop",
        "查自有属性",
        "沿[[Prototype]]上溯",
        "到 null 返回 undefined"
      ],
      "frames": [
        {
          "s": 0,
          "note": "实例访问属性"
        },
        {
          "s": 1,
          "note": "先查自己有没有"
        },
        {
          "s": 2,
          "note": "没有就沿原型链往上找"
        },
        {
          "s": 3,
          "note": "一直找不到才是 undefined"
        }
      ]
    },
    "interviewQ": [
      "class 是语法糖吗？",
      "为什么运行时改 prototype 会影响已有实例？",
      "instanceof 的原理？"
    ],
    "keywords": [
      "原型",
      "prototype",
      "原型链",
      "继承",
      "class",
      "constructor"
    ],
    "scene": [
      "给构造函数.prototype 加了个方法，所有之前 new 出来的实例都用上了——原型是共享的。",
      "面试被问「class 继承的底层是什么」，答 prototype + constructor 那套。"
    ],
    "tags": [
      "JavaScript",
      "原型",
      "继承"
    ],
    "related": [
      {
        "id": "fe-closure-scope",
        "kind": "compare",
        "note": "闭包记作用域、原型链记对象继承"
      },
      {
        "id": "fe-closure-scope-chain",
        "kind": "compare",
        "note": "相关：fe-closure-scope-chain"
      }
    ]
  },
  {
    "id": "fe-a11y",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "工程化",
      "可访问性"
    ],
    "title": "为什么 div 做的按钮读屏软件读不出来？",
    "oneLine": "可访问性依赖语义化标签和 ARIA 属性，用 div 模拟控件就丢掉了无障碍语义。",
    "analogy": "给盲人用的电梯按钮有盲文标牌，普通 div 按钮就是一块没标牌的板。",
    "why": "无障碍不是「特殊用户的事」，临时失去视力的工程师也要靠这些信息工作。",
    "mechanism": [
      "① 语义标签自带无障碍语义：<button> 自动有 role=button、可聚焦、有键盘事件",
      "② 用 div 模拟时必须补role/tabindex/@keydown，缺一不可",
      "③ alt 属性必填，装饰性图片应写 alt=\"\"（空 alt 表示装饰，不是遗漏）",
      "④ 表单控件必须配 label，用 for 关联或包裹",
      "⑤ 颜色不能是唯一区分手段（色盲用户看不出），要有文字或图标冗余",
      "⑥ 正面对比度至少 4.5:1，用 axe、Lighthouse 可自动检测"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "<div onclick>",
          "lines": [
            "读屏: 空白",
            "键盘: 无法聚焦"
          ],
          "note": "无语义"
        },
        {
          "title": "<button>",
          "lines": [
            "读屏: 按钮",
            "键盘: 可回车触发"
          ],
          "note": "自带语义"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "div 模拟按钮丢失无障碍语义"
        },
        {
          "s": 1,
          "note": "语义标签自带角色与交互能力"
        }
      ]
    },
    "interviewQ": [
      "为什么不能只用 div 模拟按钮？",
      "alt=\"\" 是什么意思？",
      "怎么检测无障碍问题？"
    ],
    "keywords": [
      "无障碍",
      "a11y",
      "ARIA",
      "语义化",
      "键盘导航"
    ],
    "scene": [
      "运营同学用 div 做了个上传按钮，键盘用户完全用不了。",
      "上线前跑 Lighthouse，无障碍分只有 72，主要是 alt 缺失。"
    ],
    "tags": [
      "无障碍",
      "工程化",
      "语义化"
    ],
    "related": [
      {
        "id": "fe-dom-attributes",
        "kind": "compare",
        "note": "属性写法影响语义与可访问性"
      }
    ]
  },
  {
    "id": "fe-dom-attributes",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "HTML 语义",
      "属性与语义化"
    ],
    "title": "defer / async 有什么区别？为什么要按需加载脚本？",
    "oneLine": "普通 script 阻塞解析，defer 等DOMContentLoaded 前按顺序执行，async 下载完立刻执行不保证顺序。",
    "analogy": "普通脚本是必须先看完的说明书；defer 是「边看边排队等」，async 是「谁先看完谁先执行」。",
    "why": "脚本加载方式没选对，会拖慢首屏或引发依赖未定义的报错。",
    "mechanism": [
      "① 普通 <script> 在head 中会阻塞 HTML 解析，直到下载并执行完才继续解析",
      "② defer 下载并行、DOM 解析完按文档顺序执行 → 保证顺序和 DOM 就绪",
      "③ async 下载并行、执行不保证顺序 → 只适合完全独立无依赖的脚本（如统计）",
      "④ 模块脚本 type=\"module\" 默认 defer",
      "⑤ 依赖顺序的两个脚本若都用 async，谁先执行完全不确定 → 会偶发 undefined",
      "⑥ 现代建议：统一放 body 末尾或用defer，减少阻塞与优先级 hack"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "d1",
          "label": "普通 script"
        },
        {
          "id": "d2",
          "label": "defer"
        },
        {
          "id": "d3",
          "label": "async"
        }
      ],
      "edges": [
        {
          "from": "d1",
          "to": "d2",
          "label": "想并行但保序"
        },
        {
          "from": "d1",
          "to": "d3",
          "label": "想立即执行"
        }
      ],
      "frames": [
        {
          "note": "普通脚本阻塞解析",
          "n": "d1"
        },
        {
          "note": "defer:并行下载 + 按序执行",
          "n": "d2"
        },
        {
          "note": "async:并行下载 + 执行不保序",
          "n": "d3"
        }
      ]
    },
    "interviewQ": [
      "defer 和 async 的区别？",
      "为什么 module 默认 defer？",
      "第三方脚本该用哪个？"
    ],
    "keywords": [
      "defer",
      "async",
      "脚本加载",
      "阻塞",
      "语义化"
    ],
    "scene": [
      "两个依赖顺序的脚本用了async，线上偶发报 b is not defined。",
      "第三方统计代码卡住首屏，改 async 后立刻见效。"
    ],
    "tags": [
      "HTML",
      "性能",
      "脚本加载"
    ],
    "related": [
      {
        "id": "fe-a11y",
        "kind": "compare",
        "note": "都是 HTML 层面对体验的优化"
      },
      {
        "id": "fe-code-split",
        "kind": "extends",
        "note": "加载时机问题的另一种解法"
      }
    ]
  },
  {
    "id": "fe-network-cache",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "工程化",
      "缓存与请求优化"
    ],
    "title": "强缓存和协商缓存有什么区别？",
    "oneLine": "强缓存直接用本地副本不发请求（Cache-Control），协商缓存发请求问「变了吗」（ETag/Last-Modified）。",
    "analogy": "强缓存是「直接看柜子里的副本」，协商缓存是「先问仓库有没有新版」。",
    "why": "缓存策略配错要么白屏（一直用旧版），要么白费流量（每次都全量下载）。",
    "mechanism": [
      "① 强缓存：Cache-Control max-age 有效期内直接用本地，不发请求（状态码 200 from cache 或304）",
      "② 协商缓存：缓存过期后带 If-None-Match/If-Modified-Since 发请求，服务端比对后返 304 或新内容",
      "③ max-age=0 且有 ETag → 走协商缓存；no-cache 表示必须协商但可缓存；no-store 完全不缓存",
      "④ ⚠️ 用户按 F5 刷新会绕过强缓存发协商请求，而「地址栏回车」才是走缓存——常被搞混",
      "⑤ 带 hash 的静态资源可设长缓存（immutable），HTML 入口设短缓存保证及时更新",
      "⑥ 内存缓存（memory cache）是优先级最高的一层，同一页面多个请求共享"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "h1",
          "label": "请求资源"
        },
        {
          "id": "h2",
          "label": "缓存是否有效"
        },
        {
          "id": "h3",
          "label": "强缓存命中"
        },
        {
          "id": "h4",
          "label": "协商比对"
        }
      ],
      "edges": [
        {
          "from": "h1",
          "to": "h2"
        },
        {
          "from": "h2",
          "to": "h3",
          "label": "max-age 未过"
        },
        {
          "from": "h2",
          "to": "h4",
          "label": "过期"
        }
      ],
      "frames": [
        {
          "note": "查缓存策略",
          "n": "h1"
        },
        {
          "note": "判断是否需要请求服务端",
          "n": "h2"
        },
        {
          "note": "有效则不发请求",
          "n": "h3"
        },
        {
          "note": "过期则带 ETag 问一次",
          "n": "h4"
        }
      ]
    },
    "interviewQ": [
      "强缓存和协商缓存的区别？",
      "no-cache 和 no-store 区别？",
      "静态资源缓存怎么配？"
    ],
    "keywords": [
      "缓存",
      "Cache-Control",
      "ETag",
      "协商缓存",
      "强缓存"
    ],
    "scene": [
      "上线新版本用户看到的是旧页面——HTML 被强缓存了，该给 HTML 短缓存。",
      "带 hash 的图片设了 no-cache，白白多发几次请求。"
    ],
    "tags": [
      "性能",
      "缓存",
      "HTTP"
    ],
    "related": [
      {
        "id": "cs-http-vs-https",
        "kind": "compare",
        "note": "缓存策略属于 HTTP 层能力"
      }
    ]
  },
  {
    "id": "fe-electron-vs-web",
    "domain": "前端",
    "category": "work",
    "subject": "fe",
    "topicPath": [
      "前端",
      "工程化",
      "桌面与移动端方案"
    ],
    "title": "Electron、Tauri、Flutter Web 为什么形态不同？",
    "oneLine": "Electron 带完整 Chromium 重但一致性好；Tauri 用系统 WebView 轻但行为有差异；Flutter 是自绘引擎。",
    "analogy": "Electron 像自带一整个浏览器搬家（可控但重）；Tauri 像借用系统浏览器（小但各家不同）。",
    "why": "跨端方案选型直接影响包体、内存和平台一致性。",
    "mechanism": [
      "① Electron = Chromium + Node，每个窗口一个渲染进程，内存占用高（一个空应用就上百 MB）",
      "② Tauri 用系统原生 WebView（WKWebView/WebView2），体积小内存省，但各平台渲染差异需适配",
      "③ Flutter Web 用 CanvasKit/DOM 两种渲染器自绘，不依赖浏览器控件，跨端一致但体积也大",
      "④ 移动端小程序限制多：无法用DOM、API 受限，渲染走 WebView 或自研引擎",
      "⑤ Tauri 的通信靠 invoke（前端调Rust），需要定义命令与序列化协议",
      "⑥ 选型看：是否需要访问本地文件/系统API、目标平台、包体敏感度、一致性要求"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "包体/内存",
          "lines": [
            "Electron 大",
            "Tauri 小"
          ],
          "note": "自带 vs 系统 WebView"
        },
        {
          "title": "一致性",
          "lines": [
            "Electron 强",
            "Tauri 有差异"
          ],
          "note": "Chromium 版本受系统限制"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "体积与一致性是最核心的权衡"
        },
        {
          "s": 1,
          "note": "Tauri 轻但需处理平台差异"
        }
      ]
    },
    "interviewQ": [
      "Electron 为什么这么占内存？",
      "Tauri 和 Electron 的核心差异？",
      "跨端方案怎么选？"
    ],
    "keywords": [
      "Electron",
      "Tauri",
      "跨端",
      "WebView",
      "小程序"
    ],
    "scene": [
      "Electron 应用内存占用 200MB 起，被用户吐槽，换 Tauri 后降到 80MB。",
      "Tauri 在 macOS 和 Windows 上按钮位置不一致，排查发现是两个系统的 WebView 差异。"
    ],
    "tags": [
      "跨端",
      "工程化",
      "Electron"
    ],
    "related": [
      {
        "id": "fe-webpack-vite",
        "kind": "compare",
        "note": "跨端方案里构建工具链选择也不同"
      }
    ]
  }
];
if (typeof module !== "undefined" && module.exports) {
  module.exports = CARDS_FE_2;
}