# -*- coding: utf-8 -*-
"""命令行入口 —— 先看这 100 行，整个 agent 层就通了。

跑法（在 study/ 目录下）：

    .venv/Scripts/python.exe back_study/agent/demo.py --status
    .venv/Scripts/python.exe back_study/agent/demo.py "SpringBoot 自动装配是怎么跑起来的"
    .venv/Scripts/python.exe back_study/agent/demo.py --mode react "今天该复习什么"
    .venv/Scripts/python.exe back_study/agent/demo.py --stream "什么是 RAG"
    .venv/Scripts/python.exe back_study/agent/demo.py --chat        # 连续对话（带记忆）

第一次跑慢是正常的：Ollama 要把 5GB 模型加载进显存，之后 keep_alive 期间都很快。
"""
import os
import sys
import time

# 让 `python back_study/agent/qa/demo.py` 这种直接跑法也能 import 到 agent 包。
# 少了这段，包内相对导入会报 "attempted relative import with no known parent package"。
# dirname 两次：demo.py → qa/ → agent/，再向上一层才是 back_study/。
_HERE = os.path.dirname(os.path.abspath(__file__))          # .../back_study/agent/qa
_BACK = os.path.dirname(os.path.dirname(_HERE))             # .../back_study
if _BACK not in sys.path:
    sys.path.insert(0, _BACK)

from agent import model as M                     # noqa: E402


def show_status():
    """环境探活：Ollama 通不通、模型在不在、langchain 装没装。"""
    st = M.status()
    print('AI 状态：%s' % ('可用' if st.get('ok') else '不可用'))
    print('  通道    %s' % st.get('provider'))
    print('  模型    %s' % (st.get('model') or '-'))
    if st.get('models'):
        print('  已装    %s' % ', '.join(st['models']))
    print('  说明    %s' % (st.get('msg') or ''))
    if not st.get('agent'):
        print('  agent层 依赖没装：%s' % st.get('agentMsg'))
    return bool(st.get('ok')) and bool(st.get('agent'))


def _print_step(ev):
    """把 agent 的中间过程打出来 —— 调试全靠这个。"""
    if ev['type'] == 'tool_call':
        print('  → 调工具 %s(%s)' % (ev['name'], ev['args']))
    else:
        print('  ← %s' % ev['content'][:160].replace('\n', ' '))


def _run_flow(q):
    from agent.qa.runtime import ask
    return ask(q, 'flow')


def _run_react(q, history=None):
    from agent.qa.runtime import run_react
    out = run_react(q, history=history, on_step=_print_step)
    return out['answer'], out['history']


def _run_stream(q):
    from agent.qa.runtime import stream_react
    print('答（流式）：', end='', flush=True)
    buf = []
    t0 = time.time()
    for piece in stream_react(q):
        buf.append(piece)
        print(piece, end='', flush=True)
    print('\n  —— %.1fs' % (time.time() - t0))
    return ''.join(buf)


def main(argv):
    if '--status' in argv or not argv:
        return 0 if show_status() else 1
    if not show_status():
        print('\n环境不通，先按上面的提示处理。')
        return 1

    mode = 'react' if '--mode' in argv and 'react' in argv else 'flow'
    words = [a for a in argv
             if not a.startswith('--') and a not in ('react', 'flow')]
    question = ' '.join(words).strip()

    if '--chat' in argv:
        print('\n连续对话（react 模式，带上下文；空行退出）\n')
        history = None
        while True:
            try:
                q = input('你> ').strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not q:
                break
            t0 = time.time()
            ans, history = _run_react(q, history)
            print('AI（%.1fs）：%s\n' % (time.time() - t0, ans))
        return 0

    if not question:
        print('给个问题，比如：demo.py "什么是数据库索引"')
        return 1

    print('\n问：%s' % question)
    t0 = time.time()
    try:
        if '--stream' in argv:
            _run_stream(question)
        elif mode == 'react':
            _run_react(question)
            print('  —— %.1fs' % (time.time() - t0))
        else:
            # 先跑完再取时间。写成 print(... % (time.time()-t0, _run_flow(q))) 会先算
            # 左边那个减法（元组从左到右求值），结果永远显示 0.0s。
            ans = _run_flow(question)
            print('答（%.1fs，flow 模式）：\n%s' % (time.time() - t0, ans))
    except RuntimeError as e:
        print('失败：%s' % e)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
