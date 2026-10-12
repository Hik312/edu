# -*- coding: utf-8 -*-
"""把中间件相关的卡片从 java 迁到 middleware 科目（一次性迁移脚本）。

**为什么需要它**：Redis / MySQL / 消息队列 这些卡原来都挂在 `java` 科目下，
但它们和 Java 语言无关——是独立的中间件。放在 java 里导致：
① 做「中间件」方向复习时得在 Java 科目里翻；
② 分类树和实际技术栈不匹配（用户学的是后端，不只 Java）。

**判定口径**：只看 `topicPath[1]`（二级主题），**不看关键词**。
★ 教训：早先用关键词搜「数据库」命中 45 张，实际 8 张是 AI 卡误伤
（AI 卡正文里提了「向量数据库」）。topicPath 是人工/生成时定死的分类，
比全文关键词可靠得多。

**幂等**：可重复执行，已迁移的卡会被跳过。

用法（必须用项目 venv，系统 python 没装 PyJWT）：
    back_study/.venv/Scripts/python.exe back_study/scripts/migrate_middleware.py
    back_study/.venv/Scripts/python.exe back_study/scripts/migrate_middleware.py --dry-run
"""
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))          # back_study/scripts
_ROOT = os.path.dirname(os.path.dirname(_HERE))             # study/
# ★ 往上**两级**才是项目根（scripts → back_study → study）。
#   少一级会指向 back_study/data（不存在），os.listdir 返回空 → 迁移 0 张却不报错。
DATA = os.path.join(_ROOT, 'data')
if not os.path.isdir(DATA):
    raise SystemExit('找不到 data 目录：%s（路径计算错了？）' % DATA)
TARGET_SUBJECT = 'middleware'
TARGET_TOPIC = '中间件'

#: 二级主题 → 迁移。键是 topicPath[1] 的精确值。
MIDDLEWARE_TOPICS = {
    'Redis 入门', 'Redis 数据结构', 'Redis 线程模型', 'Redis 持久化',
    'Redis 过期与淘汰', 'Redis 缓存设计', 'Redis 高可用', 'Redis 实战',
    'Redis 面试', 'Redis 运维',
    'MySQL', '消息队列', '分布式', '高可用', '缓存设计',
}


def card_files():
    """data/*.js 里所有含卡片数组的文件（排除配置类）。"""
    for name in sorted(os.listdir(DATA)):
        if not name.endswith('.js'):
            continue
        if name in ('catalog.js', 'roles.js', 'directions.js'):
            continue
        yield name, os.path.join(DATA, name)


def read_cards(path):
    """从 js 文件里提取卡片数组。返回 (prefix, cards, suffix) 以便原样写回。

    ★ 正则为什么用 `(\[.*\])\s*;` 而不是 `\[\s*\{.*\}\s*\]`：
      后者要求数组第一个字符后紧跟 `{`，而实际文件里有换行/注释
      （如 `var CARDS_X = \n[\n  {`），会一个文件都匹配不到 →迁移 0 张却不报错。
      **静默匹配失败是这类脚本最危险的失败方式**，所以正则宁可宽松，
      匹配不到时由调用方明确报告「0 张」而不是假装成功。
    """
    src = open(path, encoding='utf-8').read()
    m = re.search(r'(\[.*\])\s*;', src, re.S)
    if not m:
        return None
    try:
        cards = json.loads(m.group(1))
    except ValueError:
        return None
    return src[:m.start(1)], cards, src[m.end(1):]


def main():
    dry = '--dry-run' in sys.argv
    moved = skipped = 0
    by_file = {}

    for name, path in card_files():
        got = read_cards(path)
        if not got:
            continue
        prefix, cards, suffix = got
        changed = 0
        for c in cards:
            tp = c.get('topicPath') or []
            if len(tp) < 2 or tp[1] not in MIDDLEWARE_TOPICS:
                continue
            if c.get('subject') == TARGET_SUBJECT:
                skipped += 1
                continue
            c['subject'] = TARGET_SUBJECT
            # topicPath[0] 从「Java后端」换成「中间件」，保持层级语义
            c['topicPath'] = [TARGET_TOPIC] + tp[1:]
            changed += 1
        if changed:
            by_file[name] = changed
            moved += changed
            if not dry:
                out = prefix + json.dumps(cards, ensure_ascii=False, indent=2) + suffix
                open(path, 'w', encoding='utf-8').write(out)

    mode = 'DRY-RUN（未写盘）' if dry else '已写入'
    print('[migrate_middleware] %s' % mode)
    print('  迁移 %d 张，已是 middleware 跳过 %d 张' % (moved, skipped))
    for k, v in sorted(by_file.items(), key=lambda x: -x[1]):
        print('    %-32s %d' % (k, v))
    if dry:
        print('\n加 --dry-run 去掉即为真正执行。')
    else:
        print('\n下一步：python back_study/scripts/dbseed.py --sync')


if __name__ == '__main__':
    main()