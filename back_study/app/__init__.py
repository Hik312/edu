# -*- coding: utf-8 -*-
"""FastAPI 后端包（入口 `python back_study/run.py`，或先 cd 进 back_study 再 `python run.py`）。

仓库现在的分层（study/ 下四块，前后端一眼分得开）：

    study/
      back_study/   后端：本包(app/) + 入口(run.py) + 数据层(core/) + 开发脚本(scripts/)
      web/          网页端：Vue 3 + Vite 工程（src/ 四层架构，public/ 放静态与旧过渡页）
      data/         卡片数据（唯一真相源）+ 运行数据（store/）

这里为什么要动 sys.path：
    db / importer / llm / netinfo / security 住在 back_study/core/ 下。
    这一层只有一份、不复制第二份 —— 数据逻辑一旦有两份，
    「网页说明天复习、接口说后天」这类不一致迟早冒出来。
    （core/ 里除 pymysql 和 PyJWT 外只用标准库，这是为了保持它可独立测试，
      不是为了"零依赖运行" —— 那条线 2026-09-26 已经不维护了。）
    所以这里只把 core/ 挂进导入路径，之后各 router 直接 `import db` 就行。
"""
import os
import sys

BACK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # back_study/
ROOT = os.path.dirname(BACK_DIR)                                        # study/ 项目根

CORE_DIR = os.path.join(BACK_DIR, 'core')
SCRIPTS_DIR = os.path.join(BACK_DIR, 'scripts')
WEB_DIR = os.path.join(ROOT, 'web')
DATA_DIR = os.path.join(ROOT, 'data')
# 注意：以前这里还有个 MINI_DIR 指向 minprogram/。小程序端 2026-09-26 整端移除，
# 常量没人用却会指向一个不存在的目录，所以连它一起删 —— 别按老笔记再加回来。

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
