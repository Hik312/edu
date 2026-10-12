# -*- coding: utf-8 -*-
"""分章修复的回归测试：代码块内部不能被当成标题切断。

跑法：cd back_study; python -m pytest scripts/test_chapter_split.py -q
或直接 python scripts/test_chapter_split.py
"""
import os
import sys

import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(os.path.dirname(_HERE), 'core')

# ★ 只加载 importer 的源码，不走包导入：importer → db → security → PyJWT，
#   而分章是纯函数，跟鉴权一点关系没有。为了测一个正则去装 PyJWT 不值当。
#   真的缺了 PyJWT 时本机也起不了服务，所以这里 stub 掉那两个模块。
sys.path.insert(0, _HERE)
for _name in ('db', 'llm', 'docparse', 'algostore', 'security'):
    if _name not in sys.modules:
        _m = type(sys)('_stub_' + _name)
        _m.__getattr__ = lambda n: (lambda *a, **k: None)  # noqa: E731
        sys.modules[_name] = _m

_spec = importlib.util.spec_from_file_location(
    '_importer_under_test', os.path.join(_CORE, 'importer.py'))
importer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(importer)


def test_code_block_not_split():
    """markdown 文档：代码块里有 # / ## / // 看着像标题的行，不能切断。"""
    text = """# 教程

正文一。

```python
# 这是注释不是标题
## 这也是
def f():
    # 再来一个
    return 1
```

正文二。

## 第二章

更多内容。
"""
    doc = importer.parse_document(text)
    chs = doc['chapters']
    full = '\n'.join(c['body'] for c in chs)
    # 代码块内容必须完整出现在某章里
    assert '# 这是注释不是标题' in full, '注释行被当标题吃掉了'
    assert '## 这也是' in full, '代码块里的 ## 被当标题切断了'
    assert 'return 1' in full
    # 代码块不能被拆到两个章节
    fence_ch = [c for c in chs if '```python' in (c.get('body') or '')]
    assert len(fence_ch) == 1, '代码块被拆到多个章节了'


def test_shell_comment_not_split():
    """shell / yaml：整篇注释和缩进结构不能被切。"""
    text = """# 部署脚本

```bash
#!/bin/bash
# 安装依赖
echo start
```

结束。
"""
    doc = importer.parse_document(text)
    full = '\n'.join(c['body'] for c in doc['chapters'])
    assert '# 安装依赖' in full
    assert 'echo start' in full


def test_real_headings_still_split():
    """修复不能过头：真正的标题仍然要切章。"""
    text = """# 第一章

甲内容。

# 第二章

乙内容。
"""
    doc = importer.parse_document(text)
    titles = [c['title'] for c in doc['chapters']]
    assert any('第一章' in t for t in titles), '真标题没被识别：%s' % titles
    assert any('第二章' in t for t in titles), '真标题没被识别：%s' % titles


if __name__ == '__main__':
    fails = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith('test_') or not callable(fn):
            continue
        try:
            fn()
            print('  PASS %s' % name)
        except AssertionError as e:
            fails += 1
            print('  FAIL %s: %s' % (name, e))
        except Exception as e:
            fails += 1
            print('  ERROR %s: %s: %s' % (name, type(e).__name__, e))
    print('OK' if not fails else 'FAILED: %d' % fails)
    sys.exit(1 if fails else 0)