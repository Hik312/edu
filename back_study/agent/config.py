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

# 单次生成上限。3072 而不是原来的 2048 —— 出卡提示词放开到「内容充足」
# （见 cards/nodes.py CARD_SYS，整卡目标 500+ 字，mechanism 6-8×110 字、
# interviewQ 带答案要点）之后，2048 会把 JSON 从中间切掉 → llm_not_json。
# max 只是上限，答完就停，调大不多花时间；预算 = prompt + 生成 <= NUM_CTX。
NUM_PREDICT = int(_env('AGENT_NUM_PREDICT', 3072))

# ---- 编排 ----
# 自检没过时最多重来几次。本地 8B 的自检能力有限，重太多次只是在烧时间。
MAX_TRIES = int(_env('AGENT_MAX_TRIES', 2))

# ---- cards Agent（文档 → 卡片）----
# 对齐自检的及格线：卡面文字与原文的字符二元组重合度（llm.align_score）。
# 0.08 比 enrich 的 0.10 略松 —— 卡片会用自己的话写类比/场景（本来就不该
# 和原文重合），压太死会把好卡也打回去。主要防的是「换章抄袭」这种硬伤。
CARDS_MIN_ALIGN = _env('AGENT_CARDS_MIN_ALIGN', 0.08)

# 一章正文喂给卡片生成的上限（字符）。超长的章不截会拖慢且容易被
# 模型开头带偏；6000 字对一章来说已经很富余。
CARDS_MAX_BODY = int(_env('AGENT_CARDS_MAX_BODY', 6000))

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

# ---- RRF 融合（混合检索用）----
# ★ 为什么把 min-max 加权换成 RRF（2026-10-09）：
#   min-max 是「分数线性插值」，但两路的分数量纲根本不同 ——
#   余弦相似度通常挤在 0.6~0.9 之间，而关键词子串分是整数计数（0~20）。
#   各自归一化后再加权，等于让「谁的分更分散谁说了算」：
#   实测查「RRF和Rerank」时，Redis 持久化那张卡被排到第 1（纯粹的关键词命中）。
#   RRF 只看**名次**不看分数，天然免疫量纲差异，是工业界的事实标准。
#   公式见 retrieval.py 的 rrf_fuse()。
RRF_K = float(_env('AGENT_RRF_K', 60))    # 惯例值 60：抑制头部排名的统治力

# ---- 重排（cross-encoder 精排）----
# 开关：默认开。关掉就退化成纯混合检索，行为与改动前一致。
# ★ 没有沿用 `_env(...)`：那个函数只处理数字（cast=float），布尔得单独读。
RERANK_ENABLED = os.environ.get('AGENT_RERANK', '1').strip().lower() not in (
    '0', 'false', 'no', 'off')

# ★ 候选数取 12，不是越多越好。实测本机 CPU（无 GPU）+ MAX_CHARS=150，
# 候选数 x batch_size 全组合跑下来（top1 在所有配置下都正确，
# 说明**候选数只影响时间、不影响精度**）：
#       8 对 → 1037ms      12 对 → 1718ms
#      16 对 → 2273ms      20 对 → 2895ms
#   12 是甜点：多召回 4 条只多花 0.7 秒，但覆盖的候选池大一圈。
#   要更快的机器上可以把 AGENT_RERANK_CANDIDATES 调大。
RERANK_CANDIDATES = int(_env('AGENT_RERANK_CANDIDATES', 12))

# 单次重排超时（毫秒）。超了就退回召回顺序 —— 慢一点能接受，界面卡住不行。
# 按实测 12 对约 1700ms，留 1.5 倍余量取 2500；
# 机器被别的进程占用时会变慢，超时保护就是为那种情况准备的。
RERANK_TIMEOUT_MS = int(_env('AGENT_RERANK_TIMEOUT_MS', 2500))


# ---- 重排模型路径（2026-11-15 配置化）----
# 以前硬编码 r'D:\models\bge-reranker-v2-m3' —— 换机器直接挂（评测遗留项）。
# 解析顺序与 ALGO/STORE 同款：环境变量 > config.local.json 的 "Rerank":{"path":...} > 默认。
def _rerank_path_default():
    try:
        import json
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'config.local.json')
        with open(p, 'r', encoding='utf-8') as f:
            seg = (json.load(f).get('Rerank') or {})
        v = str(seg.get('path') or '').strip()
        if v:
            return v
    except Exception:
        pass
    return r'D:\models\bge-reranker-v2-m3'


RERANK_PATH = os.environ.get('AGENT_RERANK_PATH', '').strip() or _rerank_path_default()

