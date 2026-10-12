# -*- coding: utf-8 -*-
"""扫卡片数据问题，**只报告不改数据**。

★ 为什么单独写脚本而不是临时命令：
  这类扫描要反复跑（改完一批要再验一次），而判断口径每条都有讲究，
  塞在命令行里既看不清也没法复用。产出一份可对比的清单。

判据（按「会不会真的影响使用」排severity）：
  P0 title 与内容完全脱节 —— 检索时它会拿高分排第一，回答却答非所问
  P1 title 极短/非问句 —— 卡片列表和搜索结果里看不懂这张卡讲什么
  P2 内容字段缺失或过短 —— 精读/转卡时质量下降，但不影响检索
  P3 分类字段异常 —— 不影响功能，影响筛选

只读：脚本不写任何文件、不改store。清单打在 stdout。
用法：python back_study/scripts/audit_cards.py [--verbose]
"""
import collections
import os
import re
import sys

BACK = os.path.dirname(os.path.abspath(__file__))       # .../back_study/scripts
ROOT = os.path.dirname(BACK)                             # .../back_study
# ★ 要插两层：db.py 在 core/ 下（顶层模块 `db`），
#   而 scripts/ 的父目录才是 back_study —— 只插 core 的话
#   `import db` 会 ModuleNotFoundError（db 依赖的兄弟模块也在 core 里）。
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'core'))

import db  # noqa: E402


def _norm(s):
    """去掉标点空格，只留实义字符，用于「有没有关系」的宽松判断。"""
    return re.sub(r'[^\w\u4e00-\u9fff]', '', s or '')


#: title 里这些词几乎每张卡的机制里都有，拿来判断「title 与内容有没有关系」
#: 毫无区分度，必须排除 —— 否则会把正常卡全报成 P0。
_STOP = set(_norm(w) for w in (
    '是什么', '为什么', '怎么', '如何', '哪些', '区别', '原理', '机制', '详解',
    '什么', '一个', '可以', '应该', '需要', '进行', '实现', '使用', '以及',
    'the', 'and', 'for', 'with', 'how', 'why', 'what',
))


def audit():
    cards = db.all_cards()
    issues = collections.defaultdict(list)

    for c in cards:
        cid = c.get('id') or ''
        title = (c.get('title') or '').strip()
        one = (c.get('oneLine') or '').strip()
        kws = ' '.join(c.get('keywords') or [])
        mech = ' '.join(c.get('mechanism') or [])
        analogy = (c.get('analogy') or '').strip()
        why = (c.get('why') or '').strip()
        scene = c.get('scene') or []
        q = c.get('interviewQ') or []
        tp = c.get('topicPath') or []
        pool = _norm(kws + mech + one + analogy + why + ''.join(tp))

        # ---------- P0：title 与内容脱节 ----------
        # ★ 第一版判据错了：正则`[\u4e00-\u9fff]{3,}` 把**整个中文串**
        #   当成一个词块，于是「LLM 网关解决什么问题」= 一个 12 字块，
        #   拿去内容里找当然找不到 → 201 张全误报。
        #   正确做法：切成 2~4 字的**中文 n-gram**，只要有一个命中就算有关。
        #   这才是「宽松判断」该有的样子 —— 判据宁可漏（少报）不可滥（误报）。
        if title:
            grams = [title[i:i + 3] for i in range(len(title) - 2)]
            grams += [title[i:i + 2] for i in range(len(title) - 1)]
            en = re.findall(r'[A-Za-z][A-Za-z0-9_+.-]{3,}', title)
            grams += en
            # 过滤掉无实义的通用词（「是什么」「怎么」「哪些」…）
            grams = [g for g in grams if _norm(g) not in _STOP]
            if grams and not any(_norm(g) in pool for g in grams):
                issues['P0-title与内容完全脱节'].append(
                    (cid, title[:30], ' '.join((c.get('keywords') or [])[:4])[:38]))

        # ---------- P1：title 过短且不像问题 ----------
        if len(title) < 8 and not any(
                k in title for k in ('什么', '为什么', '怎么', '如何', '区别', '原理',
                                    '机制', '详解', '是什么', '是')):
            issues['P1-title过短且非问句'].append(
                (cid, title, kws[:34]))

        # ---------- P1：title 是残句（以标点收尾/开头）----------
        if title and (title[0] in '，。、；：,.:;' or title[-1] in '，。、；：,.:;'):
            issues['P1-title是残句'].append((cid, title[:34], ''))

        # ---------- P2：内容字段薄 ----------
        if len(one) < 10:
            issues['P2-oneLine过短'].append((cid, title[:26], one[:16]))
        if len(mech) < 40:
            issues['P2-mechanism过短'].append((cid, title[:26], '%d字' % len(mech)))
        if len(analogy) < 8:
            issues['P2-analogy缺失'].append((cid, title[:26], ''))
        if len(scene) < 2:
            issues['P2-scene少于2条'].append((cid, title[:26], '%d条' % len(scene)))
        if len(q) < 2:
            issues['P2-interviewQ少于2条'].append((cid, title[:26], '%d条' % len(q)))

        # ---------- P3：分类字段 ----------
        if not tp:
            issues['P3-topicPath为空'].append((cid, title[:26], ''))
        elif len(tp) < 2:
            issues['P3-topicPath只有1层'].append((cid, title[:26], '/'.join(tp)))
        if not c.get('subject'):
            issues['P3-subject为空'].append((cid, title[:26], ''))
        if not c.get('domain'):
            issues['P3-domain为空'].append((cid, title[:26], ''))
        if not kws:
            issues['P3-keywords为空'].append((cid, title[:26], ''))

        # ---------- P3：related 指向自己 ----------
        for r in (c.get('related') or []):
            if r.get('id') == cid:
                issues['P3-related指向自己'].append((cid, title[:26], r.get('id')))

    return cards, issues


SEV_ORDER = ['P0-title与内容完全脱节', 'P1-title过短且非问句', 'P1-title是残句',
             'P2-oneLine过短', 'P2-mechanism过短', 'P2-analogy缺失',
             'P2-scene少于2条', 'P2-interviewQ少于2条',
             'P3-topicPath为空', 'P3-topicPath只有1层', 'P3-subject为空',
             'P3-domain为空', 'P3-keywords为空', 'P3-related指向自己']


def main():
    verbose = '--verbose' in sys.argv
    cards, issues = audit()
    print('=' * 74)
    print('卡片数据体检：全库 %d 张' % len(cards))
    print('=' * 74)
    total = 0
    for key in SEV_ORDER:
        rows = issues.get(key)
        if not rows:
            continue
        total += len(rows)
        print()
        print('【%s】%d 张' % (key, len(rows)))
        show = rows if verbose else rows[:12]
        for cid, t, extra in show:
            print('   %-28s %-30s %s' % (cid[:28], t, extra))
        if len(rows) > len(show):
            print('   … 还有 %d 张（加 --verbose 看全部）' % (len(rows) - len(show)))
    print()
    print('-' * 74)
    print('问题条目合计 %d 条，涉及 %d 张卡（占 %.1f%%）'
          % (total, len({r[0] for k in issues for r in issues[k]}),
             100.0 * len({r[0] for k in issues for r in issues[k]}) / max(len(cards), 1)))
    if total == 0:
        print('干净。')
    return 0


if __name__ == '__main__':
    sys.exit(main())