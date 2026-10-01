# -*- coding: utf-8 -*-
"""FastAPI 应用装配。

分工很清楚：
    routers/  只写业务
    main.py   只收横切关注点 —— 请求体上限、缓存头、CORS、日志、
              异常统一翻译成 `{ok:false,msg}`、静态资源挂载、启动横幅

路由注册顺序不影响匹配（Starlette 按注册顺序匹配，但我们的路径没有歧义），
**静态挂载必须放最后** —— 它挂在 `/` 上会吃掉所有未匹配请求。
"""
import mimetypes
import os
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

import db       # noqa: E402  sys.path 由 app/__init__.py 挂好
import llm      # noqa: E402
import netinfo  # noqa: E402
import store as store_pkg   # noqa: E402  存储后端工厂（json / mysql）

# DATA_DIR 从包根取（它定义在 app/__init__.py），不从 config 转一手 ——
# config 那边为了让 main 能取到它，得写一行「自己用不到的 import」再导出，
# 那行会被 pyflakes 报假阳性，删了要到起服务才炸。少一层中转少一个坑。
from . import DATA_DIR
from .config import (API_DESC, API_TITLE, API_VERSION, DENY_PREFIX,
                     MAX_BODY, OPENAPI_TAGS, STATIC_DIR, WEB_DIST)
from .routers import ALL as ROUTERS

# Windows 上有的 Python 把 .js 认成 application/javascript，
# 少数浏览器对 service worker 的 MIME 挑得很死，显式钉住
mimetypes.add_type('application/manifest+json', '.webmanifest')
mimetypes.add_type('text/javascript', '.js')


class GuardedStatic(StaticFiles):
    """静态目录，但按 deny 前缀挡掉几段不给看。

    手机连着 WiFi 访问时，浏览器随手敲个 `/data/store/progress.json`
    就能把笔记正文拉走，这里顺手堵上。

    注意比较时转小写：Windows 文件系统大小写不敏感，`/DATA/STORE/` 照样能读到。
    """

    deny = DENY_PREFIX          # 类默认，挂载点可以按需覆盖

    async def get_response(self, path: str, scope) -> Response:
        rel = path.replace('\\', '/').lstrip('/').lower()
        if rel.startswith(tuple(p.lower() for p in self.deny)):
            return Response('404 Not Found', status_code=404, media_type='text/plain')
        return await super().get_response(path, scope)


class SpaStatic(GuardedStatic):
    """单页应用的静态目录：找不到的路径回落到 index.html。

    为什么必须这么干：Vue 用的是 history 模式，`/cards`、`/login` 这些路径
    **在服务器上并不存在对应的文件**，靠前端路由渲染。默认的 StaticFiles
    见到 `/cards` 直接 404 —— 用户手一刷新就白屏，而他刚从这一页点进去过。

    ⚠️ 注意 StaticFiles 表达 404 的方式是**抛 HTTPException**，不是返回一个
    状态码为 404 的 Response。所以这里必须 try/except —— 写成
    `resp = await super().get_response(...); if resp.status_code == 404`
    的话那行判断永远执行不到，页面照样 404，而且看不出哪里错了。

    两条例外，都不能回落成 HTML：

    1. `/api/...` 的 404 保持 404。回落的话前端拿到一坨 HTML，
       axios 报「JSON 解析失败」，排查方向直接跑偏到「后端挂了」。
    2. 带扩展名的路径（.js / .css / .png）保持 404。浏览器把 HTML 当 JS
       解析时报的错，跟真正的原因（文件没了）八竿子打不着，比 404 难查十倍。
    """

    async def get_response(self, path: str, scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as e:
            if e.status_code != 404:
                raise

        rel = (path or '').replace('\\', '/').lstrip('/')
        if rel.startswith('api/') or os.path.splitext(rel)[1]:
            raise StarletteHTTPException(404)

        try:
            return await super().get_response('index.html', scope)
        except StarletteHTTPException:
            # 连 index.html 都没有（前端还没构建）。这时给个 404 是诚实的
            raise StarletteHTTPException(404)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.ensure_store()
    _banner()
    yield


def _banner():
    """启动横幅。这几行是排查「手机连不上」「AI 不通」的第一手信息，
    所以格式要稳定：这些字段（端口 / 静态目录 / 存储 / AI / 局域网地址）
    是肉眼扫一眼就要找到的，别往上加装饰。"""
    port = int(os.environ.get('CARDS_PORT') or 8080)
    lan = os.environ.get('CARDS_LAN') == '1'

    print('serving  %s' % STATIC_DIR)
    if not os.path.isdir(WEB_DIST):
        print('         !! web/dist 还没构建，Vue 版打不开。到 web/ 下跑：')
        print('            npm install && npm run build')
    print('API      http://127.0.0.1:%d/api/health' % port)
    print('本机访问 http://127.0.0.1:%d/' % port)
    print('交互文档 http://127.0.0.1:%d/docs' % port)

    s = db.stats()
    print('卡片 %d 张（自定义 %d）· 今日待复习 %d'
          % (s['total'], s['custom'], s['dueToday']))

    try:
        n = db.user_count()
        print('账号 %d 个%s' % (n, '' if n else '（第一个注册的人自动成为管理员）'))
    except Exception as e:
        # 老库还没建 users 表时不要让整条横幅崩掉 —— 横幅是排查的第一手信息，
        # 它自己报错就没得看了
        print('账号    ? 读取失败：%s' % str(e)[:80])

    for line in store_pkg.banner_lines():
        print(line)

    st = llm.status()
    print('%s %s' % ('AI      ' if st['ok'] else 'AI 不可用', st['msg']))
    if not st['ok']:
        print('         ↑ 关了也不影响背卡 / 复习 / 导入分章，AI 只是可选增强')

    for line in netinfo.banner(port, lan):
        print(line)


app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESC,
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

# 纯公开 API，不带 cookie —— 所以 allow_credentials 保持 False
# （它和 allow_origins=['*'] 不能同时开，浏览器会直接拒）
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def guard_log_cache(request: Request, call_next):
    """三件事攒在一个中间件里：体积闸门 → 转发 → 补缓存头 + 记 API 日志。

    分开写三个会让每个请求多穿三层，收益为零。
    """
    n = request.headers.get('content-length')
    if n and n.isdigit() and int(n) > MAX_BODY:
        # 语义上 413 才对（以前这里是 400，且提示还写着「上限 2MB」，
        # 实际是 16MB —— 提示早就过期了）。
        return JSONResponse(status_code=413, content={
            'ok': False, 'msg': '请求体过大（上限 %dMB）' % (MAX_BODY >> 20)})

    is_api = request.url.path.startswith('/api/')
    t0 = time.perf_counter()
    resp = await call_next(request)

    if is_api:
        # 进度、笔记这些接口的返回值绝不能进浏览器缓存，否则标记了「会」
        # 刷新又变回原样，人会以为是数据丢了
        resp.headers['Cache-Control'] = 'no-store'
        # 只记 API：静态资源一屏几十个请求，记了刷屏，真正要看的错误反而被埋
        sys.stderr.write('%s %s → %d  %.0fms\n' % (
            request.method, request.url.path, resp.status_code,
            (time.perf_counter() - t0) * 1000))
    else:
        # sw.js 必须是 no-cache，否则 Service Worker 更新推不下去
        resp.headers.setdefault('Cache-Control', 'no-cache')
    return resp


@app.exception_handler(StarletteHTTPException)
async def on_http_error(_request: Request, exc: StarletteHTTPException):
    """HTTPException → 前端认识的 `{ok:false,msg}`。

    前端所有错误分支都读 body.msg，默认的 `{"detail": "..."}` 会让它显示成
    一串看不懂的对象。
    """
    return JSONResponse(status_code=exc.status_code,
                        content={'ok': False, 'msg': str(exc.detail)})


@app.exception_handler(RequestValidationError)
async def on_bad_params(_request: Request, exc: RequestValidationError):
    """参数问题一律 400（FastAPI 默认 422）。

    不是洁癖：老前端到处是 `if (r.status === 400)`，换成 422 会静默走进
    「服务器错误」那条分支，错误信息就没了。
    """
    errs = exc.errors()
    # 坏 JSON 走单独一句话：pydantic 原话是 "JSON decode error"，
    # 前端弹给用户看太出戏
    if errs and errs[0].get('type') == 'json_invalid':
        return JSONResponse(status_code=400,
                            content={'ok': False, 'msg': '请求体不是合法 JSON'})

    detail = '参数不合法'
    if errs:
        first = errs[0]
        # loc 形如 ('body', 'level') 或 ('query', 'limit')；只保留真正的字段名，
        # 中间那些 'body'/'query' 和列表下标（整数）都丢掉
        name = '.'.join(str(x) for x in first.get('loc', ())
                       if isinstance(x, str) and x not in ('body', 'query', 'path'))
        msg = first.get('msg') or detail
        detail = ('%s: %s' % (name, msg)) if name else msg
    return JSONResponse(status_code=400, content={'ok': False, 'msg': detail})


@app.exception_handler(Exception)
async def on_boom(_request: Request, exc: Exception):
    """兜底 500。

    Starlette 会在发完这个响应后把异常重新抛出，所以 traceback 照样会打到
    日志里 —— 该看的堆栈没被藏起来，但客户端拿到的是约定的 JSON 形状。
    """
    sys.stderr.write('[api] %s: %s\n' % (type(exc).__name__, exc))
    return JSONResponse(status_code=500,
                        content={'ok': False, 'msg': '服务器内部错误'})


for _r in ROUTERS:
    app.include_router(_r)

# /data 单独挂一份：网页里写的是 <script src="data/catalog.js">，
# 相对根路径解析成 /data/catalog.js，指向 study/data/ 那份唯一真相源。
# 这一段要挡住 store/（笔记正文、复习进度都在这儿）。
_data_mount = GuardedStatic(directory=DATA_DIR, html=False)
_data_mount.deny = ('store/',)
app.mount('/data', _data_mount, name='data')

# 最后挂，且挂在 '/' 上：API 路由先匹配，剩下的才落到静态资源。
# 用 SpaStatic 而不是 GuardedStatic —— Vue 是 history 模式，/cards 这类路径
# 在磁盘上没有对应文件，必须回落到 index.html，否则用户一刷新就白屏。
_web_mount = SpaStatic(directory=STATIC_DIR, html=True)
_web_mount.deny = ()
app.mount('/', _web_mount, name='static')
