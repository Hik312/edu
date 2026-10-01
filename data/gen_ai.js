// 自动生成于 2026-09-29 by scripts/gen_cards.py（大纲批量造卡）。
// 机器产出，人工复核后可保留/删改；此文件由 git 管理，属「内容」不是「状态」。
var CARDS_AI = [
  {
    "id": "ai-transformer-self-attention",
    "domain": "AI工程",
    "category": "work",
    "subject": "ai",
    "topicPath": [
      "AI工程",
      "Transformer 自注意力机制"
    ],
    "title": "Transformer 自注意力机制是怎么工作的？",
    "oneLine": "自注意力机制让模型关注输入中不同位置的信息。",
    "analogy": "在图书馆里，读者能同时关注不同书架上的书。",
    "why": "解决传统RNN无法并行处理长序列的问题。",
    "mechanism": [
      "① 每个词生成查询、键、值向量",
      "② 通过点积计算词与词的相关性",
      "③ 用Softmax归一化相关性得到权重",
      "④ 加权求和得到最终的注意力输出"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "输入词向量",
        "计算查询键值",
        "计算相关性",
        "加权求和输出"
      ],
      "frames": [
        {
          "s": 0,
          "note": "输入词向量被拆分成查询、键、值向量"
        },
        {
          "s": 1,
          "note": "通过点积计算词与词的相关性"
        },
        {
          "s": 2,
          "note": "用Softmax归一化相关性得到权重"
        },
        {
          "s": 3,
          "note": "加权求和得到最终的注意力输出"
        }
      ]
    },
    "interviewQ": [
      "自注意力机制和多头注意力有什么区别？",
      "如何计算自注意力的得分？"
    ],
    "keywords": [
      "自注意力机制",
      "多头注意力",
      "查询键值"
    ],
    "scene": [
      "在自然语言处理任务中，模型能同时关注句子中的多个词",
      "在翻译任务中，模型能正确捕捉句子间的依赖关系"
    ],
    "tags": [
      "Transformer",
      "自然语言处理",
      "注意力机制"
    ],
    "related": []
  },
  {
    "id": "ai-transformer-position-encoding",
    "domain": "AI工程",
    "category": "work",
    "subject": "ai",
    "topicPath": [
      "AI工程",
      "位置编码的作用"
    ],
    "title": "位置编码是怎么让Transformer理解位置信息的？",
    "oneLine": "位置编码帮助模型理解序列中词的位置关系。",
    "analogy": "在快递站，每个包裹有唯一的地址标识。",
    "why": "解决Transformer无法处理序列顺序的问题。",
    "mechanism": [
      "① 用正弦和余弦函数生成位置编码",
      "② 每个位置的编码包含不同频率的正弦波",
      "③ 编码与词向量相加作为模型输入"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "输入词向量",
        "生成位置编码",
        "相加得到输入表示"
      ],
      "frames": [
        {
          "s": 0,
          "note": "输入词向量被拆分成不同的位置"
        },
        {
          "s": 1,
          "note": "每个位置用正弦和余弦函数生成编码"
        },
        {
          "s": 2,
          "note": "位置编码与词向量相加作为模型输入"
        }
      ]
    },
    "interviewQ": [
      "位置编码和自注意力机制有什么关系？",
      "如何生成位置编码？"
    ],
    "keywords": [
      "位置编码",
      "正弦波",
      "余弦波"
    ],
    "scene": [
      "在机器翻译任务中，模型能正确理解句子的顺序",
      "在文本生成任务中，模型能保持语义的连贯性"
    ],
    "tags": [
      "Transformer",
      "位置编码",
      "自然语言处理"
    ],
    "related": []
  },
  {
    "id": "ai-lora-low-rank-micro-tuning",
    "domain": "AI工程",
    "category": "work",
    "subject": "ai",
    "topicPath": [
      "AI工程",
      "LoRA 低秩微调原理"
    ],
    "title": "LoRA 低秩微调是怎么工作的？",
    "oneLine": "LoRA通过低秩矩阵更新实现高效的微调。",
    "analogy": "用少量的颜料在画布上进行局部上色。",
    "why": "解决传统微调需要大量计算资源的问题。",
    "mechanism": [
      "① 在模型权重矩阵中插入低秩矩阵",
      "② 仅训练低秩矩阵的参数",
      "③ 保持原始权重不变，仅更新低秩矩阵"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "原始权重矩阵",
        "插入低秩矩阵",
        "仅训练低秩矩阵"
      ],
      "frames": [
        {
          "s": 0,
          "note": "原始权重矩阵保持不变"
        },
        {
          "s": 1,
          "note": "在权重矩阵中插入低秩矩阵"
        },
        {
          "s": 2,
          "note": "仅训练低秩矩阵的参数"
        }
      ]
    },
    "interviewQ": [
      "LoRA和传统微调有什么区别？",
      "如何选择低秩矩阵的秩？"
    ],
    "keywords": [
      "LoRA",
      "低秩矩阵",
      "微调"
    ],
    "scene": [
      "在部署模型时，LoRA能有效节省计算资源",
      "在小数据集上，LoRA能实现快速微调"
    ],
    "tags": [
      "微调",
      "LoRA",
      "模型优化"
    ],
    "related": []
  },
  {
    "id": "ai-position-encoding",
    "domain": "AI工程",
    "category": "work",
    "subject": "ai",
    "topicPath": [
      "AI工程",
      "位置编码的作用"
    ],
    "title": "位置编码在Transformer中有什么作用？",
    "oneLine": "位置编码赋予模型对序列中元素位置信息的理解能力。",
    "analogy": "在快递分拣中，位置编码帮助系统确定包裹的正确位置。",
    "why": "解决Transformer无法区分序列顺序的问题，提升模型的上下文理解能力。",
    "mechanism": [
      "① 在输入嵌入向量中加入位置信息。",
      "② 位置信息与输入向量相加，形成位置编码。",
      "③ 位置编码帮助模型理解元素在序列中的相对位置。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "输入嵌入",
        "位置编码",
        "合并"
      ],
      "frames": [
        {
          "s": 0,
          "note": "输入序列被转换为嵌入向量。"
        },
        {
          "s": 1,
          "note": "位置编码被添加到嵌入向量中。"
        },
        {
          "s": 2,
          "note": "位置编码与嵌入向量相加，形成最终输入。"
        }
      ]
    },
    "interviewQ": [
      "位置编码有哪些常见的实现方式？",
      "位置编码如何影响模型的性能？"
    ],
    "keywords": [
      "位置编码",
      "序列位置",
      "嵌入向量",
      "Transformer"
    ],
    "scene": [
      "在机器翻译任务中，位置编码有助于模型理解句子的结构。",
      "在文本生成任务中，位置编码有助于模型生成连贯的文本。"
    ],
    "tags": [
      "Transformer",
      "位置编码",
      "NLP"
    ],
    "related": []
  },
  {
    "id": "ai-lora-low-rank",
    "domain": "AI工程",
    "category": "work",
    "subject": "ai",
    "topicPath": [
      "AI工程",
      "LoRA 低秩微调原理"
    ],
    "title": "LoRA 低秩微调的原理是什么？",
    "oneLine": "LoRA 通过添加低秩矩阵来微调大模型，减少计算资源消耗。",
    "analogy": "在快递分拣中，LoRA 像一个小型分拣站，只处理关键的包裹。",
    "why": "解决大模型微调时参数量过大、训练成本高的问题。",
    "mechanism": [
      "① 在大模型的权重矩阵中添加低秩矩阵。",
      "② 低秩矩阵的参数数量远小于原始权重矩阵。",
      "③ 微调过程中只更新低秩矩阵，减少计算量。"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "原始权重",
        "低秩矩阵",
        "微调"
      ],
      "frames": [
        {
          "s": 0,
          "note": "大模型的权重矩阵被拆分为低秩矩阵。"
        },
        {
          "s": 1,
          "note": "低秩矩阵被添加到模型中。"
        },
        {
          "s": 2,
          "note": "微调过程中只更新低秩矩阵。"
        }
      ]
    },
    "interviewQ": [
      "LoRA 与传统微调方法有哪些区别？",
      "LoRA 如何影响模型的性能？"
    ],
    "keywords": [
      "LoRA",
      "低秩矩阵",
      "微调",
      "大模型"
    ],
    "scene": [
      "在大模型微调任务中，LoRA 能显著减少训练时间和资源消耗。",
      "在模型部署时，LoRA 可以提高推理速度并降低计算成本。"
    ],
    "tags": [
      "LoRA",
      "微调",
      "大模型"
    ],
    "related": []
  }
];

if (typeof module !== "undefined" && module.exports) { module.exports = CARDS_AI; }
