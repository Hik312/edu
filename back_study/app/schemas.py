# -*- coding: utf-8 -*-
"""请求体模型。

两条原则：

1. **字段名一律 camelCase**，与 `data/*.js` 的卡片契约、index.html 发过来的 JSON
   逐字对齐。这里不收 snake_case，免得后端多一层「自动转换」的魔法，
   出问题时排查还得先猜字段名被谁改过。
2. **不在这里重复业务校验**。哪些字段必填、scene 至少 2 条，唯一真相是
   `core/importer.py:validate()` —— 网页、导入两条路都走它。
   这里只做「类型对不对、缺没缺参数」这一层，把 422 变成 400 由 main.py 统一翻译。
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Loose(BaseModel):
    """允许携带未知字段的基类。

    `extra='allow'` 不是偷懒：卡片/草稿上有一批内部字段（`_custom`、`_draft`、
    `_from`、`_meta`）由数据层自己维护，前端也可能带上别的键。
    用严格模型会把它们悄悄吃掉 —— 那才是真的破坏契约。
    """
    model_config = ConfigDict(extra='allow')


# ---------- 卡片 ----------
class CardIn(Loose):
    id: Optional[str] = Field(None, description='唯一 id，内置卡在 data/*.js 里改')
    domain: Optional[str] = Field(None, description='领域，如 工作 / 考研')
    category: Optional[str] = Field(None, description='分类树里的一级 id，必须在 data/catalog.js 中存在')
    subject: Optional[str] = Field(None, description='分类树里的二级 id')
    topicPath: Optional[List[str]] = Field(None, description='主题路径，用于图谱分层')
    title: Optional[str] = None
    oneLine: Optional[str] = Field(None, description='一句话说清是什么')
    analogy: Optional[str] = Field(None, description='类比（不许出现技术词，越像生活越好）')
    why: Optional[str] = None
    mechanism: Optional[List[str]] = Field(None, description='原理拆解，分步骤')
    diagram: Optional[Dict[str, Any]] = Field(None, description='pipeline / state-machine / snapshot / arch 四选一')
    interviewQ: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    scene: Optional[List[str]] = Field(None, description='真实场景，硬规矩：至少 2 条')
    tags: Optional[List[str]] = None
    related: Optional[List[Dict[str, Any]]] = Field(
        None, description='关联卡：[{id, kind: prereq|extends|compare, note}]，note 必填')
    images: Optional[List[Dict[str, Any]]] = Field(
        None, description='配图：[{name, src, caption}]，src 是 /api/media/... 直链')


class ProgressIn(BaseModel):
    level: int = Field(..., description='1 = 不会，2 = 模糊，3 = 会')


class PickIn(BaseModel):
    """今日自选复习清单：整体覆盖式 PUT，ids 用真实卡 id。

    不存在的 id 由 db.set_today_pick 过滤（前端可能拿着已删卡的清单提交），
    这层不校验 —— 校验的唯一真相在数据层，schema 只管类型。
    """
    ids: List[str] = Field(..., max_length=100, description='今日要刷的卡 id，上限 100')


class NoteIn(Loose):
    id: Optional[str] = Field(None, description='带 id 就是更新，不带就是新建')
    title: Optional[str] = None
    body: Optional[str] = None
    category: Optional[str] = None
    subject: Optional[str] = None
    cardId: Optional[str] = Field(None, description='挂在哪张卡下面（卡片底部的「我的理解」）')
    tags: Optional[List[str]] = None


# ---------- 导入 ----------
class ImportTextIn(Loose):
    text: str = Field(..., description='要切分的原文')
    useLLM: bool = Field(False, description='true 时优先走大模型抽取，失败自动退回本地规则')
    domain: Optional[str] = None
    category: Optional[str] = None
    subject: Optional[str] = None
    topicPath: Optional[List[str]] = None


class DocImportIn(Loose):
    text: Optional[str] = Field(None, description='纯文本内容（与 dataB64 二选一）')
    dataB64: Optional[str] = Field(None, description='文件 base64（md/txt/pdf）')
    filename: Optional[str] = Field(None, description='文件名，用来判断是不是 PDF')
    title: Optional[str] = Field(None, description='不给就从文中第一个标题推')
    category: Optional[str] = None
    subject: Optional[str] = None
    domain: Optional[str] = None


class DocRenameIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=60, description='新的卡片组名（即文档标题）')


class DraftPatch(Loose):
    scene: Optional[List[str]] = Field(None, description='补齐 2 条场景后才能入库')
    keywords: Optional[List[str]] = None
    title: Optional[str] = None
    oneLine: Optional[str] = None
    analogy: Optional[str] = None
    why: Optional[str] = None
    mechanism: Optional[List[str]] = None
    interviewQ: Optional[List[str]] = None


class PublishIn(BaseModel):
    id: str = Field(..., description='草稿 id')


# ---------- AI 精读 ----------
class EnrichIn(Loose):
    docId: Optional[str] = Field(None, description='给了就按文档章节精读，结果逐章落盘')
    index: Optional[int] = Field(None, description='单章下标')
    indexes: Optional[List[int]] = Field(None, description='多章下标；都不给则整篇')
    title: Optional[str] = Field(None, description='不给 docId 时直接精读一段：标题')
    text: Optional[str] = Field(None, description='不给 docId 时直接精读一段：正文')
    model: Optional[str] = Field(None, description='指定模型，默认取服务端挑好的那个')
    selfCheck: bool = Field(True, description='类比里混进技术词就自动重问一次')
    batch: int = Field(4, description='批量精读时一次送几章（批量会串味，前端默认逐章）')


class ToCardIn(BaseModel):
    docId: str
    index: int = Field(..., description='章节下标')
    ai: Optional[Dict[str, Any]] = Field(None, description='覆盖章节上已存的精读结果')


class FillIn(BaseModel):
    """生成模块「AI 补齐」：整张草稿通读一遍，缺的补上、薄的重写后落回草稿池。"""
    draftId: str
    model: Optional[str] = Field(None, description='指定模型，默认取服务端挑好的那个')


# ---------- cards Agent（文档 → 卡片，LangGraph）----------
class CardsStructureIn(BaseModel):
    """structure 阶段：LLM 看规则初切的章节清单，定切分点后重切。"""
    docId: str


class CardsChapterIn(BaseModel):
    """chapter 阶段：一章跑完整张图（图注 → 生成 → 对齐自检），落一张草稿。

    幂等：同章草稿已存在就跳过（断点续跑）；force=true 覆盖重生成。"""
    docId: str
    index: int = Field(..., description='章节下标')
    force: bool = Field(False, description='已有草稿也重新生成（覆盖）')


class CardsParseIn(BaseModel):
    """parse 阶段：内容解析 —— 规则预判 + LLM 判定每章有用/没用，报告落库。"""
    docId: str


class CardsParseKeepsIn(BaseModel):
    """保存解析报告上的勾选调整（出卡前的确认环节）。"""
    docId: str
    keeps: Dict[str, bool] = Field(..., description='章节下标（字符串键）→ 是否保留')


# ---------- AI Agent（back_study/agent/，可选依赖）----------
class ChatTurn(BaseModel):
    """一轮对话的一条消息。role 只认 user / assistant —— 多轮历史由前端持有，
    每次随问题一起发过来，后端不存会话（存了就要考虑过期、清理、多端同步）。"""
    role: str = Field(..., description='user 或 assistant')
    content: str = Field(..., description='这一条的正文')


class AgentAskIn(BaseModel):
    question: str = Field(..., description='要问什么')
    mode: str = Field('flow', description=('flow = 固定流程（检索→回答→自检，答得快、不编）'
                                           '；react = 模型自己决定查什么工具（能答"我有几张卡"这类）'))
    stream: bool = Field(False, description='流式返回（SSE）。本地模型出字慢，建议前端开')
    history: List[ChatTurn] = Field(
        default_factory=list,
        description='本次会话的既往对话（L1 记忆）。超预算后端自动裁剪，前端不用管')
    profile: Optional[Dict[str, Any]] = Field(
        None, description=('长期档案（L3 记忆）：{role:目标岗位, topics:[常问主题], '
                           'weak:[薄弱卡id]}。不传就用服务端存的那份'))
    webSearch: bool = Field(
        False, description=('联网搜索开关：true 时资料追加【网页】搜索结果'
                            '（Bing RSS，免 key）；搜不到不影响回答'))


class AgentAskOut(BaseModel):
    ok: bool = True
    answer: str = Field('', description='回答正文')
    mode: str = Field('', description='实际走的模式')
    sources: List[str] = Field(
        default_factory=list,
        description='这次回答引用了哪些卡片 id（溯源用，前端可点击跳转到对应卡片）')
    steps: Optional[List[Dict[str, Any]]] = Field(
        None, description='react 模式下 agent 的中间过程（调了哪些工具、返回了什么）')
    model: Optional[str] = Field(None, description='用的哪个模型')
    ms: Optional[int] = Field(None, description='耗时毫秒')


class AgentProfileIn(BaseModel):
    """长期档案的写入体。字段全可选：只改每日目标就只发 dailyTarget。

    列表字段用 `Optional[...] = None` 而不是 `default_factory=list` 是刻意的 ——
    合并语义要能区分「没发这个字段」（None，不动）和「发了空数组」（清空）。
    topics/weak 仍用默认空列表：它们是追加合并，空数组等于没改。
    """
    role: Optional[str] = Field(None, description='目标岗位（如 "Java+Python Agent 开发"）')
    topics: List[str] = Field(default_factory=list, description='常问主题（自动积累）')
    weak: List[str] = Field(default_factory=list, description='薄弱卡片 id')
    dailyTarget: Optional[int] = Field(
        None, description='每天学几张（0 = 从没设过，前端按默认 20 显示）')
    directions: Optional[List[str]] = Field(
        None, description='选中的学习方向 id（data/directions.js）。null = 不动，[] = 清空')
