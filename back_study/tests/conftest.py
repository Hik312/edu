# -*- coding: utf-8 -*-
"""pytest 的路径引导 —— 让 `import algo` / `import report` 都能解析。

algo/ 依赖 back_study/ 在 sys.path；report.py（以及任何要碰 core/ 的测试）
依赖 core/ 在 sys.path。两条都挂上，测试文件就不用各自再写一遍。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACK = os.path.dirname(_HERE)                    # back_study
_CORE = os.path.join(_BACK, 'core')
for _p in (_BACK, _CORE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
