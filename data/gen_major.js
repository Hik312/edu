// 自动生成于 2026-09-29 by scripts/gen_cards.py（大纲批量造卡）。
// 机器产出，人工复核后可保留/删改；此文件由 git 管理，属「内容」不是「状态」。
var CARDS_MAJOR = [
  {
    "id": "major-data-struct-complexity",
    "domain": "专业课",
    "category": "kaoyan",
    "subject": "major",
    "topicPath": [
      "专业课",
      "数据结构复杂度分析"
    ],
    "title": "如何判断算法效率高低？",
    "oneLine": "数据结构复杂度分析是评估算法效率的核心方法。",
    "analogy": "做菜时判断哪种方法更快更省材料。",
    "why": "帮助选择更高效的算法，提升程序运行速度。",
    "mechanism": [
      "① 复杂度分析定义算法运行时间的上界。",
      "② 通过时间复杂度评估算法在最坏情况下的性能。",
      "③ 通过空间复杂度评估算法占用的内存资源。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "输入",
        "分析",
        "输出"
      ],
      "frames": [
        {
          "s": 0,
          "note": "输入算法流程图或伪代码"
        }
      ]
    },
    "interviewQ": [
      "如何区分时间复杂度和空间复杂度？",
      "如何计算递归算法的时间复杂度？"
    ],
    "keywords": [
      "时间复杂度",
      "空间复杂度",
      "算法效率",
      "大O表示法"
    ],
    "scene": [
      "在面试中被要求分析排序算法的时间复杂度。",
      "在实际项目中选择更高效的算法优化性能。"
    ],
    "tags": [
      "算法分析",
      "时间复杂度",
      "面试高频"
    ],
    "related": []
  },
  {
    "id": "major-dp-state-design",
    "domain": "专业课",
    "category": "kaoyan",
    "subject": "major",
    "topicPath": [
      "专业课",
      "动态规划状态设计"
    ],
    "title": "如何设计动态规划的状态？",
    "oneLine": "动态规划状态设计是解题的关键步骤。",
    "analogy": "规划旅行路线时选择最优的起点和终点。",
    "why": "状态设计决定了问题是否能被拆解为子问题。",
    "mechanism": [
      "① 定义状态变量表示问题的当前情况。",
      "② 确定状态转移方程表示如何从子问题推导当前问题。",
      "③ 初始化边界条件确保计算的正确性。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "定义状态",
        "状态转移",
        "初始化"
      ],
      "frames": [
        {
          "s": 0,
          "note": "定义状态变量和状态转移方程"
        }
      ]
    },
    "interviewQ": [
      "如何判断一个问题是否适合用动态规划解决？",
      "如何避免重复计算？"
    ],
    "keywords": [
      "动态规划",
      "状态转移方程",
      "状态变量",
      "初始化"
    ],
    "scene": [
      "在面试中被问如何用动态规划解决背包问题。",
      "在实际项目中使用动态规划优化资源分配。"
    ],
    "tags": [
      "算法设计",
      "动态规划",
      "面试高频"
    ],
    "related": []
  },
  {
    "id": "major-graph-shortest-path",
    "domain": "专业课",
    "category": "kaoyan",
    "subject": "major",
    "topicPath": [
      "专业课",
      "图论最短路算法"
    ],
    "title": "如何找到图中的最短路径？",
    "oneLine": "图论最短路算法是解决路径优化的核心方法。",
    "analogy": "在城市中寻找最快捷的交通路线。",
    "why": "帮助找到最优路径，提升网络和物流的效率。",
    "mechanism": [
      "① 使用Dijkstra算法优先处理距离最短的节点。",
      "② 使用Bellman-Ford算法处理负权边的情况。",
      "③ 使用Floyd-Warshall算法处理所有节点对的最短路径。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "初始化",
        "松弛操作",
        "更新最短路径"
      ],
      "frames": [
        {
          "s": 0,
          "note": "使用松弛操作更新最短路径"
        }
      ]
    },
    "interviewQ": [
      "如何选择适合的最短路算法？",
      "如何处理负权边？"
    ],
    "keywords": [
      "最短路算法",
      "Dijkstra",
      "Bellman-Ford",
      "Floyd-Warshall"
    ],
    "scene": [
      "在面试中被问如何使用Dijkstra算法解决实际问题。",
      "在实际项目中使用最短路算法优化物流路径。"
    ],
    "tags": [
      "图论",
      "最短路算法",
      "面试高频"
    ],
    "related": []
  },
  {
    "id": "major-datastructurecomplexity",
    "domain": "专业课",
    "category": "kaoyan",
    "subject": "major",
    "topicPath": [
      "专业课",
      "数据结构复杂度分析"
    ],
    "title": "如何判断算法的效率高低？",
    "oneLine": "复杂度分析用于评估算法运行时间与空间需求。",
    "analogy": "计算做菜时间，看哪道菜更快完成。",
    "why": "帮助选择更高效的算法，节省资源。",
    "mechanism": [
      "① 计算操作次数，如循环次数",
      "② 分析输入规模对操作次数的影响",
      "③ 用大O表示法描述最坏情况"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "输入规模",
        "操作次数",
        "大O表示法"
      ],
      "frames": [
        {
          "s": 0,
          "note": "确定输入规模"
        },
        {
          "s": 1,
          "note": "计算操作次数"
        },
        {
          "s": 2,
          "note": "用大O表示法描述"
        }
      ]
    },
    "interviewQ": [
      "如何区分时间复杂度和空间复杂度？",
      "大O表示法是否考虑常数项？"
    ],
    "keywords": [
      "时间复杂度",
      "空间复杂度",
      "大O表示法"
    ],
    "scene": [
      "在面试中需要快速估算算法效率",
      "实际项目中选择最优数据结构"
    ],
    "tags": [
      "算法分析",
      "复杂度评估"
    ],
    "related": []
  },
  {
    "id": "major-dpstate",
    "domain": "专业课",
    "category": "kaoyan",
    "subject": "major",
    "topicPath": [
      "专业课",
      "动态规划状态设计"
    ],
    "title": "如何设计动态规划的状态？",
    "oneLine": "状态设计是动态规划的核心，决定解题思路。",
    "analogy": "规划旅行路线时，每一步的选择影响最终目的地。",
    "why": "状态设计能简化问题，避免重复计算。",
    "mechanism": [
      "① 确定状态变量，如当前位置",
      "② 定义状态转移方程，如如何到达当前状态",
      "③ 考虑边界条件，如初始状态"
    ],
    "interviewQ": [
      "如何判断一个问题是动态规划的？",
      "状态设计是否需要考虑所有可能情况？"
    ],
    "keywords": [
      "动态规划",
      "状态转移方程",
      "边界条件"
    ],
    "scene": [
      "在面试中设计复杂问题的解决方案",
      "实际项目中优化重复计算问题"
    ],
    "tags": [
      "算法设计",
      "动态规划"
    ],
    "related": []
  },
  {
    "id": "major-shortestpath",
    "domain": "专业课",
    "category": "kaoyan",
    "subject": "major",
    "topicPath": [
      "专业课",
      "图论最短路算法"
    ],
    "title": "如何找到图中两点的最短路径？",
    "oneLine": "最短路算法用于计算图中节点间的最短距离。",
    "analogy": "寻找城市间的最优交通路线。",
    "why": "帮助优化物流、网络传输等实际问题。",
    "mechanism": [
      "① 初始化距离数组，设置起点为0",
      "② 使用优先队列选择当前最短路径节点",
      "③ 更新相邻节点的距离并加入队列"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "初始化距离数组",
        "优先队列选择节点",
        "更新相邻节点距离"
      ],
      "frames": [
        {
          "s": 0,
          "note": "设置起点距离为0"
        },
        {
          "s": 1,
          "note": "选择当前最短路径节点"
        },
        {
          "s": 2,
          "note": "更新相邻节点距离"
        }
      ]
    },
    "interviewQ": [
      "Dijkstra和Bellman-Ford算法的区别是什么？",
      "如何处理负权边？"
    ],
    "keywords": [
      "最短路算法",
      "Dijkstra",
      "Bellman-Ford"
    ],
    "scene": [
      "在面试中比较不同算法的适用场景",
      "实际项目中优化路径规划问题"
    ],
    "tags": [
      "图论算法",
      "最短路径"
    ],
    "related": []
  }
];

if (typeof module !== "undefined" && module.exports) { module.exports = CARDS_MAJOR; }
