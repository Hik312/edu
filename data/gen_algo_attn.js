// 严格 JSON 字面量：Node(vm) 与 Python(json) 都能直接读，请勿改回单引号
// 算法模块 · 模型与注意力（2026-10-09）
// ★ Transformer 已有 3 张（自注意力/位置编码）散在 ai 科目，
//   这里补「整体架构 + 注意力计算细节 + 现代LLM 的注意力变体」，与已有卡互补不重复。
var CARDS_ALGO_ATTN = [
  {
    "id": "algo-transformer-arch",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": ["算法", "注意力机制", "Transformer 整体架构"],
    "title": "Transformer 的整体架构是什么？为什么它取代了 RNN？",
    "oneLine": "编码器-解码器全用自注意力+前馈网络堆叠，抛弃循环，靠位置编码注入顺序，训练可完全并行。",
    "analogy": "RNN 像「一个人从左读到右逐字读」（串行，慢）；Transformer 像「一眼看全句，每个词同时看其他词」（并行）。",
    "why": "它是 BERT/GPT 的基础，理解它才明白自注意力、位置编码、多头这些设计为什么存在。",
    "mechanism": [
      "① 核心层：Multi-Head Self-Attention（看上下文）+ Feed-Forward（逐位置变换）",
      "② 位置：因没有循环需要知道顺序，靠位置编码注入「第几个词」的信息",
      "③ 编码器层：注意力 + FF + LayerNorm + 残差连接",
      "④ 解码器层：多了 Masked Attention（不看未来词）",
      "⑤ ⚠️ 关键优势：训练时一层内所有位置**完全并行**，不像 RNN 要等前一步算完",
      "⑥ ⚠️ 代价：自注意力复杂度 O(n²)（序列平方），长文本处理贵（这就是 FlashAttention 等优化的动机）",
      "⑦ 现代 LLM（如 GPT）只用**解码器**（去掉编码器），因果掩码保证只生成、不偷看"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["输入Embedding", "+位置编码", "多头自注意力", "FeedForward", "输出"],
      "frames": [
        { "s": 0, "note": "词向量 + 位置编码" },
        { "s": 1, "note": "注意力层看上下文" },
        { "s": 2, "note": "FFN 逐位置非线性变换" },
        { "s": 3, "note": "残差 + LayerNorm 贯穿" }
      ]
    },
    "interviewQ": [
      "Transformer 为什么比 RNN 快？",
      "自注意力的复杂度是多少？长文本怎么办？",
      "现在的大模型为什么只用解码器？"
    ],
    "keywords": ["Transformer", "架构", "自注意力", "位置编码", "解码器", "并行"],
    "scene": [
      "面试从 RNN 一路问到 Transformer，核心追问就是「为什么能并行」和「长文本怎么搞」。",
      "读 LLM 论文时发现都基于 Transformer decoder，理解架构才看得懂后续变体。"
    ],
    "tags": ["Transformer", "深度学习", "架构"],
    "related": [
      { "id": "algo-self-attention", "kind": "extends", "note": "自注意力是架构的核心计算" },
      { "id": "algo-multi-head", "kind": "extends", "note": "多头是架构里的关键组件" },
      { "id": "algo-position-encoding", "kind": "extends", "note": "位置编码解决无序问题" }
    ]
  },
  {
    "id": "algo-self-attention",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": ["算法", "注意力机制", "自注意力计算"],
    "title": "自注意力 Q、K、V 是怎么算的？为什么除以 √d_k？",
    "oneLine": "每个词用Q 和所有词的 K 算相似度当权重，对所有 V 加权求和；除以 √d_k 是防softmax 溢出。",
    "analogy": "像查档案：「我（Q）」去和所有档案的「索引（K）」比一下找相关，再拿相关档案的「内容（V）」汇总。",
    "why": "它是 Transformer 的核心，也是理解「注意力权重可视化」「幻觉」等概念的基础。",
    "mechanism": [
      "① 输入 X 乘三个可学习矩阵 W_Q/W_K/W_V 得到 Q、K、V",
      "② 注意力权重 = softmax(Q·Kᵀ / √d_k)——Q 和 K 的点积衡量「相关性」",
      "③ ⚠️ 为什么要除 √d_k：d_k 维度大时点积方差会随维度放大，softmax 前值过大进入饱和区，梯度趋近 0 训练不动",
      "④ 输出 = 权重矩阵 × V（按注意力权重对所有 V 加权求和）",
      "⑤ 因果掩码（decoder）：把「未来」位置的权重置 -∞，保证只生成不看答案",
      "⑥ 权重矩阵的每一行之和为 1（softmax），表示「这个词对各词的关注分布」"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["算QKV", "QK^T相似度", "/√d_k+softmax", "加权V"],
      "frames": [
        { "s": 0, "note": "X 分别投影出 Q、K、V" },
        { "s": 1, "note": "Q·Kᵀ 衡量词间相关性" },
        { "s": 2, "note": "除 √d_k 防止 softmax 饱和" },
        { "s": 3, "note": "按权重汇总 V" }
      ]
    },
    "interviewQ": [
      "为什么注意力要除以 √d_k？",
      "Q、K、V 各自是什么？",
      "因果掩码是怎么加的？"
    ],
    "keywords": ["自注意力", "QKV", "注意力权重", "softmax", "根号dk", "因果掩码"],
    "scene": [
      "面试高频题：解释 attention 公式，尤其被追问「为什么除 √d_k」。",
      "调试 LLM 时看注意力权重图，发现模型没关注关键 token——排查幻觉的线索之一。"
    ],
    "tags": ["注意力", "Transformer", "深度学习"],
    "related": [
      { "id": "algo-transformer-arch", "kind": "extends", "note": "自注意力是架构核心组件" },
      { "id": "algo-multi-head", "kind": "extends", "note": "多头 = 多个自注意力并行" }
    ]
  },
  {
    "id": "algo-multi-head",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": ["算法", "注意力机制", "多头注意力"],
    "title": "多头注意力为什么比单头好？它学到了什么？",
    "oneLine": "把模型拆成多组注意力并行学不同子空间，再拼接——不同头关注不同关系（指代、语法、语义）。",
    "analogy": "像一个会议多位专家同时听：有人关注语法搭配，有人关注指代关系，有人关注语气，各自汇报。",
    "why": "它让模型能同时捕捉多种关系，是提升效果的关键设计之一。",
    "mechanism": [
      "① 切成 h 份，每份用独立的 Q/K/V 投影，在各自的子空间做自注意力",
      "② h 份输出拼接后再过一个线性层 W_O 融合",
      "③ 不同头能学到不同关系：一个盯句法、一个盯指代、一个盯全局语义",
      "④ 总参数量可控：每个头的维度是 d_model/h，所以拼接后维度不变",
      "⑤ ⚠️ 不是「头越多越好」：头数多而每头维度太小，反而每个头学不到完整信息",
      "⑥ 可视化不同头的注意力矩阵，能看出它们分工不同"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        { "title": "头1", "lines": ["关注：语法搭配"], "note": "子空间A" },
        { "title": "头2", "lines": ["关注：指代关系"], "note": "子空间B" },
        { "title": "…", "lines": ["关注：语气/主题"], "note": "各司其职" }
      ],
      "frames": [
        { "s": 0, "note": "多头各学不同子空间关系" }
      ]
    },
    "interviewQ": [
      "多头注意力解决了单头的什么问题？",
      "多头后为什么要拼接？",
      "头数是不是越多越好？"
    ],
    "keywords": ["多头注意力", "Multi-Head", "自注意力", "子空间", "注意力头"],
    "scene": [
      "可视化注意力权重，发现不同头分工明显——有的盯主谓、有的盯代词指代。",
      "面试被问「多头比单头好在哪」，答能并行学多种关系子空间。"
    ],
    "tags": ["注意力", "Transformer", "深度学习"],
    "related": [
      { "id": "algo-self-attention", "kind": "extends", "note": "多头是单自注意力的并行化" }
    ]
  },
  {
    "id": "algo-position-encoding",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": ["算法", "注意力机制", "位置编码"],
    "title": "Transformer 没有循环，为什么需要位置编码？",
    "oneLine": "自注意力本身不知道词序，必须显式注入「位置」信息，否则「狗咬人」和「人咬狗」无区别。",
    "analogy": "所有词都站在同一个会议室里聊天，谁先谁后全靠你贴座位号——位置编码就是那个座位号。",
    "why": "不理解这点就看不懂 Transformer 为什么需要这个组件、以及RoPE 等变体在改什么。",
    "mechanism": [
      "① 纯注意力对输入是**置换等变**的——把词打乱，输出只是跟着换位置，不知道谁在前",
      "② 位置编码给每个位置注入一个可区分的向量，加到词Embedding 上",
      "③ 正弦编码（原论文）：不同频率 sin/cos 组合，可外推到训练没见过的长度",
      "④ 可学习编码（BERT）：直接学位置向量，更强但不能外推",
      "⑤ RoPE/ALiBi（现代 LLM）：把位置信息编进 Q/K 的旋转而非加到输入，更适合长上下文",
      "⑥ ⚠️ 绝对 vs 相对：正弦/可学习是绝对位置，RoPE 偏相对——影响长度外推能力"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        { "title": "无位置编码", "lines": ["狗 咬 人", "人 咬 狗", "注意力结果相同"], "note": "不知道顺序" },
        { "title": "有位置编码", "lines": ["第0位 狗", "第1位 咬", "第2位 人"], "note": "顺序可辨" }
      ],
      "frames": [
        { "s": 0, "note": "注意力不自带顺序信息" },
        { "s": 1, "note": "位置编码注入顺序" }
      ]
    },
    "interviewQ": [
      "为什么 Transformer 需要位置编码？",
      "正弦编码为什么能外推？",
      "RoPE 相比正弦编码好在哪？"
    ],
    "keywords": ["位置编码", "Position", "RoPE", "正弦编码", "置换等变", "长上下文"],
    "scene": [
      "让LLM 判断句子语序，完全不靠谱——因为它没拿到位置信息或位置编码有问题。",
      "面试被问「Transformer 为什么要有位置编码」，答置换等变、需显式注入顺序。"
    ],
    "tags": ["注意力", "Transformer", "位置编码"],
    "related": [
      { "id": "algo-transformer-arch", "kind": "extends", "note": "位置编码是架构的关键组件" },
      { "id": "algo-flash-attention", "kind": "compare", "note": "注意力优化，与位置编码共同支撑长文本" }
    ]
  },
  {
    "id": "algo-flash-attention",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": ["算法", "注意力机制", "FlashAttention 与高效注意力"],
    "title": "FlashAttention 为什么比朴素注意力快？是近似吗？",
    "oneLine": "分块计算注意力、避免把大矩阵写回显存（HBM），是**精确**算法不是近似——快在 IO 不是算力。",
    "analogy": "不是抄近路算得更少，而是不用把整张中间表搬来搬去，就地算完再汇总。",
    "why": "长文本推理慢的元凶就是标准注意力，理解它才明白各家推理引擎为什么都上它。",
    "mechanism": [
      "① 标准注意力要materialize N×N 的注意力矩阵到显存，长序列时这块显存爆炸",
      "② FlashAttention 分块（block）计算，每块在片上 SRAM 里算完就累加，不把大矩阵写回 HBM",
      "③ ⚠️ 关键：它是**精确**算法（数学结果完全相同），通过 IO 感知 tiling 实现，不是砍精度",
      "④ 复杂度不变仍 O(n²)，但常数因子小得多，显存从 O(n²) 降到 O(n)",
      "⑤ 配套还有 PagedAttention（vLLM，缓解 KV Cache 碎片）",
      "⑥ 现在推理引擎（vLLM/TRT-LLM）几乎都默认启用"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["QKV分块", "片上SRAM计算", "在线softmax累加", "合并输出"],
      "frames": [
        { "s": 0, "note": "分块避免大矩阵落显存" },
        { "s": 1, "note": "块内片上计算" },
        { "s": 2, "note": "在线 softmax 边算边归一化" },
        { "s": 3, "note": "精确结果但快得多" }
      ]
    },
    "interviewQ": [
      "FlashAttention 是近似算法吗？",
      "它快在哪里（算力还是 IO）？",
      "PagedAttention 解决什么问题？"
    ],
    "keywords": ["FlashAttention", "IO优化", "长文本", "KV Cache", "显存", "分块"],
    "scene": [
      "部署长文档问答，吞吐上不去，换 FlashAttention + PagedAttention 后翻数倍。",
      "面试被问「注意力怎么优化」，答精确 IO 优化（Flash）+ KV Cache 管理（Paged）。"
    ],
    "tags": ["注意力", "性能", "工程优化"],
    "related": [
      { "id": "algo-position-encoding", "kind": "extends", "note": "共同支撑长上下文场景" }
    ]
  },
  {
    "id": "algo-page-rank",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": ["算法", "图算法", "PageRank 与图排序"],
    "title": "PageRank 怎么算？为什么比度数中心性更抗噪？",
    "oneLine": "网页重要性=被「重要的网页」指向，迭代求解特征向量；比单纯数度数更抗造谣噪点。",
    "analogy": "像「学霸推荐」：被很多普通同学夸的不算权威，被其他权威夸的才真权威。",
    "why": "它衡量「网络中更重要/更中心」的节点，比简单数度数更智能，是图排序的经典。",
    "mechanism": [
      "① 网页 i 的重要性 = 它被指向的权重之和，被重要网页指向贡献更大",
      "② 阻尼因子 0.85（论文值别乱调）+85%按链接分配 + 15%随机跳转",
      "③ 迭代式 PR = (1-d) + d×Σ(各来源的PR/出度)，直到收敛",
      "④ ⚠️ 悬挂节点（无出链）要均摊回填，否则它吞掉全图概率质量、变成黑洞",
      "⑤ 相比度数中心性：度数只数「我连着几个」，PageRank 数「连着我的有多重要」",
      "⑥ 个性化 PageRank（PPR）从已掌握节点出发扩散，用来推荐「下一步该学什么」"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["初始全1", "按入边分配", "阻尼混合", "迭代至收敛"],
      "frames": [
        { "s": 0, "note": "重要性沿链接传播" },
        { "s": 1, "note": "被重要节点指向才算重要" },
        { "s": 2, "note": "悬挂节点需均摊回填" },
        { "s": 3, "note": "收敛后得最终排名" }
      ]
    },
    "interviewQ": [
      "PageRank 的公式是什么？阻尼因子的作用？",
      "悬挂节点为什么要处理？",
      "个性化 PageRank 用来干什么？"
    ],
    "keywords": ["PageRank", "图排序", "中心性", "阻尼因子", "悬挂节点", "PPR"],
    "scene": [
      "用 PPR 从已掌握的卡推荐下一步学习的卡。",
      "面试被问「怎么找图里最重要的节点」，答 PageRank 比度数抗噪。"
    ],
    "tags": ["图算法", "排序", "中心性"],
    "related": [
      { "id": "algo-dijkstra", "kind": "compare", "note": "同为图算法，PPR 是迭代式打分，Dijkstra 是路径搜索" }
    ]
  },
  {
    "id": "algo-topk-sort",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": ["算法", "排序算法", "TopK 与堆"],
    "title": "求 TopK 为什么用堆而不是全排序？复杂度差多少？",
    "oneLine": "全排序 O(nlogn) 全排，堆维护只 O(nlogk)，当 k 远小于 n 时优势巨大。",
    "analogy": "要选 Top10，不必把500 人全排序，像擂台赛只需维护一张 10 强的榜单。",
    "why": "TopK 是面试和工程里的超高频题（推荐、日志 TopN、分位数），核心是「只求前K不求全序」。",
    "mechanism": [
      "① 全排序 O(nlogn) 求出全部顺序，但 TopK 只需要 K 个",
      "② 大顶堆（容量 K）：遍历时把当前元素和堆顶比，大于堆顶就替换堆顶并下沉",
      "③ 复杂度 O(nlogk)：建堆 O(k)，每次替换 O(logk)，共 n 次比较",
      "④ k 远小于 n 时优势显著（如 Top10 的n=百万，差距百倍）",
      "⑤ ⚠️ 若k 接近 n，全排序更简单更快（logk 接近 logn，且没有堆的常数开销）",
      "⑥ 流式数据必须用堆：数据量大到不能全放内存，边读边维护 TopK"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["遍历元素", "与堆顶比较", "替换并下沉", "堆内即TopK"],
      "frames": [
        { "s": 0, "note": "维护容量 K 的大顶堆" },
        { "s": 1, "note": "比堆顶：大的才进堆" },
        { "s": 2, "note": "O(logk) 下沉调整" },
        { "s": 3, "note": "堆里始终是当前 TopK" }
      ]
    },
    "interviewQ": [
      "TopK 用堆的复杂度？",
      "什么情况下堆不如全排序？",
      "流式数据求 TopK 怎么做？"
    ],
    "keywords": ["TopK", "堆", "优先级队列", "复杂度", "流式"],
    "scene": [
      "从百万条日志里找Top10 错误——用堆避免全排序的 O(nlogn)。",
      "面试被问「海量数据求 TopK」，答固定大小堆，边读边维护。"
    ],
    "tags": ["排序", "堆", "复杂度"],
    "related": [
      { "id": "algo-heap-sort", "kind": "extends", "note": "堆的另一个经典用途是堆排序" },
      { "id": "algo-dijkstra", "kind": "extends", "note": "Dijkstra 的优先队列就用堆" }
    ]
  },
  {
    "id": "algo-heap-sort",
    "domain": "算法",
    "category": "work",
    "subject": "algorithm",
    "topicPath": ["算法", "排序算法", "堆排序"],
    "title": "堆排序怎么保证 O(nlogn)？它稳定吗？",
    "oneLine": "建大顶堆后反复把堆顶(最大值)换到末尾、缩小堆并调整，O(nlogn)，原地但不稳定。",
    "analogy": "像选人当第一名：每次把最厉害的挑出来放第一位，剩下的重新排队再来。",
    "why": "它是唯一「最坏情况也有 O(nlogn) 且原地」的排序，面试常和数据结构一起问。",
    "mechanism": [
      "① 先把数组原地建成大顶堆（自底向上建堆 O(n)）",
      "② 把堆顶（最大值）与末尾交换，锁定它，缩小堆范围",
      "③ 对新堆顶下沉调整，恢复大顶堆性质，重复 n-1 次",
      "④ 建堆 O(n)+ n次调整O(logn) → 总 O(nlogn)",
      "⑤ ⚠️ 不稳定：相同元素的相对顺序会被打乱",
      "⑥ 原地（O(1) 额外空间）是它相比快排的最大优势"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["建大顶堆", "堆顶换末尾", "缩小堆", "下沉调整"],
      "frames": [
        { "s": 0, "note": "自底向上 O(n) 建堆" },
        { "s": 1, "note": "最大值就位" },
        { "s": 2, "note": "堆顶下沉恢复性质" },
        { "s": 3, "note": "重复直到排完" }
      ]
    },
    "interviewQ": [
      "堆排序为什么是 O(nlogn)？",
      "堆排序稳定吗？",
      "和快排相比有什么优缺点？"
    ],
    "keywords": ["堆排序", "大顶堆", "稳定性", "原地排序", "复杂度"],
    "scene": [
      "面试被问「最坏 O(nlogn) 且原地的排序」，答堆排序。",
      "排序 100 万数据且内存紧张，堆排序的原地特性有用。"
    ],
    "tags": ["排序", "堆", "复杂度"],
    "related": [
      { "id": "algo-topk-sort", "kind": "extends", "note": "TopK 是堆排序思路的局部应用" }
    ]
  }
];
if (typeof module !== "undefined" && module.exports) {
  module.exports = CARDS_ALGO_ATTN;
}