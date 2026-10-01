# -*- coding: utf-8 -*-
"""全局常量：路径、体积上限、错误话术、OpenAPI 元信息。只在这里写一次。"""
import os

from . import WEB_DIR

# ⚠️ 这里以前写的是 `from . import DATA_DIR, WEB_DIR`，为了让 app/main.py 能
# `from .config import DATA_DIR` 中转一手。DATA_DIR 在本文件里从没被用过 ——
# pyflakes 报 "imported but unused" 是**对的**，但删了会炸：
# py_compile 全绿、check.js 的语法检查也过，一直到真起服务才 ImportError。
# （2026-09-26 就是照 pyflakes 删掉它，check.js 当场报「服务没起来」。）
#
# 正确解法不是加 noqa，是**去掉这层中转** —— DATA_DIR 本来就定义在
# app/__init__.py，main.py 已改成 `from . import DATA_DIR` 直接取。
# 教训：静态分析报的"没人用"，动手前必须 grep 一遍跨模块的引用点。

# ---- 网页端目录（Vue 工程）----
#
#   web/                Vite 工程根（源码在 src/）
#   web/public/         原样搬到站点根的静态资源：
#                         _seed.html   截图/冒烟用的登录种子页
#                         sw.js        历史 Service Worker 的清理脚本（自杀版）
#                         icons/ manifest.json  PWA 图标与清单
#   web/dist/           构建产物（npm run build 生成）
#
# 后端只挂 dist 一个目录：Vite 会把 public/ 里的东西原样复制进去，
# 所以 icons、sw.js 构建后都在 dist 根上，路径不用动。
WEB_DIST = os.path.join(WEB_DIR, 'dist')
WEB_PUBLIC = os.path.join(WEB_DIR, 'public')

#: 静态根。优先构建产物；一次都没构建过时退回 public —— 此时
#: 只有 _seed.html / sw.js 这类静态资源可用，Vue 版会打不开，
#: 启动横幅里会明确提示去跑 npm run build。
STATIC_DIR = WEB_DIST if os.path.isdir(WEB_DIST) else WEB_PUBLIC

# 请求体上限。PDF 走 base64 会膨胀 ~33%，一份八股文 PDF 动辄好几兆，
# 几年前的 2MB 上限（以及那句过期的「上限 2MB」提示）早就不够用。
MAX_BODY = 16 * 1024 * 1024

# 大模型报错的内部代号 → 给人看的话。面板上写「no_model」没人看得懂。
# 注意：这里的 key 必须与 core/llm.py 里 raise RuntimeError(...) 的字符串一致
# —— 两边对不上时不会报错，只会把内部代号原样甩到面板上。
LLM_ERR = {
    'ai_off': '本服务关了 AI 精读（启动时设了 AI=off）—— 背卡、复习、导入分章不受影响',
    'no_key': '云端模式要设 LLM_API_KEY',
    'no_model': '没找到可用模型。跑 `ollama pull qwen2.5:7b-instruct` 再试',
    'too_short': '这一章太短，没啥可精读的',
    'llm_not_json': '模型没吐出合法 JSON，多半是模型太小或提示被截断，换个模型再试',
}

# 共用数据目录 study/data 单独挂在 /data 上（网页里 `<script src="data/xx.js">` 要用），
# 但 store/ 这一层不给外部看：手机连着 WiFi 时，浏览器随手敲个
# /data/store/progress.json 就能把笔记正文、复习进度拉走。
DENY_PREFIX = ('store/',)

API_TITLE = '智径 EduPath API'
API_VERSION = '3.0'
API_DESC = """
自适应学习平台的后端接口：账号 / 背卡 / 复习 / 笔记 / 导入 / 图谱。

响应永远是 `{"ok": true, ...}` 或 `{"ok": false, "msg": "..."}`：

| 实现 | 启动 | 依赖 |
|---|---|---|
| FastAPI（唯一实现） | `python back_study/run.py 8080` | `pip install -r back_study/requirements.txt` |

> 以前还有个零依赖版 `back_study/server.py`（纯标准库，一个包都不用装），
> 2026-09-26 已移除：鉴权改用 PyJWT 之后它名不副实，留着它意味着每个接口写两遍。

鉴权用 `Authorization: Bearer <token>`。**状态码约定**（前端依赖这个，别改）：
- `401` token 缺失/失效 → 前端清 token 跳登录页
- `400` 凭据不对/参数问题 → 前端就地弹提示
- `403` 登录了但没权限

`/api/llm/status` 返回 `ok:false` 是**正常状态**不是故障 —— AI 精读是可选增强，
关了它，背卡 / 复习 / 导入分章照常工作。

注意：`progress` / `notes` 目前**还没有按用户隔离**（见 README 的「登录」一节），
所以多账号之间会看到同一份学习进度。这是下一步的事，不是 bug。
"""

# Swagger 里的分组顺序
OPENAPI_TAGS = [
    {'name': '认证', 'description': '注册、登录、当前用户'},
    {'name': '结构', 'description': '健康探测、分类树、知识框架、图谱'},
    {'name': '卡片', 'description': '卡片的增删改查'},
    {'name': '学习', 'description': '复习进度（SM-2 间隔调度）、今日队列、统计'},
    {'name': '笔记', 'description': '笔记的增删改查'},
    {'name': '导入', 'description': '粘贴文本 → 切分成草稿卡；草稿补齐后入库'},
    {'name': '文档', 'description': '整份 md/txt/pdf 导入 → 自动分章 → 逐章阅读'},
    {'name': 'AI 精读', 'description': '调本地 Ollama 或云端大模型，给章节补类比/重点/原理拆解'},
]
