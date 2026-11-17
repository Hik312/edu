# -*- coding: utf-8 -*-
"""FastAPI 后端启动入口。在 study/ 目录下执行：

    python back_study/run.py                # http://127.0.0.1:8080
    python back_study/run.py 8099           # 换端口
    python back_study/run.py 8080 --lan     # 手机同 WiFi 访问（绑 0.0.0.0）
    python back_study/run.py 8080 --reload  # 改代码自动重启（开发用）

也可以先 cd 进 back_study 再 `python run.py`，两种都行。

为什么不直接 `uvicorn app.main:app`：
    启动横幅要打印「卡片多少张 / AI 通不通 / 手机该访问哪个 IP」——
    这几行是排查时的第一手信息，还得打印在 uvicorn 那几行之后才看得清。
    端口和 --lan 靠环境变量递给 app/main.py 的 lifespan，
    因为 --reload 会重启子进程，函数参数传不过去、环境变量能。
"""
import os
import sys

# 1. `__file__`：Python 内置变量，保存**当前脚本文件的路径字符串**（只是文本，不会读文件内容）
# 2. `os.path.abspath(path)`：把路径转为绝对路径，**纯字符串运算**，只会解析路径格式；不打开、不读取文件
# 3. `os.path.dirname(path)`：**截取路径字符串，去掉最后一段**，返回目录部分。
#    - 输入字符串：`/a/b/c/run.py`
#    - 输出字符串：`/a/b/c`
HERE = os.path.dirname(os.path.abspath(__file__))        # back_study/
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# 钉住工作目录：uvicorn 的 --reload 会另起子进程，靠 cwd 找 'app.main'。
# 这里所有路径都是从 __file__ 推出来的绝对路径，chdir 不影响任何东西。
if os.getcwd() != HERE:
    os.chdir(HERE)


def main(argv):
    # 输出重定向到文件时 Python 默认块缓冲，启动横幅会卡在缓冲区里看不见 ——
    # 正是要排查「服务到底起没起」的时候最需要那几行，所以强制行缓冲。
    try:
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    except Exception:
        pass

    lan = '--lan' in argv
    reload_ = '--reload' in argv
    port = 8080
    for a in argv:
        if a.isdigit():
            port = int(a)

    try:
        import uvicorn
    except ImportError:
        print('缺依赖：FastAPI / uvicorn / PyJWT 还没装。')
        print()
        print('  装一次就够：pip install -r back_study/requirements.txt')
        print('  以前有个零依赖版 server.py 能绕开这一步，'
              '2026-09-26 已经移除 —— 鉴权改用 PyJWT 后它名不副实了。')
        return 1

    os.environ['CARDS_PORT'] = str(port)
    os.environ['CARDS_LAN'] = '1' if lan else '0'

    uvicorn.run(
        'app.main:app',
        host='0.0.0.0' if lan else '127.0.0.1',
        port=port,
        reload=reload_,
        log_level='info',
        # 关掉 uvicorn 自带的访问日志，改用 main.py 里那个「只记 /api/」的 ——
        # 一屏几十个静态资源请求会把真正要看的 API 错误埋掉
        access_log=False,
    )
    return 0
    

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
