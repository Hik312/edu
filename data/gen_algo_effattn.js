// 严格 JSON 字面量：Node(vm) 与 Python(json) 都能直接读，请勿改回单引号
// 算法模块 · 高效注意力与状态空间（2026-10-09）
// ★ 查重：库里已有 5 张注意力卡（架构/自注意力/多头/位置编码/FlashAttention），
//   但「线性注意力 / 稀疏注意力 / 状态空间模型」全是空白 —— 这轮补齐。
//
// ★★ 全库贯穿的一条主线：标准自注意力是 O(n²)，
//   长文本（n很大）时「算得慢 + 显存爆」是根本瓶颈。
//   解法两条路：
//     路线A「让注意力变快」：稀疏（只算部分位置）/ 线性（核技巧去 O(n²)）/ 低秩
//     路线B「绕开注意力」：状态空间模型（Mamba）——把序列当状态递推，完全没有注意力
var CARDS_ALGO_EFFATTN = [
  {
    "id": "algo-attn-complexity",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": [
      "算法",
      "高效注意力",
      "O(n²) 瓶颈与解法地图"
    ],
    "title": "标准注意力为什么是 O(n²)？长文本到底卡在哪？",
    "oneLine": "注意力矩阵 n×n，序列翻倍计算量变四倍、显存也爆——这是长文本的根本瓶颈。",
    "analogy": "像让 n 个人两两对视：10 人 45 对，100 人就4950 对，人一多根本看不过来。",
    "why": "不理解 O(n²) 这个根，就理解不了后面所有高效注意力方案在解什么问题。",
    "mechanism": [
      "① 注意力矩阵大小 =序列长度²：n=8K 时是 6400万个元素，直接爆显存",
      "② 计算量：QKᵀ 是 O(n²·d)，序列翻倍 → 计算量 4 倍（不是 2 倍）",
      "③ 三个瓶颈：① 显存（O(n²) 中间矩阵）② 计算（O(n²d)）③ 长程信息传递（每层只能跨 1 跳）",
      "④ 解法分两路：路线A「让注意力更快」（稀疏/线性/低秩，保留注意力机制）",
      "⑤ 路线B「绕开注意力」（状态空间模型/Mamba，用递推代替两两计算）",
      "⑥ ⚠️ 注意 FlashAttention 属于「另一条路」：它不改复杂度，而是把 O(n²) 做精确（IO 优化）",
      "⑦ 上下文长度 8K→128K 不是线性的工程问题，是算法问题"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "n=8K",
          "lines": [
            "注意力矩阵 6400万元素",
            "直接爆显存"
          ],
          "note": "O(n²) 直观体现"
        },
        {
          "title": "n=128K",
          "lines": [
            "矩阵 163亿元素",
            "完全不可行"
          ],
          "note": "4 倍关系"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "注意力矩阵是 n×n 的"
        },
        {
          "s": 1,
          "note": "长文本时显存和计算都爆"
        }
      ]
    },
    "interviewQ": [
      "为什么自注意力是 O(n²)？",
      "长文本处理有哪些解法路线？",
      "FlashAttention 降低了复杂度吗？"
    ],
    "keywords": [
      "O(n²)",
      "长文本",
      "复杂度",
      "瓶颈",
      "上下文长度"
    ],
    "scene": [
      "模型上下文标称 128K，实际推理慢到不可用——瓶颈在 O(n²)。",
      "面试被问「长上下文怎么做」，先说清O(n²) 瓶颈再谈方案。"
    ],
    "tags": [
      "注意力",
      "复杂度",
      "长文本"
    ],
    "related": [
      {
        "id": "algo-flash-attention",
        "kind": "compare",
        "note": "Flash 是精确 IO 优化，不改复杂度"
      },
      {
        "id": "algo-sparse-attention",
        "kind": "extends",
        "note": "稀疏注意力：路线A 的代表"
      },
      {
        "id": "algo-linear-attention",
        "kind": "extends",
        "note": "线性注意力：路线A 的另一分支"
      },
      {
        "id": "algo-mamba-ssm",
        "kind": "extends",
        "note": "Mamba：路线B，绕开注意力"
      }
    ]
  },
  {
    "id": "algo-sparse-attention",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": [
      "算法",
      "高效注意力",
      "稀疏注意力"
    ],
    "title": "稀疏注意力怎么只算一部分？局部窗口和全局 token 怎么选？",
    "oneLine": "放弃「每个 token 看所有 token」，改成只看附近窗口 + 少数全局关键 token，把 O(n²) 降成 O(n·w)。",
    "analogy": "像开会：不让所有人听所有人发言，只让每人听最近 3 位发言 + 主持人总结全局。",
    "why": "它保住了「注意力」这个机制（比换架构更安全），但把长程依赖交给稀疏结构承载。",
    "mechanism": [
      "① 核心：只计算部分注意力连接，把 O(n²) 的全连接图稀疏化",
      "② 局部窗口（sliding window）：每个 token 只看前后 w 个 → O(n·w)，w 常取 256~1024",
      "③ 全局 token：留少数（如每段开头/特殊 token）能被所有 token 看，打通长程信息",
      "④ 组合起来 = 「局部窗口 + 全局接收」，长程靠全局、局部靠窗口",
      "⑤ Longformer：滑窗 + 全局 token；BigBird：再加随机注意力（理论上有近似保证）",
      "⑥ ⚠️ 稀疏模式是**人为设计的归纳偏置**，不是学出来的——选错窗口会丢关键信息",
      "⑦ 代价：信息传递要靠多层堆叠（局部感受野逐层扩大），不如全连接直接"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "全注意力",
          "lines": [
            "n×n 全连接",
            "O(n²)"
          ],
          "note": "标准"
        },
        {
          "title": "稀疏注意力",
          "lines": [
            "窗口内 + 全局token",
            "O(n·w)"
          ],
          "note": "局部+全局"
        }
      ],
      "frames": [
        {
          "s": 0,
          "note": "全连接成本随n平方增长"
        },
        {
          "s": 1,
          "note": "滑窗保局部，全局 token 保长程"
        }
      ]
    },
    "interviewQ": [
      "稀疏注意力怎么做？为什么要留全局 token？",
      "Longformer 和 BigBird 有什么区别？",
      "稀疏注意力的代价是什么？"
    ],
    "keywords": [
      "稀疏注意力",
      "局部窗口",
      "全局token",
      "Longformer",
      "BigBird",
      "O(nw)"
    ],
    "scene": [
      "文档摘要任务要读超长文，滑窗+全局 token 让它能处理 4 万 token。",
      "面试被问「稀疏注意力和全注意力区别」，答连接数从 n² 降到 n·w。"
    ],
    "tags": [
      "注意力",
      "稀疏",
      "长文本"
    ],
    "related": [
      {
        "id": "algo-attn-complexity",
        "kind": "extends",
        "note": "稀疏是解 O(n²) 的路线A"
      },
      {
        "id": "algo-linear-attention",
        "kind": "compare",
        "note": "稀疏降连接数，线性降计算量"
      },
      {
        "id": "algo-mamba-ssm",
        "kind": "compare",
        "note": "另一条路线：干脆不用注意力"
      }
    ]
  },
  {
    "id": "algo-linear-attention",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": [
      "算法",
      "高效注意力",
      "线性注意力"
    ],
    "title": "线性注意力怎么把 O(n²) 降到 O(n)？核技巧做了什么？",
    "oneLine": "利用矩阵乘法的结合律先算 KᵀV（O(n·d²)）再乘 Q，得到 O(n·d²)，无需真的算 n×n 矩阵。",
    "analogy": "标准做法是「两两打分再汇总」；线性做法是「先把所有值汇成向量，再按相关度加权取用」。",
    "why": "它把复杂度从序列长度 n 的平方降到线性，是长上下文的高效方案之一。",
    "mechanism": [
      "① 标准注意力：Attention = softmax(Q·Kᵀ)·V，中间的 n×n 矩阵是瓶颈",
      "② 关键洞察：先算 KᵀV（d×n · n×d = d×d 小矩阵），不必显式算出 n×n",
      "③ 用矩阵乘法结合律重排：Attn(Q,K,V) = Q·(KᵀV) ·归一化 —— 复杂度 O(n·d²)",
      "④ ⚠️ 问题：softmax 非线性，不能直接交换顺序——需要先用「特征映射」φ 近似 exp(q·k)",
      "⑤ 核技巧：把 softmax(q·k) 近似成 φ(q)·φ(k) 的内积，引入可计算的特征映射",
      "⑥ Performer：用随机特征做 φ 的无偏近似，把 O(n²) 降到 O(n·d)（仍是近似）",
      "⑦ Linformer：假设 K/V 低秩，用投影降到固定长度 —— 也牺牲表达力换速度"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "φ映射(Q/K)",
        "KᵀV先聚合",
        "Q加权",
        "归一化"
      ],
      "frames": [
        {
          "s": 0,
          "note": "特征映射绕开 softmax"
        },
        {
          "s": 1,
          "note": "先算 KᵀV 得到 d×d"
        },
        {
          "s": 2,
          "note": "O(n·d²) 替代 O(n²·d)"
        }
      ]
    },
    "interviewQ": [
      "线性注意力为什么能降到 O(n)？",
      "为什么需要核技巧/特征映射？",
      "Performer 和 Linformer 各是什么思路？"
    ],
    "keywords": [
      "线性注意力",
      "核技巧",
      "Performer",
      "Linformer",
      "结合律",
      "特征映射"
    ],
    "scene": [
      "把长文档模型的注意力从 O(n²) 改成线性，推理成本降一个数量级。",
      "面试被问「怎么把注意力变快」，答换顺序先算 KᵀV + 核技巧近似 softmax。"
    ],
    "tags": [
      "注意力",
      "线性",
      "核方法",
      "近似"
    ],
    "related": [
      {
        "id": "algo-attn-complexity",
        "kind": "extends",
        "note": "线性是解 O(n²) 的路线A 分支"
      },
      {
        "id": "algo-sparse-attention",
        "kind": "compare",
        "note": "稀疏降连接数，线性降单次计算量"
      },
      {
        "id": "algo-flash-attention",
        "kind": "compare",
        "note": "Flash 精确；线性注意力多是近似"
      }
    ]
  },
  {
    "id": "algo-mamba-ssm",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": [
      "算法",
      "高效注意力",
      "状态空间模型与Mamba"
    ],
    "title": "Mamba 为什么说「注意力不是一切」？SSM 怎么替代注意力？",
    "oneLine": "用状态空间递推把序列压进固定大小的隐藏状态，复杂度线性且能无限扩展上下文——彻底不用注意力。",
    "analogy": "注意力像每来新信息就重读整本书；SSM 像边读边把要点记进一个小本，记住就忘旧。",
    "why": "它是 2024 年后最热的架构路线，挑战「Transformer 一统天下」的共识。",
    "mechanism": [
      "① 状态空间模型（SSM）：把序列看成递推系统 h_t = A·h_{t-1} + B·x_t",
      "② 关键在「状态维度是固定的」——不随序列增长，长上下文不会爆",
      "③ 传统 SSM 因需逐步递推无法并行；Mamba 用「选择性扫描」硬件友好并行化",
      "④ 选择性（selective）：让 A、B、Δ 依赖当前输入 → 每个 token 有不同的记忆策略",
      "⑤ 复杂度O(n) 且推理时每步只维护固定大小状态（像 RNN 一样快）",
      "⑥ ⚠️ 缺点：自回归逐token 生成，无法像 Transformer 那样一次性并行算完整个序列",
      "⑦ 混合架构（Hattention/Jamba）在用：多数层 SSM + 少数层注意力"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "mb1",
          "label": "输入 x_t"
        },
        {
          "id": "mb2",
          "label": "选择性参数(Δ,A,B)"
        },
        {
          "id": "mb3",
          "label": "更新状态 h_t"
        },
        {
          "id": "mb4",
          "label": "输出 y_t"
        }
      ],
      "edges": [
        {
          "from": "mb1",
          "to": "mb2"
        },
        {
          "from": "mb2",
          "to": "mb3",
          "label": "依赖当前输入"
        },
        {
          "from": "mb3",
          "to": "mb3",
          "label": "递推"
        },
        {
          "from": "mb3",
          "to": "mb4"
        }
      ],
      "frames": [
        {
          "note": "状态维度固定，不随n 增长",
          "n": "mb1"
        },
        {
          "note": "选择性：参数依赖当前 token",
          "n": "mb2"
        },
        {
          "note": "O(n) 复杂度，线性",
          "n": "mb3"
        }
      ]
    },
    "interviewQ": [
      "Mamba 为什么能处理长上下文？",
      "SSM 和 RNN 的区别？",
      "Mamba 有什么局限？"
    ],
    "keywords": [
      "Mamba",
      "状态空间模型",
      "SSM",
      "选择性扫描",
      "线性复杂度",
      "替代Transformer"
    ],
    "scene": [
      "要百万 token 上下文，注意力方案太贵，Mamba 类架构给了另一条路。",
      "面试被问「Transformer 之后是什么」，答状态空间模型/Mamba 是热门方向。"
    ],
    "tags": [
      "状态空间",
      "Mamba",
      "架构",
      "长文本"
    ],
    "related": [
      {
        "id": "algo-attn-complexity",
        "kind": "extends",
        "note": "Mamba 是解 O(n²) 的路线B"
      },
      {
        "id": "algo-transformer-arch",
        "kind": "compare",
        "note": "挑战 Transformer 一统地位的架构"
      },
      {
        "id": "algo-rwkv",
        "kind": "extends",
        "note": "RWKV 是另一条类似思路"
      }
    ]
  },
  {
    "id": "algo-rwkv",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": [
      "算法",
      "高效注意力",
      "线性注意力的其他路线"
    ],
    "title": "RWKV 和线性注意力有什么关系？ReLU 特征映射是什么意思？",
    "oneLine": "RWKV 用带ReLU 的轻量 RNN 加衰减记忆，能像 Transformer 一样并行训练、像 RNN 一样高效推理。",
    "analogy": "线性注意力用「核技巧近似相似度」，RWKV 用「可被小本记住」的记忆衰减，两者都在省算力。",
    "why": "它展示了「并行训练 + 高效推理」这个目标不只有一条实现路径。",
    "mechanism": [
      "① RWKV 重新表述为「带ReLU 的线性 RNN」，训练时可用线性注意力式的并行",
      "② 核心技巧：ReLU(x)·ReLU(y) 近似 exp(q·k)，作为线性注意力的因果特征映射",
      "③ 时间混合（token mixing）：用「过去信息的衰减」代替注意力的全局查询",
      "④ 通道混合（channel mixing）：类似 Transformer 的 FFN，做特征变换",
      "⑤ 优势：训练可并行、推理 O(1) 每步、context 无上限",
      "⑥ 对比 Mamba：两者都是线性复杂度，RWKV 更轻、Mamba 表达力更强",
      "⑦ 共同点：都在挑战「Transformer 是唯一道路」"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "token混合(衰减)",
        "channel混合",
        "残差累加"
      ],
      "frames": [
        {
          "s": 0,
          "note": "用衰减记忆替代注意力查询"
        },
        {
          "s": 1,
          "note": "训练可并行、推理轻量"
        }
      ]
    },
    "interviewQ": [
      "RWKV 和 Mamba 有什么区别？",
      "ReLU 特征映射用来干什么？",
      "为什么说它们都是线性复杂度？"
    ],
    "keywords": [
      "RWKV",
      "线性注意力",
      "ReLU映射",
      "状态空间",
      "轻量架构"
    ],
    "scene": [
      "边缘设备上跑语言模型，要推理快且训练可并行，RWKV 是个选项。",
      "面试被问「注意力不是唯一出路」，举 RWKV/Mamba 两条路线。"
    ],
    "tags": [
      "线性注意力",
      "RWKV",
      "架构",
      "轻量"
    ],
    "related": [
      {
        "id": "algo-linear-attention",
        "kind": "extends",
        "note": "ReLU 特征映射连接两者"
      },
      {
        "id": "algo-mamba-ssm",
        "kind": "compare",
        "note": "同为线性架构的另一种选择"
      }
    ]
  },
  {
    "id": "algo-attention-kv-cache",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": [
      "算法",
      "高效注意力",
      "KV Cache 与推理优化"
    ],
    "title": "KV Cache 为什么能让生成快一个数量级？它占多少显存？",
    "oneLine": "生成时缓存已算的 K/V 避免重算，但它是显存大户——大模型常被KV Cache 卡住而非算力。",
    "analogy": "像每次接着写文章要重新读一遍全部参考资料；缓存后只读新的一段，速度快但占桌面积。",
    "why": "它是理解 LLM 推理成本结构的关键——很多「算力不够」其实是「显存不够」。",
    "mechanism": [
      "① 自回归生成逐 token 进行：没缓存时每步要把整个已有序列的 K/V 全重算",
      "② KV Cache：把历史 token 的 K/V 存起来，每步只算新 token 的 K/V 再拼接",
      "③ 复杂度从 O(n²) 降到 O(n)——但**只是不重算，缓存本身仍在长**",
      "④ ⚠️ 显存占用 ∝ 层数 × 头数 × 维度 × 序列长度 × 2(K和V) × batch——长上下文时爆炸",
      "⑤ 量化 KV Cache（int8）能省一半以上显存，代价是精度略降",
      "⑥ PagedAttention（vLLM）：像操作系统的分页管理，消除 KV Cache 碎片，提高利用率",
      "⑦ MQA/GQA：多query/分组共享 K/V 头，直接减少 KV Cache 体积"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "缓存历史K/V",
        "只算新token",
        "拼接",
        "喂给模型"
      ],
      "frames": [
        {
          "s": 0,
          "note": "历史 K/V 不重算"
        },
        {
          "s": 1,
          "note": "每步只算新增部分"
        },
        {
          "s": 2,
          "note": "生成速度提升数量级"
        }
      ]
    },
    "interviewQ": [
      "KV Cache 是什么？为什么能加速？",
      "KV Cache 占多少显存？怎么优化？",
      "PagedAttention 和 MQA 分别解决什么？"
    ],
    "keywords": [
      "KV Cache",
      "推理优化",
      "显存",
      "PagedAttention",
      "MQA",
      "GQA",
      "量化"
    ],
    "scene": [
      "部署大模型，batch 一大就 OOM——不是算力不够是 KV Cache 占满显存。",
      "面试被问「怎么提升推理吞吐」，答 KV Cache 管理 + 量化 + MQA。"
    ],
    "tags": [
      "推理",
      "显存",
      "优化",
      "KV"
    ],
    "related": [
      {
        "id": "algo-flash-attention",
        "kind": "extends",
        "note": "FlashAttention 也常与 KV Cache 配合优化"
      },
      {
        "id": "algo-mamba-ssm",
        "kind": "compare",
        "note": "Mamba 的固定状态也避免了 KV Cache 问题"
      }
    ]
  }
];
if (typeof module !== "undefined" && module.exports) {
  module.exports = CARDS_ALGO_EFFATTN;
}