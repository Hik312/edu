"""把 docs.py 的 SSE 队列模式抽成一个可复用的工具。

★ 为什么要抽出来：`/docs/{did}/ask`（问答）和 `/docs/{did}/translate/run`
  （翻译）都需要「后台线程跑阻塞任务 + 主生成器转发事件」这个结构。
  两份拷贝一旦有一份改了心跳间隔或漏了线程 daemon，
  表现是「翻译页面挂着不动」而极难联想到是 SSE 实现的问题。

用起来：
    return sse_json_stream(worker, first=[('total', {...})])
worker 是一个在后台线程里跑的函数，它调用 emit('seg', {...}) 推帧。
"""
import json
import threading

from fastapi.responses import StreamingResponse


def sse_json_stream(worker, first=None, poll=0.12):
    """把 worker() 的 emit() 回调变成 SSE 响应。

    worker 签名：worker(emit)，emit(kind, payload)
      kind == 'data' 时按文本增量发（换行转义成 \\n）
      其余 kind 发成 `event: <kind>` 帧

    ★ worker 必须**同步阻塞**地跑在一个线程里 —— 不能在生成器里
      直接调用它（生成器里 yield 和阻塞调用互斥）。
    """
    queue = []
    lock = threading.Lock()

    def emit(kind, payload):
        with lock:
            queue.append((kind, payload))

    def run():
        try:
            worker(emit)
        except Exception as e:
            with lock:
                queue.append(('event: error',
                              {'msg': str(e).replace('\n', ' ')[:300]}))

    th = threading.Thread(target=run, daemon=True)
    th.start()

    def gen():
        for kind, payload in (first or []):
            yield _frame(kind, payload)
        while th.is_alive() or queue:
            with lock:
                batch = list(queue)
                queue.clear()
            for kind, payload in batch:
                yield _frame(kind, payload)
            # ★ 这个 join 不只是"防空转"：它同时是**心跳**。
            #   翻译一段要 3~8 秒（甚至更久），中间没有帧的话
            #   nginx / 浏览器在 60s 空闲后会把连接掐掉，
            #   前端表现为「翻到一半就停了」，而后端日志一切正常。
            #   顺带它让循环不至于空转 CPU。
            if th.is_alive():
                th.join(poll)

    return StreamingResponse(gen(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-store',
                                      'X-Accel-Buffering': 'no'})


def _frame(kind, payload):
    if kind == 'data':
        return 'data: %s\n\n' % str(payload).replace('\n', '\\n')
    if isinstance(payload, str):
        return 'event: %s\ndata: %s\n\n' % (kind, payload)
    return 'event: %s\ndata: %s\n\n' % (kind,
                                       json.dumps(payload, ensure_ascii=False))