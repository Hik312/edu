# -*- coding: utf-8 -*-
"""pdfmarkup 的回归测试。

跑法：cd back_study; python scripts/test_pdfmarkup.py
"""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(os.path.dirname(_HERE), 'core')
for _name in ('db', 'llm', 'algostore', 'security'):
    if _name not in sys.modules:
        _m = type(sys)('_stub_' + _name)
        _m.__getattr__ = lambda n: (lambda *a, **k: None)  # noqa: E731
        sys.modules[_name] = _m

_spec = importlib.util.spec_from_file_location(
    '_pm', os.path.join(_CORE, 'pdfmarkup.py'))
pm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pm)


def test_typescript_block():
    src = '''基本语法

需求：定义一个装饰器。

function CustomString(target: Function) {
  target.prototype.toString = function () {
    return JSON.stringify(this)
  }
  Object.seal(target.prototype)
}

结束语。'''
    md = pm.to_markdown(src)
    assert '```' in md, '没识别出代码块:\n' + md
    assert 'function CustomString' in md
    assert '```typescript' in md, '语言没标成 typescript:\n' + md
    # 正文不能被吞进代码块
    assert md.count('```') == 2, '围栏不配对:\n' + md
    assert '结束语。' in md


def test_python_block():
    src = '''说明

from typing import List

class Foo:
    def bar(self):
        print("hi")
        return 1

后面还有内容。'''
    md = pm.to_markdown(src)
    assert '```python' in md, '没认出 python:\n' + md
    assert '后面还有内容。' in md


def test_prose_not_code():
    """正文里的括号/等号不能被当代码。"""
    src = '''这个参数 = 5 ，见下表(x) 。
我们约定：a == b 时返回 true 。
就这样，没有别的了。'''
    md = pm.to_markdown(src)
    assert '```' not in md, '正文被误判成代码了:\n' + md


def test_page_numbers_dropped():
    lines = ['标题', ''] + ['%d' % i for i in range(1, 21)] + ['正文内容']
    out = pm.drop_page_numbers(lines)
    assert len(out) == 3, '页码没被剔除: %r' % out
    assert '正文内容' in out


def test_page_numbers_kept_when_few():
    """数字很少时不删 —— 数学推导里的 1 2 3 不是页码。"""
    lines = ['推导', '1', '2', '3', '结论']
    out = pm.drop_page_numbers(lines)
    assert len(out) == 5, '少量数字被误删: %r' % out


def test_pua_stripped():
    lines = ['正常文字', '坏字考']
    out = pm.clean_pua(lines)
    assert '' not in ''.join(out), '私用区乱码没清掉'


def test_existing_fence_preserved():
    """已经有围栏的（md/txt 上传）不能被二次包裹。"""
    src = '说明\n\n```ts\nconst a = 1\n```\n'
    md = pm.to_markdown(src)
    assert md.count('```') == 2, '原有围栏被搞坏了:\n' + md


def test_long_prose_with_number_not_heading():
    """★ 回归：带序号的整句正文曾被误判成标题。

    真实案例（实测 80 字）���「1. 装饰器本质是一种特殊的函数，它可以对：
    类、属性、方法、参数进行扩展，同时能让代码更简洁。」——
    它以「1. 」开头，但它是正文不是标题。
    """
    prose = ('1. 装饰器本质是一种特殊的函数，它可以对：类、属性、方法、参数进行扩展，'
             '同时能让代码更简洁。')
    assert len(prose) > 32
    assert pm.detect_title_level(prose) is None, '长正文被当成标题了'

    # 短标题仍然要认出来
    assert pm.detect_title_level('1. 基本语法') == (2, '1. 基本语法')
    assert pm.detect_title_level('一、简介') == (1, '一、简介')


def test_heading_levels():
    """中文序号 = 1 级，阿拉伯序号 = 2 级。"""
    md = pm.annotate_headings('''一、装饰器工厂

正文。

1. 基本语法

更多正文。''')
    assert '# 一、装饰器工厂' in md, md
    assert '## 1. 基本语法' in md, md


def test_chapter_marker():
    md = pm.annotate_headings('第二章 并发\n\n正文。')
    assert '# 第二章 并发' in md, md


def test_code_not_turned_into_heading():
    """代码里的 `1. xxx` 不能被当成二级标题。"""
    src = '''说明

```ts
const a = 1
for (let i = 0; i < 3; i++) {
  console.log(i)
}
function f() {
  return 1
}
```

一、真正的章

正文。'''
    md = pm.annotate_headings(src)
    assert '## 1.' not in md, '代码被当成标题了:\n' + md
    assert '# 一、真正的章' in md, '真标题没标出来:\n' + md
    assert md.count('```') % 2 == 0, '围栏被打破:\n' + md


def test_cn_num():
    assert pm._cn_to_int('三') == 3
    assert pm._cn_to_int('十') == 10
    assert pm._cn_to_int('十二') == 12
    assert pm._cn_to_int('二十') == 20
    assert pm._cn_to_int('二十一') == 21


def test_junk_not_heading():
    """★ 回归：论文/日志类 PDF 的垃圾行不能进目录。

    真实案例（实测 16 章文档里有 5 条）：「55.18%」「62.59%」「32.00%」
    「3...」「8 ).」「1.0success rate」—— 全都能匹配编号正则。
    """
    for junk in ('55.18%', '62.59%', '32.00%', '3...', '8 ).',
                 '1.0success rate', '123', '-'):
        assert pm.detect_title_level(junk) is None, '垃圾行被当标题了: %r' % junk
    # 真标题仍然要认
    assert pm.detect_title_level('1. 基本语法') is not None
    assert pm.detect_title_level('5.2 Conversational AI') is not None


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