# -*- coding: utf-8 -*-
"""只读的结构类接口：能不能用、有哪些分类、知识框架长什么样、图谱怎么连。

写同步 `def` 而不是 `async def` 是有意的：db 层的卡片加载是同步文件 IO，
在 async 函数里直接跑会卡住事件循环（整个服务一起等）。FastAPI 见到普通 `def`
会自动丢进线程池，并发上限由 anyio 管 —— 一个慢请求不会打垮别的请求。
**别把端点改成 `async def`**，那会让所有请求排在同一条事件循环上。
"""
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

import algo
import db
import store as store_pkg
from ...deps import current_user

router = APIRouter(prefix='/api', tags=['结构'])

# ★ 哪些端点要登录、哪些不要，判据是**响应里有没有个人数据**，不是"读还是写"：
#
#   要登录：/outline、/graph、/graph/neighbors、/plan
#     —— 它们把每张卡的 level / 掌握度一起吐出来（来自 progress），
#        是个人复习状态，不是公共内容。
#   不要登录：/health、/catalog、/roles、/directions
#     —— 纯配置与存活探测。data/catalog.js 这类文件本身就在 git 里、
#        没有任何秘密；留公开是为了让「后端活着吗」和「未登录时整站
#        结构还渲染得出来吗」这两件事不需要凭据就能验。
#   /storage 含库名/主机/账号，属于踩点信息 → 要登录。


@router.get('/health', summary='健康探测')
def health():
    """前端启动时先打这个：通了就走 API，不通就整站回退 localStorage。

    `framework` 字段恒为 `fastapi`。它是给 check.js 的冒烟断言用的：
    「测到的确实是这个后端」比「请求没报错」更值得断言（端口撞上别的服务
    时会返回 200 但内容根本不是本项目）。

    `store` 字段是这次新增的：json / mysql。两个都是**正常状态**，
    不是故障指示 —— 数据库连不上时服务会回退到 json 并且照常工作，
    真正需要关注的是 `degraded` 有没有值（有值才是「你以为在用 MySQL，
    其实写进文件了」）。
    """
    st = store_pkg.get()
    return {
        'ok': True,
        'mode': 'server',
        'lang': 'python',
        'framework': 'fastapi',
        'store': st.name,
        'cards': len(db.all_cards()),
        'today': db.today_str(),
        'llm': bool(os.environ.get('LLM_API_KEY')),
    }


@router.get('/storage', summary='存储后端状态')
def storage(user=Depends(current_user)):
    """当前用的是哪个存储、库里有多少行、内置卡副本有没有过期。

    用途有两个：一是排查（「我明明改了 data/*.js，怎么接口还是旧的」→
    看 builtin.stale），二是让人确认数据库真的在工作，而不是
    服务回退到 JSON 了自己还不知道（看 degraded）。
    """
    return {'ok': True, 'storage': db.storage_info()}


@router.post('/storage/reprobe', summary='立刻重新探测存储后端（切回 MySQL）')
def storage_reprobe(user=Depends(current_user)):
    """不等 TTL，立刻重探一次 MySQL，起来了就切回去。

    自动复探（`store._maybe_reprobe`）已经覆盖了「等一个请求 + 最多 30 秒」
    这条路，这个端点补的是**立刻**那一段：MySQL 刚起、用户正盯着
    存储状态页看，不想干等下一次请求。

    返回 `restored` 明确告诉你切没切成功 —— 失败时 `storage.degraded`
    里是**这次**的新原因（可能和上次不同，比如从「连不上」变成「缺表」）。
    """
    ok, info = store_pkg.reprobe_now()
    return {'ok': True, 'restored': ok, 'storage': info}


@router.get('/catalog', summary='分类树')
def catalog():
    """一级分类 → 二级科目。改动 data/catalog.js 后前端导航跟着变。"""
    return {'ok': True, 'catalog': db.load_catalog()}


@router.get('/algo', summary='当前调度算法与可切换项')
def algo_status():
    """现在用哪个间隔调度算法算复习间隔，以及还有哪些可以切。

    为什么要暴露它：`ALGO` 是个配置项（`ALGO=fsrs` 就换算法），换掉之后
    **界面上完全看不出来** —— 用户看到的是同一批卡、同一套队列，
    但背后的间隔模型已经从 SM-2 变成 FSRS 了。算法是这个系统的核心竞争力，
    藏在配置文件里等于不存在。
    每个算法都带自己的 `efNote`（ef 这一列在它那儿代表什么），一并吐出来：
    sm2=难度因子 / fsrs=难度 D / hlr=记忆半衰期(天) / bkt=掌握度 p。

    判据仍是「响应里有没有个人数据」→ 这是纯配置，**不要登录**。
    """
    return {'ok': True, 'current': algo.get().describe(),
            'options': algo.describe_all(),
            # Load Balance 开关状态（algo/loadbalance.py，默认关）——
            # 改变了排期行为的配置必须看得见，跟算法本身同一原则
            'loadBalance': _loadbalance_cfg()}


def _loadbalance_cfg():
    try:
        import algo.loadbalance as loadbalance
        return loadbalance.config()
    except Exception as e:
        return {'enabled': False, 'window': 0, 'cap': None, 'error': str(e)[:120]}


@router.get('/roles', summary='目标岗位列表')
def roles():
    """预置岗位（data/roles.js）。只回目录，不含卡片 —— 对账走 /api/plan。"""
    return {'ok': True, 'roles': db.load_roles()}


@router.get('/directions', summary='学习方向预设')
def directions():
    """学习方向（data/directions.js）+ 每个方向能推出多少张卡。

    count 是现算的（67 张卡 × 十几个关键词，微秒级）：chips 上要显示「7」，
    用户一眼看出这个方向推不推得出东西 —— 库里还没有卡的方向不该让人白点。
    筛卡本身不在这儿：队列走 `/api/review/due?dirs=`，那边筛完才截断 limit。
    """
    cards = db.all_cards()
    # 单遍统计：与 /api/mini/home 共用 db.direction_counts，口径必须一致
    # （卡包页模块 chips 显示的「张数」和小程序首页的得对上，否则用户会困惑）。
    counts = db.direction_counts(cards)
    out = [dict(d, count=counts.get(d.get('id'), 0)) for d in db.load_directions()]
    return {'ok': True, 'directions': out}


@router.get('/plan', summary='岗位知识点地图')
def plan(role: Optional[str] = Query(None, description='预置岗位 id'),
         subjects: Optional[str] = Query(
             None, description='自定义科目组合，逗号分隔，如 java,ai,python'),
         user=Depends(current_user)):
    """岗位（或自定义科目组合）→ 按技能分组的卡片 + 覆盖缺口。

    自定义组合**不落库**：用完即走，用户勾的组合存在前端 localStorage。
    两个参数都不给、或 id 查不到 → 400/404，前端据此回选岗位的提示。
    """
    if not role and not subjects:
        raise HTTPException(400, '要给 role（预置岗位 id）或 subjects（科目组合）之一')
    p = db.role_plan(role_id=role or None, subjects=subjects or None,
                     user_id=user.get('id'))
    if p is None:
        raise HTTPException(404, '岗位不存在: %s' % (role or subjects))
    return {'ok': True, 'plan': p}


@router.get('/outline', summary='知识框架（MOC 树）')
def outline(category: Optional[str] = Query(None, description='只看某个一级分类'),
            subject: Optional[str] = Query(None, description='只看某个科目'),
            user=Depends(current_user)):
    return {'ok': True, 'tree': db.build_outline(category=category or None,
                                                 subject=subject or None,
                                                 user_id=user.get('id'))}


@router.get('/graph', summary='知识图谱')
def graph(category: Optional[str] = Query(None), subject: Optional[str] = Query(None),
          user=Depends(current_user)):
    """节点 + 边。层级边构成骨架，语义边来自卡片自己的 `related` 字段。"""
    return {'ok': True, 'graph': db.build_graph(category=category or None,
                                                subject=subject or None,
                                                user_id=user.get('id'))}


#: 节点 id 里带 '/'（章节节点是 'sub:work/ai'、'topic:ai/Agent/框架'），
#: 而路径参数 {cid} 默认不跨 '/' —— 请求会 404 掉、最后落到 SPA 回落，
#: 拿 dist/api/graph/neighbors/sub:work/ai 当静态文件找，
#: 在 Windows 上炸 WinError 123（文件名非法）。**点章节节点必坏**。
#: 改成 query 传参是唯一干净的解法（:path 转换器会让这一段吞掉所有后缀）。
@router.get('/graph/neighbors', summary='某节点的邻居')
def graph_neighbors(cid: str = Query(..., description='节点 id（含 / 原样传，别自己拼路径）'),
                    depth: int = Query(1, description='1~3，越深越慢'),
                    untilCards: bool = Query(False,
                                              description='展开到见到卡为止（点章节节点时必开）'),
                    user=Depends(current_user)):
    """图谱点开某个节点时用：「这个节点还牵着谁」。

    ★ until_cards 是给「章节节点」用的：层级是 subject → topic → … → card，
      卡挂的层数不固定，按跳数停会出现「满屏章节、一张卡都没有」。
    """
    nb = db.neighbors(cid, max(1, min(3, depth)), until_cards=bool(untilCards))
    if nb['center'] is None:
        raise HTTPException(404, '节点不存在: ' + cid)
    return {'ok': True, **nb}


# ---------- 图算法接口 ----------
#
# 上面三个是「图长什么样」，下面四个是「图算法算出了什么」。
# 分开是因为**消耗量级差一个数量级**：/graph 只是拼 dict（毫秒级），
# 而 PageRank + Louvain + Betweenness 三个加起来要跑 60 次幂迭代（0.4s）。
# 合成一个接口的话，页面每次切筛选都要重算 centrality，纯属浪费。
#
# `/graph/rank` 这个查表接口是缓存命中的（graph_raw 带 5 分钟 TTL +
# mtime 失效），所以详情页随时可以问，不占算力。

@router.get('/graph/insight', summary='图结构洞察（中心性 + 社区 + 体检）')
def graph_insight(category: Optional[str] = Query(None),
                  subject: Optional[str] = Query(None),
                  user=Depends(current_user)):
    """PageRank / Betweenness / Louvain 社区 + 连通性体检。

    要登录：返回的 betweenness、communities 虽不含个人数据，但它是
    整个图谱页的上下文，而图谱本身（/graph）带 level → 是个人数据。
    口径与 /graph 保持一致，不给「图是公共的、所以这个公开」的借口。
    """
    return db.graph_insight(category=category or None, subject=subject or None)


@router.get('/graph/community-summary', summary='社区摘要（AI 生成的「这是一块什么知识」）')
def graph_community_summary(category: Optional[str] = Query(None),
                            subject: Optional[str] = Query(None),
                            refresh: str = Query(
                                '', description='=1 强制重新生成（跑本地模型，几十秒量级）'),
                            user=Depends(current_user)):
    """对 louvain 分出的每个社区，用本地 LLM 写一段「这块知识讲什么」。

    要登录：社区成员里的卡片 id 与个人图谱页共用同一份上下文（口径随 /graph）。

    ★ AI 未启用 / 模型没吐对 JSON：200 + available:false + msg —— 摘要挂了
      不该让图谱页崩，前端拿 msg 渲一行提示即可。refresh=1 是显式按钮行为
      （同步等几十秒），普通 GET 永远只读缓存，命中即回、毫秒级。
    """
    try:
        return db.community_summary(category=category or None,
                                    subject=subject or None,
                                    refresh=(refresh == '1'))
    except Exception as e:
        # Ollama 超时 / 没起 / 云端断网：可见的降级状态，不当 500 抛给前端
        return {'ok': False, 'available': False, 'items': [],
                'msg': '摘要生成失败：%s' % str(e)[:160]}


@router.get('/graph/recommend', summary='图推荐（个性化 PageRank）')
def graph_recommend(limit: int = Query(8, ge=1, le=30),
                    category: Optional[str] = Query(None),
                    subject: Optional[str] = Query(None),
                    user=Depends(current_user)):
    """从「我不会的卡」往外推「该学什么」，每条带推荐理由。

    要登录：种子来自当前用户的 progress（level / nextAt），
    是纯个人数据。没登录时种子为空 → 退化成全局 PageRank → 推荐列表
    变成「全库最权威的卡」，那不是任何人的学习建议。
    """
    return db.graph_recommend(user_id=user.get('id'), limit=limit,
                              category=category or None, subject=subject or None)


@router.get('/graph/path', summary='两卡之间的最短学习路径')
def graph_path(src: str = Query(..., description='起点卡 id'),
               dst: str = Query(..., description='终点卡 id'),
               user=Depends(current_user)):
    """沿 prereq 找依赖链，**两个方向都试**，返回的 nodes 是**学习顺序**
    （基础在前、进阶在后）。找不到返回 200 + found=false（不是 404）。

    404 是「接口/资源不存在」，这里是「这两张卡之间没有依赖关系」——
    是正常答案的一种，客户端不该把它当错误弹窗。
    """
    return db.graph_path(src, dst)


#: 单次 rank 查询的 id 上限。
#:
#: 为什么是 500 而不是 50：老截断只按 data 文件顺序取前 50 个，图上其余
#: 卡片**拿不到排名** —— 节点大小退回 degree、侧栏 PageRank 一律显示「—」
#: （前端按可见卡 id 顺序发，等于前 50 张有排名、后面 300 多张没有）。
#: 上限只用来挡异常调用，因为 pagerank / betweenness / louvain 都是对**整图**
#: 算的（见 graph_rank_of），多给几个 id 不多花算力，只多几 KB 响应。
#: 前端按 150 个一片分片发：全量 414 个 id 逗号串就有 8343 字符，一次塞进
#: GET 查询串会顶到 8KB 请求头上限（部分代理/浏览器直接 431）。
MAX_RANK_IDS = 500


@router.get('/graph/rank', summary='批量查卡在图里的排名')
def graph_rank(ids: str = Query(..., description='逗号分隔的卡片 id'),
               user=Depends(current_user)):
    """给卡片详情页用：一次问清这几张卡的 PageRank 名次 / 社区归属。

    返回 {ranks: {...}, missing: [...]}。missing 是查不到的 id ——
    通常意味着前端拼错了 id，静默吞掉会让「排名不显示」这个现象
    无法定位。
    """
    want = [x.strip() for x in (ids or '').split(',') if x.strip()][:MAX_RANK_IDS]
    ranks, missing = db.graph_rank_of(want)
    return {'ok': True, 'ranks': ranks, 'missing': missing}
