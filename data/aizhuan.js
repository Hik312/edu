// 严格 JSON 字面量：Node(vm) 与 Python(json) 都能直接读，请勿改回单引号
var CARDS_AI = [
  {
    "id": "ai-agent",
    "domain": "求职·AI工程",
    "topicPath": [
      "AI工程",
      "核心概念",
      "Agent"
    ],
    "title": "Agent（智能体）是怎么自主转起来的",
    "oneLine": "感知现状 → 思考规划 → 调用工具行动 → 观察结果，再回到思考，循环直到任务完成",
    "analogy": "像一个不会累的实习生：先看一眼当前局面，想清楚下一步，动手做，看结果，再想下一步，不交差不罢休",
    "why": "这是 LangChain/LangGraph、AutoGPT、各类工作流智能体的共同骨架；面试问 Agent，先答这个循环再谈框架",
    "mechanism": [
      "① 感知（Perceive）：把任务目标 + 上一轮的观察结果 + 记忆，拼成当前上下文",
      "② 思考（Think）：模型基于上下文做规划——下一步做什么、调哪个工具、还是直接给结论",
      "③ 行动（Act）：需要外部能力时走工具调用（Tool Calling），把模型决策变成真实操作",
      "④ 观察（Observe）：拿到工具返回的结果或环境反馈，写回上下文",
      "⑤ 回到 ② 继续循环，直到模型判断任务完成，或触发最大步数/预算上限而停止",
      "⑥ 整个过程由「停止条件」收口：要么产出最终结果，要么因步数/成本封顶而终止"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "perceive",
          "label": "感知上下文"
        },
        {
          "id": "think",
          "label": "思考规划"
        },
        {
          "id": "act",
          "label": "调用工具行动"
        },
        {
          "id": "observe",
          "label": "观察结果"
        }
      ],
      "edges": [
        {
          "from": "perceive",
          "to": "think"
        },
        {
          "from": "think",
          "to": "act"
        },
        {
          "from": "act",
          "to": "observe"
        },
        {
          "from": "observe",
          "to": "think"
        }
      ],
      "frames": [
        {
          "n": "perceive",
          "note": "上下文 = 目标 + 历史观察 + 记忆，缺了记忆每轮都从零开始"
        },
        {
          "n": "think",
          "note": "模型在此决定：继续调工具 / 直接回答 / 判定完成"
        },
        {
          "n": "act",
          "note": "这一步才真正接触外部世界：查库、跑代码、发请求"
        },
        {
          "n": "observe",
          "note": "工具结果是下一轮思考的原料，闭环靠它维持"
        }
      ]
    },
    "interviewQ": [
      "Agent 和普通「问一句答一句」的对话机器人本质区别在哪？（答：自主循环 + 工具调用 + 停止条件）",
      "Agent 为什么容易跑飞、停不下来？怎么约束？（答：步数/预算上限 + 明确的停止条件 + 反思节点）"
    ],
    "keywords": [
      "Agent",
      "ReAct",
      "工具调用",
      "自主循环",
      "停止条件"
    ],
    "scene": [
      "代码助手：你让它「给这个仓库加一个登录接口」，它自己读代码、改文件、跑测试、看报错再修",
      "数据分析：把「整理这份 Excel 并画趋势图」交给 Agent，它自己读表、写脚本、生成图表",
      "坑：没有步数上限时，Agent 会反复调工具烧 token，一定要设 max_steps 和超时"
    ],
    "tags": [
      "高频",
      "必会"
    ],
    "category": "work",
    "subject": "ai",
    "related": [
      {
        "id": "ai-toolcall",
        "kind": "extends",
        "note": "Agent 的「行动」就是调用工具，tool calling 是它落地能力的接口"
      },
      {
        "id": "ai-memory",
        "kind": "extends",
        "note": "没有记忆的 Agent 每轮都从零开始，多轮与长任务撑不住"
      },
      {
        "id": "ai-langgraph",
        "kind": "compare",
        "note": "Agent 是概念，LangGraph 是把它落成代码的一种工程范式"
      },
      {
        "id": "ai-rag",
        "kind": "compare",
        "note": "Agent和RAG都涉及信息处理，但方式不同"
      },
      {
        "id": "ai-embedding",
        "kind": "compare",
        "note": "Agent和Embedding都涉及信息转换，但目标不同"
      }
    ]
  },
  {
    "id": "ai-rag",
    "domain": "求职·AI工程",
    "topicPath": [
      "AI工程",
      "核心概念",
      "RAG"
    ],
    "title": "RAG 检索增强生成是怎么办到的",
    "oneLine": "先根据用户问题从知识库检索相关片段，拼进提示词，再让大模型基于这些证据作答",
    "analogy": "像开卷考试：不许瞎编，先翻书（检索）找到相关页，把关键段落抄到答题纸上（拼提示），再组织语言写答案",
    "why": "大模型训练数据有截止日期、不知你的私有资料；RAG 用检索把「最新/私有知识」喂进去，大幅减少幻觉",
    "mechanism": [
      "① 文档切分（Chunking）：把长文档按固定长度或语义边界切成片段，过长会稀释检索精度",
      "② 向量化入库：每段文本经 Embedding 模型变成向量，写入向量数据库并建立索引",
      "③ 查询向量化：用户问题同样经同一个 Embedding 模型转成向量",
      "④ 相似检索 + 重排：用向量距离召回 Top-K 片段，再用重排模型（rerank）精筛",
      "⑤ 拼装提示：把召回片段作为上下文，和问题一起塞进提示词模板",
      "⑥ 生成答案：大模型基于「问题 + 检索到的证据」作答，并尽量给出引用来源"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "文档切分",
        "向量化入库",
        "查询向量化",
        "相似检索+重排",
        "拼装提示",
        "大模型生成"
      ],
      "frames": [
        {
          "s": 0,
          "note": "切分粒度是 RAG 效果的命门：太大噪声多，太小丢上下文"
        },
        {
          "s": 1,
          "note": "入库这一步离线做，决定后续检索的上限"
        },
        {
          "s": 2,
          "note": "必须用和入库同一个 Embedding 模型，否则向量空间不一致"
        },
        {
          "s": 3,
          "note": "召回看向量近邻，重排看语义相关，两步互补"
        },
        {
          "s": 4,
          "note": "提示词里要显式告诉模型「只依据下列资料回答」以减少编造"
        },
        {
          "s": 5,
          "note": "输出最好带出处，便于人工核验与追溯"
        }
      ]
    },
    "interviewQ": [
      "RAG 和微调（Fine-tuning）分别解决什么问题？（答：RAG 补「知识/时效性」，微调补「能力/风格」）",
      "检索召回了但答案还是错，可能卡在哪一步？（答：切分粒度 / embedding 选型 / 重排缺失 / 提示词没约束）"
    ],
    "keywords": [
      "RAG",
      "检索增强",
      "Chunking",
      "重排",
      "幻觉抑制"
    ],
    "scene": [
      "企业知识库问答：把内部文档灌进向量库，员工用自然语言查制度、查流程",
      "客服助手：检索产品手册片段后作答，避免模型编出不存在的退款政策",
      "坑：直接把整篇 PDF 当一段向量，检索时噪声太大；一定要先切分"
    ],
    "tags": [
      "高频",
      "必会"
    ],
    "category": "work",
    "subject": "ai",
    "related": [
      {
        "id": "ai-embedding",
        "kind": "prereq",
        "note": "检索的「相似」建立在向量距离上，向量化是前置步骤"
      },
      {
        "id": "ai-vectordb",
        "kind": "prereq",
        "note": "海量向量必须靠向量库索引才能毫秒级召回"
      },
      {
        "id": "ai-agent",
        "kind": "compare",
        "note": "RAG 解决「知识从哪来」，Agent 解决「活怎么干」，生产里常叠加"
      },
      {
        "id": "ai-toolcall",
        "kind": "prereq",
        "note": "理解工具调用机制能更好整合到 RAG 的生成流程中"
      },
      {
        "id": "ai-prompt",
        "kind": "compare",
        "note": "RAG 依赖结构化提示，对比看如何用提示控制信息检索"
      }
    ]
  },
  {
    "id": "ai-embedding",
    "domain": "求职·AI工程",
    "topicPath": [
      "AI工程",
      "核心概念",
      "Embedding"
    ],
    "title": "Embedding 怎么把文本变成向量",
    "oneLine": "用神经网络把词/句/段映射成一个高维稠密向量，语义相近的文本向量也相近",
    "analogy": "像给每段文字发一张「意义坐标卡」：意思接近的卡在坐标里挨得近，意思无关的隔得远",
    "why": "向量是机器算「语义相似」的唯一抓手——搜索、去重、聚类、RAG 检索全都建立在它之上",
    "mechanism": [
      "① 清洗与分词：统一大小写、去噪，切成 token（子词更省词表）",
      "② Token 编码：每个 token 先映射成 id，再查表得到初始嵌入",
      "③ 送入模型：Transformer 编码器让每个 token 吸收上下文信息",
      "④ 池化（Pooling）：把一串 token 向量压缩成句/段级单一向量（如取 [CLS] 或均值）",
      "⑤ 归一化输出：通常做 L2 归一化，方便之后用余弦相似度直接计算距离"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "清洗分词",
        "Token编码",
        "编码器",
        "池化",
        "归一化向量"
      ],
      "frames": [
        {
          "s": 0,
          "note": "同一模型对同义词要输出近邻向量，清洗不当会破坏这种一致性"
        },
        {
          "s": 1,
          "note": "子词切分让罕见词也能被表示，是中文分词外的另一条路"
        },
        {
          "s": 2,
          "note": "上下文相关：同一个词在不同句子里向量不同，这是它强于老式词袋的地方"
        },
        {
          "s": 3,
          "note": "池化策略影响句向量质量，均值/CLS 是常见两种"
        },
        {
          "s": 4,
          "note": "归一化后余弦相似度等价于点积，检索计算更快"
        }
      ]
    },
    "interviewQ": [
      "为什么语义搜索要用向量而不是关键词匹配？（答：能捕捉同义/近义，关键词对表述差异无能为力）",
      "余弦相似度和欧氏距离在归一化后是什么关系？（答：归一化后余弦=点积，排序与欧氏距离一致）"
    ],
    "keywords": [
      "Embedding",
      "向量化",
      "Transformer",
      "余弦相似度",
      "语义检索"
    ],
    "scene": [
      "推荐去重：把两篇新闻各自向量化，距离近就判定为重复报道",
      "语义搜索：搜「怎么退订会员」也能命中标题写「取消订阅方法」的文档",
      "坑：用 A 模型入库、用 B 模型查询，向量空间不同，相似度全作废"
    ],
    "tags": [
      "基础",
      "必会"
    ],
    "category": "work",
    "subject": "ai",
    "related": [
      {
        "id": "ai-vectordb",
        "kind": "extends",
        "note": "向量是向量库的写入单元，二者是输入输出关系"
      },
      {
        "id": "ai-rag",
        "kind": "extends",
        "note": "RAG 的检索质量天花板由 embedding 模型决定"
      },
      {
        "id": "ai-agent",
        "kind": "compare",
        "note": "Agent和Embedding都涉及信息转换，但目标不同"
      }
    ]
  },
  {
    "id": "ai-vectordb",
    "domain": "求职·AI工程",
    "topicPath": [
      "AI工程",
      "核心概念",
      "向量数据库"
    ],
    "title": "向量数据库怎么在海量向量里查相似",
    "oneLine": "用近似最近邻（ANN）索引把「暴力比对所有向量」降成「先粗筛候选再精比」，换一点精度换百倍速度",
    "analogy": "像在图书馆找书：不逐本翻，而是先看楼层导览（图索引）锁定几排，再在排里细找",
    "why": "百万级以上向量若每条都算余弦，延迟根本扛不住线上检索；向量库用索引把毫秒级召回变成现实",
    "mechanism": [
      "① 写入：每条记录存「向量 + 原始文本 + 元数据」，并建立 ANN 索引",
      "② HNSW 路线：建多层可导航小世界图，查询时从顶层粗定位、逐层下钻到最细层",
      "③ IVF 路线：用聚类把向量空间切成若干桶（倒排），先找最近的桶再桶内细比",
      "④ 查询：把问题向量送入索引，返回 Top-K 近邻及距离",
      "⑤ 元数据过滤：在向量召回基础上叠加标量过滤（如按时间、来源筛选）"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "HNSW 多层图",
          "lines": [
            "结构：多层可导航小世界图",
            "查询：顶层粗定位→逐层下钻",
            "优点：召回高、速度快",
            "代价：内存占用大"
          ]
        },
        {
          "title": "IVF+PQ 倒排+量化",
          "lines": [
            "结构：聚类分桶 + 向量压缩",
            "查询：先找近桶再桶内比",
            "优点：省内存、易扩展",
            "代价：精度略损"
          ]
        },
        {
          "title": "Flat 暴力",
          "lines": [
            "结构：全量逐条比",
            "优点：100% 精确",
            "代价：数据一大就慢死",
            "用途：小库或基线校验"
          ]
        }
      ],
      "frames": [
        {
          "note": "先问规模：数据量决定该选图索引还是量化索引",
          "active": []
        },
        {
          "note": "线上低延迟、内存充裕，优先 HNSW",
          "active": [
            0
          ]
        },
        {
          "note": "亿级数据、内存吃紧，IVF+PQ 更实际",
          "active": [
            1
          ]
        },
        {
          "note": "无论哪种，召回都是近似的，别指望和暴力完全一致",
          "active": [
            0,
            1,
            2
          ]
        }
      ]
    },
    "interviewQ": [
      "为什么不能直接暴力比对全部向量？（答：O(N) 每次查询，百万级就扛不住线上延迟）",
      "HNSW 和 IVF 各自适合什么场景？（答：HNSW 要速度内存足，IVF+PQ 要省内存能扩展）"
    ],
    "keywords": [
      "向量数据库",
      "ANN",
      "HNSW",
      "IVF",
      "近似检索"
    ],
    "scene": [
      "RAG 检索后端：Milvus / pgvector / Qdrant 存千万级文档向量供实时召回",
      "以图搜图：把图片向量化后入库，查询时返回视觉近邻",
      "坑：元数据过滤太严会把 ANN 候选全滤掉，要确认索引支持「预过滤」而非「后过滤」"
    ],
    "tags": [
      "基础"
    ],
    "category": "work",
    "subject": "ai",
    "related": [
      {
        "id": "ai-embedding",
        "kind": "prereq",
        "note": "存进去的必须是向量，维度与距离度量要和写入时一致"
      },
      {
        "id": "ai-rag",
        "kind": "extends",
        "note": "它是 RAG 检索阶段的实际执行者"
      }
    ]
  },
  {
    "id": "ai-toolcall",
    "domain": "求职·AI工程",
    "topicPath": [
      "AI工程",
      "核心概念",
      "工具调用"
    ],
    "title": "Tool Calling（工具调用）是怎么工作的",
    "oneLine": "把可用函数的签名写进提示词，模型输出结构化的调用请求，由外部代码执行后再把结果喂回模型",
    "analogy": "像点菜：菜单（函数清单）摆桌上，你（模型）报菜名和口味（参数），后厨（代码）做菜，再把菜（结果）端回你面前",
    "why": "大模型本身不能查实时数据、不能执行代码；工具调用是它连接外部世界的唯一正规通道，也是 Agent 行动的基础",
    "mechanism": [
      "① 声明工具：把函数名、参数 schema（JSON Schema）随请求发给模型",
      "② 模型决策：模型判断当前是否需要调用、调哪个、参数填什么，输出结构化 tool_calls",
      "③ 执行：应用侧按 tool_calls 真正运行函数（查库/HTTP/算数等）",
      "④ 回灌：把函数返回值作为 tool 消息追加进对话历史",
      "⑤ 再决策：模型看到结果后，继续调用下一个工具或直接给出最终回答"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "decide",
          "label": "模型决策"
        },
        {
          "id": "emit",
          "label": "输出调用请求"
        },
        {
          "id": "exec",
          "label": "执行函数"
        },
        {
          "id": "return",
          "label": "结果回灌"
        },
        {
          "id": "replan",
          "label": "再决策"
        }
      ],
      "edges": [
        {
          "from": "decide",
          "to": "emit"
        },
        {
          "from": "emit",
          "to": "exec"
        },
        {
          "from": "exec",
          "to": "return"
        },
        {
          "from": "return",
          "to": "replan"
        },
        {
          "from": "replan",
          "to": "decide"
        }
      ],
      "frames": [
        {
          "n": "decide",
          "note": "是否调用由模型自主判断，取决于你给的工具描述是否清晰"
        },
        {
          "n": "emit",
          "note": "输出的是 JSON 参数，不是自然语言，便于代码解析"
        },
        {
          "n": "exec",
          "note": "执行在模型之外，权限与报错都归应用侧管控"
        },
        {
          "n": "return",
          "note": "结果必须回灌，否则模型看不到自己调用的产出"
        },
        {
          "n": "replan",
          "note": "多步任务靠这个回环串起来，直到无需再调工具"
        }
      ]
    },
    "interviewQ": [
      "Function Calling 和 RAG 有什么关系？（答：RAG 常作为「检索工具」被 Agent 通过 tool calling 调用）",
      "模型输出的参数格式错了（如类型不符）怎么兜底？（答：校验 schema、失败重试、把错误回灌让模型修正）"
    ],
    "keywords": [
      "Tool Calling",
      "Function Calling",
      "JSON Schema",
      "工具",
      "Agent行动"
    ],
    "scene": [
      "查天气：声明 get_weather(city) 工具，模型填城市，代码调 API 拿结果",
      "数据库问答：模型生成 SQL 经工具执行，再把查询结果用于回答",
      "坑：工具描述写得含糊，模型就乱填参数；schema 一定要写清类型与必填项"
    ],
    "tags": [
      "高频",
      "必会"
    ],
    "category": "work",
    "subject": "ai",
    "related": [
      {
        "id": "ai-prompt",
        "kind": "prereq",
        "note": "工具描述与调用格式都写在 prompt 里，模型据此决策"
      },
      {
        "id": "ai-agent",
        "kind": "extends",
        "note": "Agent 靠它把「想做」变成「真做」"
      },
      {
        "id": "ai-rag",
        "kind": "extends",
        "note": "理解工具调用机制能更好整合到 RAG 的生成流程中"
      },
      {
        "id": "ai-langgraph",
        "kind": "prereq",
        "note": "图里的节点常常就是一个工具调用步骤"
      },
      {
        "id": "ai-mcp",
        "kind": "prereq",
        "note": "工具调用是 MCP 实现的具体方式之一"
      }
    ]
  },
  {
    "id": "ai-langgraph",
    "domain": "求职·AI工程",
    "topicPath": [
      "AI工程",
      "框架",
      "LangGraph"
    ],
    "title": "LangGraph 状态图是怎么搭出来的",
    "oneLine": "用「节点 = 算子、边 = 流转、共享状态 = 上下文」把 Agent 的循环显式画成一张可中断、可回放的有向图",
    "analogy": "像工厂流水线图纸：每个工位（节点）干一件事，传送带（边）决定下一步去哪，中央看板（状态）记录做到哪了",
    "why": "比线性 Chain 更可控：支持分支、循环、人工介入（human-in-the-loop）和断点续跑，适合复杂多步 Agent",
    "mechanism": [
      "① 定义 State：用一个带Reducer的共享结构（如 TypedDict）贯穿全程，节点往里写、从里读",
      "② 加节点（Node）：每个节点是一个函数，输入当前 State、输出对 State 的更新",
      "③ 加边（Edge）：普通边按顺序连；条件边（Conditional Edge）按 State 内容路由到不同下一节点",
      "④ 配入口与终点：指定 START 和 END，图从 START 流入、到 END 流出",
      "⑤ 挂检查点（Checkpoint）：把每步 State 落库，支持中断恢复、回放与人工审批"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "state",
          "label": "共享状态"
        },
        {
          "id": "node",
          "label": "节点/算子"
        },
        {
          "id": "edge",
          "label": "边/流转"
        },
        {
          "id": "cond",
          "label": "条件路由"
        },
        {
          "id": "end",
          "label": "终点END"
        }
      ],
      "edges": [
        {
          "from": "state",
          "to": "node"
        },
        {
          "from": "node",
          "to": "edge"
        },
        {
          "from": "edge",
          "to": "cond"
        },
        {
          "from": "cond",
          "to": "node"
        },
        {
          "from": "cond",
          "to": "end"
        }
      ],
      "frames": [
        {
          "n": "state",
          "note": "所有节点共享同一份状态，这是图能串起长任务的关键"
        },
        {
          "n": "node",
          "note": "纯函数式：吃 State 产更新，便于测试与复用"
        },
        {
          "n": "edge",
          "note": "普通边是顺序，条件边按 State 决定分支"
        },
        {
          "n": "cond",
          "note": "这里实现「该继续还是收工」，对应 Agent 的停止条件"
        },
        {
          "n": "end",
          "note": "到 END 才产出最终结果，中途可借检查点暂停"
        }
      ]
    },
    "interviewQ": [
      "LangGraph 相比普通 Chain 强在哪？（答：可循环、可分支、可中断恢复、显式状态）",
      "为什么复杂 Agent 需要 Checkpoint？（答：支持长任务断点续跑与人工介入审批）"
    ],
    "keywords": [
      "LangGraph",
      "状态图",
      "Reducer",
      "条件边",
      "Checkpoint"
    ],
    "scene": [
      "多步研究助手：规划→检索→写草稿→评审→修订，评审不通过就绕回修订节点",
      "带人工审批的工单：执行到「确认发送」节点暂停，人点通过才走 END",
      "坑：State 的 Reducer 写错，多节点写入会互相覆盖，调试时先看状态合并逻辑"
    ],
    "tags": [
      "框架"
    ],
    "category": "work",
    "subject": "ai",
    "related": [
      {
        "id": "ai-agent",
        "kind": "prereq",
        "note": "它解决的是 Agent 循环如何被显式编排与控制"
      },
      {
        "id": "ai-toolcall",
        "kind": "extends",
        "note": "图里的节点常常就是一个工具调用步骤"
      }
    ]
  },
  {
    "id": "ai-prompt",
    "domain": "求职·AI工程",
    "topicPath": [
      "AI工程",
      "核心概念",
      "提示词工程"
    ],
    "title": "提示词工程的核心套路是什么",
    "oneLine": "用「角色 + 任务 + 上下文 + 格式 + 示例」把模糊需求钉成模型能稳定复现的指令",
    "analogy": "像给新人写工作说明书：先说你是谁、要干什么、背景是什么、交付长什么样、给两个样例，他才不会跑偏",
    "why": "同一模型，提示词质量直接决定输出好坏；它是零成本、最先该调的杠杆，也是工具调用和 Agent 的底层载体",
    "mechanism": [
      "① 角色设定：给模型一个身份与口吻（如「你是资深后端工程师」），约束回答视角",
      "② 任务描述：用一句话说清要做什么，避免歧义",
      "③ 上下文/背景：把必要的已知信息、约束条件、禁忌写进去",
      "④ 输出格式约束：规定返回结构（JSON / 列表 / 模板），方便下游解析",
      "⑤ 示例（Few-shot）：给 1~3 个输入输出样例，模型照着学格式与风格",
      "⑥ 防跑偏：显式要求「只依据给定资料」「不确定就说明」，降低编造与越界"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "角色设定",
        "任务描述",
        "上下文",
        "输出格式",
        "少样本示例",
        "防跑偏约束"
      ],
      "frames": [
        {
          "s": 0,
          "note": "身份帮模型选对知识域和语气"
        },
        {
          "s": 1,
          "note": "任务越具体，输出越可控"
        },
        {
          "s": 2,
          "note": "缺上下文模型只能靠训练记忆猜，易错"
        },
        {
          "s": 3,
          "note": "结构化输出是接 Agent/工具的前提"
        },
        {
          "s": 4,
          "note": "样例比长篇规则更管用，尤其定格式"
        },
        {
          "s": 5,
          "note": "显式兜底能压住幻觉和越权"
        }
      ]
    },
    "interviewQ": [
      "Few-shot 为什么往往比零样本更稳？（答：样例把期望的格式与风格直接演示出来）",
      "提示词写得很长但效果差，可能问题在哪？（答：指令冲突、缺少示例、没约束输出格式）"
    ],
    "keywords": [
      "提示词工程",
      "Few-shot",
      "角色设定",
      "结构化输出",
      "System Prompt"
    ],
    "scene": [
      "分类打标：提示词要求「只输出 JSON {label, reason}」，下游直接解析",
      "代码评审：贴代码 + 「你是严谨的 reviewer，列出风险与改进」",
      "坑：在一个提示里同时要求「详尽」又要求「一句话」，指令互搏模型会乱"
    ],
    "tags": [
      "基础",
      "必会"
    ],
    "category": "work",
    "subject": "ai",
    "related": [
      {
        "id": "ai-toolcall",
        "kind": "extends",
        "note": "工具调用本质是 prompt 里夹带结构化指令"
      },
      {
        "id": "ai-agent",
        "kind": "extends",
        "note": "Agent 的规划与反思都靠 prompt 驱动"
      },
      {
        "id": "ai-rag",
        "kind": "compare",
        "note": "RAG 依赖结构化提示，对比看如何用提示控制信息检索"
      },
      {
        "id": "ai-system-prompt-principles",
        "kind": "prereq",
        "note": "理解系统提示原则能更好设计角色与任务的指令结构"
      }
    ]
  },
  {
    "id": "ai-memory",
    "domain": "求职·AI工程",
    "topicPath": [
      "AI工程",
      "进阶",
      "记忆"
    ],
    "title": "Agent 的短期记忆和长期记忆怎么管",
    "oneLine": "短期记忆存当前对话窗口，长期记忆落外部存储（向量库/数据库），按需要读回，并做压缩与淘汰",
    "analogy": "像人的脑子：眼前事记在便签（短期），重要经验写进笔记本（长期），笔记本太厚就做目录摘要（压缩）",
    "why": "上下文窗口有限且贵；没有记忆，Agent 跨轮就失忆、长任务就崩；记忆是 Agent 能「持续干活」的底座",
    "mechanism": [
      "① 短期记忆：最近若干轮对话直接放上下文窗口，最新鲜但容量受限",
      "② 写入长期记忆：把重要结论/用户偏好摘要后存入向量库或键值库",
      "③ 读取：每轮按需检索相关记忆拼回上下文（常与 RAG 机制重合）",
      "④ 压缩：对过长记忆做摘要，保留要点、丢弃细节，控制 token 成本",
      "⑤ 淘汰：按时间或重要性清理陈旧记忆，避免噪声淹没关键信息"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "write",
          "label": "写入记忆"
        },
        {
          "id": "read",
          "label": "读取召回"
        },
        {
          "id": "compress",
          "label": "压缩摘要"
        },
        {
          "id": "evict",
          "label": "淘汰陈旧"
        }
      ],
      "edges": [
        {
          "from": "write",
          "to": "read"
        },
        {
          "from": "read",
          "to": "compress"
        },
        {
          "from": "compress",
          "to": "evict"
        },
        {
          "from": "evict",
          "to": "write"
        }
      ],
      "frames": [
        {
          "n": "write",
          "note": "什么值得记由模型判定，记错了比忘了更糟"
        },
        {
          "n": "read",
          "note": "读取常复用 RAG 的检索链路"
        },
        {
          "n": "compress",
          "note": "长对话不压缩，token 成本和延迟都会爆"
        },
        {
          "n": "evict",
          "note": "不淘汰，陈旧信息会污染决策"
        }
      ]
    },
    "interviewQ": [
      "短期记忆和长期记忆分别解决什么问题？（答：短期保当下上下文，长期跨轮/跨会话保留经验）",
      "记忆越多越好吗？（答：不是，噪声会淹没信号，要压缩与淘汰）"
    ],
    "keywords": [
      "记忆",
      "短期记忆",
      "长期记忆",
      "压缩",
      "上下文窗口"
    ],
    "scene": [
      "个人助手：记住「用户不喝咖啡」，之后推荐都避开",
      "长文档分析：把中间结论存长期记忆，避免一轮装不下整篇",
      "坑：把每一步都写进长期记忆，检索回来全是噪声，反而拖垮回答"
    ],
    "tags": [
      "进阶"
    ],
    "category": "work",
    "subject": "ai",
    "related": [
      {
        "id": "ai-agent",
        "kind": "prereq",
        "note": "记忆是 Agent 维持多轮上下文与长期偏好的底座"
      },
      {
        "id": "ai-rag",
        "kind": "compare",
        "note": "RAG 是外挂知识库，记忆是 Agent 自己的经验，一个向外一个向内"
      },
      {
        "id": "ai-context-window-management",
        "kind": "prereq",
        "note": "理解上下文窗口管理能更好设计短期记忆的存储与压缩"
      },
      {
        "id": "ai-long-term-memory-storage",
        "kind": "prereq",
        "note": "理解长期记忆存储能更好设计长期记忆的存储与读取"
      },
      {
        "id": "ai-agent-core-components",
        "kind": "compare",
        "note": "Agent 核心组件包含记忆模块，对比看记忆在系统中的位置"
      }
    ]
  },
  {
    "id": "ai-multiagent",
    "domain": "求职·AI工程",
    "topicPath": [
      "AI工程",
      "进阶",
      "多智能体"
    ],
    "title": "多智能体是怎么协作的",
    "oneLine": "把大任务拆给多个各司其职的 Agent，靠共享状态/消息总线分工、汇总、评审，比一个万能 Agent 更稳",
    "analogy": "像项目组：有人调研、有人写、有人审，彼此通过群聊（共享黑板）对齐进度，而不是一个人硬扛全部",
    "why": "单 Agent 什么都干容易跑偏且上下文爆炸；多 Agent 用「分工 + 专门提示」换取可控性与专业度",
    "mechanism": [
      "① 任务分解：由一个 Orchestrator 把目标拆成子任务并分配角色",
      "② 委派执行：各子 Agent 在自己的上下文里独立完成子任务",
      "③ 状态同步：通过共享黑板/消息总线交换中间结果，保持对齐",
      "④ 汇总：把各子任务产出合并成阶段性成果",
      "⑤ 评审/裁决：引入 critic 或投票，对汇总结过筛，不达标则打回重做"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "decompose",
          "label": "任务分解"
        },
        {
          "id": "dispatch",
          "label": "委派"
        },
        {
          "id": "execute",
          "label": "子Agent执行"
        },
        {
          "id": "aggregate",
          "label": "汇总"
        },
        {
          "id": "review",
          "label": "评审裁决"
        }
      ],
      "edges": [
        {
          "from": "decompose",
          "to": "dispatch"
        },
        {
          "from": "dispatch",
          "to": "execute"
        },
        {
          "from": "execute",
          "to": "aggregate"
        },
        {
          "from": "aggregate",
          "to": "review"
        },
        {
          "from": "review",
          "to": "dispatch"
        }
      ],
      "frames": [
        {
          "n": "decompose",
          "note": "拆得好坏直接决定后面协不协作得起来"
        },
        {
          "n": "dispatch",
          "note": "角色提示要专，别让每个 Agent 都当通才"
        },
        {
          "n": "execute",
          "note": "子 Agent 各自上下文隔离，互不污染"
        },
        {
          "n": "aggregate",
          "note": "合并方式很关键，简单拼接常丢逻辑"
        },
        {
          "n": "review",
          "note": "评审不通过就打回，形成质量闭环"
        }
      ]
    },
    "interviewQ": [
      "多智能体相比单智能体解决了什么痛点？（答：上下文隔离、专业分工、可加评审闭环）",
      "多 Agent 的代价是什么？（答：更多 token、更慢、编排与状态同步复杂度高）"
    ],
    "keywords": [
      "多智能体",
      "Orchestrator",
      "角色分工",
      "共享黑板",
      "评审"
    ],
    "scene": [
      "代码生成：一个写、一个审、一个跑测试，三 Agent 串成流水线",
      "调研报告：多个 Agent 分头查不同主题，再汇总成一份",
      "坑：Agent 之间消息没设计好，会出现「互相甩锅」或无限循环协商"
    ],
    "tags": [
      "进阶"
    ],
    "category": "work",
    "subject": "ai",
    "related": [
      {
        "id": "ai-agent",
        "kind": "extends",
        "note": "多智能体是多个单 Agent 的分工协作，是单体的扩展"
      },
      {
        "id": "ai-memory",
        "kind": "extends",
        "note": "子 Agent 之间需要共享黑板/记忆来对齐状态"
      },
      {
        "id": "ai-eval",
        "kind": "compare",
        "note": "评估效果涉及多 Agent 协作，对比看如何评估协作质量"
      },
      {
        "id": "ai-communication-patterns",
        "kind": "prereq",
        "note": "理解通信模式能更好设计多 Agent 的协作方式"
      },
      {
        "id": "ai-a2a-protocol",
        "kind": "compare",
        "note": "A2A 协议涉及通信模式，对比看如何实现 Agent 间协作"
      }
    ]
  },
  {
    "id": "ai-eval",
    "domain": "求职·AI工程",
    "topicPath": [
      "AI工程",
      "评估",
      "效果评测"
    ],
    "title": "RAG / Agent 怎么科学地评估效果",
    "oneLine": "用固定评测集 + 分层指标，把「感觉还行」变成可量化、可回归对比的数字",
    "analogy": "像考试打分：先有标准答卷（评测集），再按得分点（指标）逐项判分，这周和上周能直接比高低",
    "why": "不评估就无法迭代——你改了切分策略、换了模型，到底变好还是变坏，只能靠指标说话",
    "mechanism": [
      "① 构建评测集：准备「问题 + 标准答案/标准检索片段 + 评分标准」的黄金集",
      "② 跑通链路：用同一套输入分别跑新旧版本，记录全过程（检索片段、工具调用、最终答案）",
      "③ 计算指标：RAG 看上下文召回率/答案相关性/忠实度；Agent 看任务完成率/工具调用正确率",
      "④ 人工抽检：对自动指标存疑的样本做人工判分，校准自动指标偏差",
      "⑤ 回归比对：把新旧版本指标并排，确认改动能带来正向提升而非偶然波动"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "构建评测集",
        "跑通链路",
        "计算指标",
        "人工抽检",
        "回归比对"
      ],
      "frames": [
        {
          "s": 0,
          "note": "评测集质量决定评估可信度，别用训练时见过的题"
        },
        {
          "s": 1,
          "note": "保留中间产物，便于定位是检索差还是生成差"
        },
        {
          "s": 2,
          "note": "RAG 与 Agent 指标不同，别混用一把尺"
        },
        {
          "s": 3,
          "note": "自动指标会偏，关键样本要人看"
        },
        {
          "s": 4,
          "note": "没有回归基线，你根本不知道改了变好还是变坏"
        }
      ]
    },
    "interviewQ": [
      "RAG 和 Agent 的评估指标有什么区别？（答：RAG 重检索与忠实度，Agent 重任务完成与工具正确）",
      "为什么光看最终答案准确率不够？（答：要定位病根是检索、生成还是规划，需分层指标）"
    ],
    "keywords": [
      "评估",
      "评测集",
      "召回率",
      "忠实度",
      "回归"
    ],
    "scene": [
      "上线前验收：用 200 道黄金问题对比新旧 RAG，确认答案相关性提升",
      "Agent 调优：统计任务完成率，发现工具调用错误率高就先修工具描述",
      "坑：用和调优时相同的题当验收，指标虚高，要留独立测试集"
    ],
    "tags": [
      "进阶"
    ],
    "category": "work",
    "subject": "ai",
    "related": [
      {
        "id": "ai-rag",
        "kind": "extends",
        "note": "RAG 评估看上下文召回率与答案忠实度"
      },
      {
        "id": "ai-agent",
        "kind": "extends",
        "note": "Agent 评估还要看任务完成率与工具调用正确性"
      },
      {
        "id": "ai-memory",
        "kind": "prereq",
        "note": "理解记忆管理能更好设计评估指标的维度"
      },
      {
        "id": "ai-multiagent",
        "kind": "compare",
        "note": "多 Agent 协作涉及评估指标，对比看如何评估协作质量"
      },
      {
        "id": "ai-evaluation-tools-comparison",
        "kind": "compare",
        "note": "评估工具对比涉及评估指标，对比看如何选择工具"
      }
    ]
  }
];
if (typeof module !== "undefined" && module.exports) {
  module.exports = CARDS_AI;
}
