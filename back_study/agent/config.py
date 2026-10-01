# -*- coding: utf-8 -*-
"""Agent 层的所有可调参数。改行为先来这里看一眼，不要去业务代码里翻 magic number。

每个都能用环境变量覆盖 —— 调参不想改代码（尤其是想对比两种配置的效果时）。
默认值是本机 qwen3:8b 实测下来的取舍，注释写了为什么是这个数。
"""
import os


def _env(name, default, cast=float):
    v = os.environ.get(name)
    if v is None or v == '':
        return default
    try:
        return cast(v)
    except ValueError:
        return default


# ---- 模型 ----
# 0.2 而不是 0：8B 模型在 temperature=0 下容易复读，0.2 既稳又不发散。
# 做抽取这类要确定结果的任务，调用方自己传 0。
TEMPERATURE = _env('AGENT_TEMPERATURE', 0.2)

# 上下文窗口。Ollama 默认只有几千，塞长文档会被**静默截断** ——
# 不报错，就是少了后半段，极难查。qwen3:8b 实际能撑 40960，这里取 8192
# 是兼顾小显存机器的折中，喂整本书再调大。
NUM_CTX = int(_env('AGENT_NUM_CTX', 8192))

# 单次生成上限。2048 而不是原来的 1024 —— 回答放开到「300~600 字讲透」之后
# （见 qa/nodes.py ANSWER_SYS），600 个汉字约 900 token，1024 会把最后一段
# 从半句话切掉。max 只是上限，答完就停，调大不多花时间。
NUM_PREDICT = int(_env('AGENT_NUM_PREDICT', 2048))

# ---- 编排 ----
# 自检没过时最多重来几次。本地 8B 的自检能力有限，重太多次只是在烧时间。
MAX_TRIES = int(_env('AGENT_MAX_TRIES', 2))

# ReAct 的步数上限。小模型偶尔会陷入「调同一个工具 → 不满意 → 再调」的循环，
# 不设上限能跑到天荒地老。这是**必须**的保险，不是优化项。
RECURSION_LIMIT = int(_env('AGENT_RECURSION_LIMIT', 12))

# ---- 记忆（L1 会话内多轮）----
# 带进下一轮的历史字符预算。超了就从**最旧**开始丢，但至少留最近
# HISTORY_KEEP 轮 —— 留着最近的才有"记得上一句"的效果，全丢等于没记忆。
#
# 为什么不做 LLM 摘要压缩：本地 8B 一次调用 20 秒，为了省上下文多花 20 秒，
# 用户等的是回答不是摘要。等上了云端大模型再考虑（注释留个记号）。
HISTORY_MAX_CHARS = int(_env('AGENT_HISTORY_MAX_CHARS', 1500))
HISTORY_KEEP = int(_env('AGENT_HISTORY_KEEP', 2))

# ---- 检索 ----
# 检索取几张卡塞进上下文。3 张是实测甜点：1 张容易漏，5 张以上 8B 开始顾此失彼。
TOP_K = int(_env('AGENT_TOP_K', 3))

# search_cards 工具一次返回几张。工具返回是给模型看的，太长它反而抓不住重点。
SEARCH_LIMIT = int(_env('AGENT_SEARCH_LIMIT', 6))

# 检索策略：hybrid（向量为主+关键词兜底）/ vector / keyword。
# 默认 hybrid：即使本地没装 embedding 模型，也会自动退化成纯关键词，不会报错。
# 想纯向量就设 AGENT_RETRIEVER=vector；想纯关键词设 keyword。
RETRIEVER = os.environ.get('AGENT_RETRIEVER', 'hybrid')

# 向量权重（融合时向量分占多少，关键词分占 1-它）。0.7 = 向量为主。
VECTOR_WEIGHT = _env('AGENT_VECTOR_WEIGHT', 0.7)

# 本地 Ollama 的 embedding 模型名。没拉这个模型时 VectorRetriever 自动退化（返回空）。
EMBED_MODEL = os.environ.get('AGENT_EMBED_MODEL', 'nomic-embed-text')
