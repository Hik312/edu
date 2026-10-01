# -*- coding: utf-8 -*-
"""只读的结构类接口：能不能用、有哪些分类、知识框架长什么样、图谱怎么连。

写同步 `def` 而不是 `async def` 是有意的：db 层的卡片加载是同步文件 IO，
在 async 函数里直接跑会卡住事件循环（整个服务一起等）。FastAPI 见到普通 `def`
会自动丢进线程池，并发上限由 anyio 管 —— 一个慢请求不会打垮别的请求。
**别把端点改成 `async def`**，那会让所有请求排在同一条事件循环上。
"""
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

import db
import store as store_pkg

router = APIRouter(prefix='/api', tags=['结构'])


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
def storage():
    """当前用的是哪个存储、库里有多少行、内置卡副本有没有过期。

    用途有两个：一是排查（「我明明改了 data/*.js，怎么接口还是旧的」→
    看 builtin.stale），二是让人确认数据库真的在工作，而不是
    服务回退到 JSON 了自己还不知道（看 degraded）。
    """
    return {'ok': True, 'storage': db.storage_info()}


@router.get('/catalog', summary='分类树')
def catalog():
    """一级分类 → 二级科目。改动 data/catalog.js 后前端导航跟着变。"""
    return {'ok': True, 'catalog': db.load_catalog()}


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
    out = []
    for d in db.load_directions():
        kws = [str(k) for k in (d.get('keywords') or [])]
        out.append(dict(d, count=sum(1 for c in cards if db.card_hit(c, kws))))
    return {'ok': True, 'directions': out}


@router.get('/plan', summary='岗位知识点地图')
def plan(role: Optional[str] = Query(None, description='预置岗位 id'),
         subjects: Optional[str] = Query(
             None, description='自定义科目组合，逗号分隔，如 java,ai,python')):
    """岗位（或自定义科目组合）→ 按技能分组的卡片 + 覆盖缺口。

    自定义组合**不落库**：用完即走，用户勾的组合存在前端 localStorage。
    两个参数都不给、或 id 查不到 → 400/404，前端据此回选岗位的提示。
    """
    if not role and not subjects:
        raise HTTPException(400, '要给 role（预置岗位 id）或 subjects（科目组合）之一')
    p = db.role_plan(role_id=role or None, subjects=subjects or None)
    if p is None:
        raise HTTPException(404, '岗位不存在: %s' % (role or subjects))
    return {'ok': True, 'plan': p}


@router.get('/outline', summary='知识框架（MOC 树）')
def outline(category: Optional[str] = Query(None, description='只看某个一级分类'),
            subject: Optional[str] = Query(None, description='只看某个科目')):
    return {'ok': True, 'tree': db.build_outline(category=category or None,
                                                 subject=subject or None)}


@router.get('/graph', summary='知识图谱')
def graph(category: Optional[str] = Query(None), subject: Optional[str] = Query(None)):
    """节点 + 边。层级边构成骨架，语义边来自卡片自己的 `related` 字段。"""
    return {'ok': True, 'graph': db.build_graph(category=category or None,
                                                subject=subject or None)}


@router.get('/graph/neighbors/{cid}', summary='某张卡的邻居')
def graph_neighbors(cid: str, depth: int = Query(1, description='1~3，越深越慢')):
    """图谱点开某张卡时用：「这张卡还牵着谁」。"""
    nb = db.neighbors(cid, max(1, min(3, depth)))
    if nb['center'] is None:
        raise HTTPException(404, '卡片不存在: ' + cid)
    return {'ok': True, **nb}
