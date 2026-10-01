# -*- coding: utf-8 -*-
"""AI Agent 路由 —— 把 back_study/agent/ 那套（LangGraph + 本地 Ollama）接到 HTTP 上。

**为什么整份文件的 import 都在函数内部。**
langchain 全家桶 import 一次要 2-3 秒。这个模块是 main.py 在启动时
**模块级**注册的，所以只要在文件顶部写 `from agent import runtime`，
每个请求都还没来，后端冷启动就先替 AI 多等 3 秒 —— 而多数请求根本不碰 AI。
延迟导入让「没装 langchain 也能正常起服务」这件事继续成立。

**为什么端点是 async def，而不是本项目其他路由那样的同步 def。**
项目里其他路由写同步 def，是因为它们只做毫秒级的 db 读写；
同步 def 会被 FastAPI 丢进线程池，短请求没问题。
但这里的调用是**几十秒**量级（本地 8B 模型实测 20-30 秒），
线程池默认只有 40 个线程 —— 几个并发就把池子占满，连 `/api/health` 都排不上队。
所以这里用 async def + `asyncio.to_thread()`：把阻塞调用挪出事件循环，
既不堵事件循环（直接写 async 里调同步 IO 会堵死），也不占线程池槽位。

**`/api/agent/status` 返回 ok:false 是正常状态，不是故障**
—— 和 `/api/llm/status` 一个道理：AI 是可选增强，HTTP 仍然返 200，
前端据此把 AI 那一块换成提示文字，其余功能照常。
"""
import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..deps import current_user
from ..schemas import AgentAskIn, AgentAskOut, AgentProfileIn

router = APIRouter(prefix='/api', tags=['AI Agent'])

MISSING = ('AI Agent 没装。装一次就够：'
           'pip install langgraph langchain langchain-ollama')


def _runtime():
    """延迟导入执行层。没装依赖就给 503 + 能动手的提示，别抛裸 ImportError。"""
    try:
        from agent.qa import runtime
    except ImportError as e:
        raise HTTPException(503, '%s（%s）' % (MISSING, e))
    return runtime


def _model():
    """延迟导入模型工厂（探活端点用，同样不该在启动时拉起依赖）。"""
    try:
        from agent import model
    except ImportError as e:
        raise HTTPException(503, '%s（%s）' % (MISSING, e))
    return model


@router.get('/agent/status', summary='AI Agent 可用性')
def agent_status():
    """探活：Ollama 通不通、模型在不在、langchain 装没装。"""
    st = _model().status()
    st['ok'] = bool(st.get('ok')) and bool(st.get('agent'))
    return st                      # 注意：ok 可能是 false，但 HTTP 仍然是 200


def _hist(body: AgentAskIn):
    """历史消息 → runtime 认的形状（[{role, content}]）。只留 role/content，
    顺手把长度上限交给 runtime.trim_history —— 那里才是唯一裁剪点。"""
    return [{'role': m.role, 'content': m.content} for m in (body.history or [])]


def _prof(body: AgentAskIn, uid):
    """本次问答用哪份长期档案：请求里带了就用请求的，没带就用服务端存的。

    请求里带的优先，是为了让前端能在"这次换了个岗位试试"时临时覆盖，
    不用先写档案再问 —— 那会让每一次试岗位都污染用户的长期档案。"""
    if isinstance(body.profile, dict):
        p = body.profile
        if p.get('role') or p.get('topics') or p.get('weak'):
            return p
    try:
        import db
        return db.profile_of(uid)
    except Exception:
        return None


@router.post('/agent/ask', summary='问 agent 一句话', response_model=AgentAskOut)
async def agent_ask(body: AgentAskIn, user=Depends(current_user)):
    rt = _runtime()
    q = (body.question or '').strip()
    if not q:
        raise HTTPException(400, '问题不能为空')
    if body.mode not in ('flow', 'react'):
        raise HTTPException(400, 'mode 只能是 flow 或 react')
    hist = _hist(body)
    prof = _prof(body, user.get('id') if user else None)

    # 流式走 SSE，由 StreamingResponse 在线程池里驱动同步生成器，不堵事件循环
    if body.stream:
        return StreamingResponse(_sse(rt, q, hist, prof),
                                 media_type='text/event-stream')

    t0 = time.time()
    try:
        out = await asyncio.to_thread(rt.ask_full, q, body.mode, hist, prof)
        answer = out['answer']
        sources = out.get('sources') or []
        steps = out.get('steps')
    except RuntimeError as e:
        # no_model / ai_off 这类内部代号，转成人话
        raise HTTPException(502, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, 'agent 调用失败：%s' % e)

    return AgentAskOut(ok=True, answer=answer, mode=body.mode, sources=sources,
                       steps=steps, ms=int((time.time() - t0) * 1000))


def _sse(rt, question, hist=None, prof=None):
    """SSE 生成器。

    帧协议（前端 api/agent.js 按 event 名分流，**改动必须两边同步**）：
      无 event 名  = 正文增量，data 是一行文本（换行已转义）
      event: sources = 这次引用到的卡片 id，data 是 JSON 数组 —— 必须在 done
                  之前发，因为 react 模式要等生成完才抽得出来 id
      event: done    = 正文流结束，data 为空
      event: error   = 出错，data 是错误信息

    本地模型出字慢，20 秒空白基本等于「坏了」—— 流式是本地模型的必需补偿。
    这里只发文本增量，不做心跳：单次请求几十秒，不需要抗空闲断连。"""
    import json as _json
    box = {'sources': None}

    def on_sources(ids):
        box['sources'] = ids or []

    try:
        for piece in rt.stream_react(question, hist, prof, on_sources=on_sources):
            yield 'data: %s\n\n' % piece.replace('\n', '\\n')
        if box['sources'] is not None:
            yield 'event: sources\ndata: %s\n\n' % _json.dumps(box['sources'],
                                                               ensure_ascii=False)
        yield 'event: done\ndata: \n\n'
    except Exception as e:
        yield 'event: error\ndata: %s\n\n' % str(e).replace('\n', ' ')


# ---------------------------------------------------------------------------
# 长期档案（L3 记忆）：只有一份，跟着登录用户走
# ---------------------------------------------------------------------------
@router.get('/agent/profile', summary='取当前用户的长期档案')
def get_profile(user=Depends(current_user)):
    import db
    return {'ok': True, 'profile': db.profile_of(user.get('id') if user else None)}


@router.put('/agent/profile', summary='更新长期档案（合并写入）')
def put_profile(body: AgentProfileIn, user=Depends(current_user)):
    """★ `exclude_unset=True` 是必须的，不是风格问题。

    `AgentProfileIn` 的字段全是「没发 = None = 不动」，而 `save_profile`
    判的是 `if 'role' in patch`。不带 `exclude_unset` 时 `model_dump()`
    会把**没发的** role 一起序列化成 `role: None` 放进 patch → 被判为
    「用户要清空岗位」→ 档案里的目标岗位变成空串。

    真实现象：先在「今日路径」点了「存进我的档案」，再到「复习队列」
    点一下 ±5（只发 dailyTarget），岗位就没了。属静默丢用户数据。
    """
    import db
    uid = user.get('id') if user else None
    if uid is None:
        raise HTTPException(401, '未登录')
    p = db.save_profile(uid, body.model_dump(exclude_unset=True))
    return {'ok': True, 'profile': p}
