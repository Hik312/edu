# -*- coding: utf-8 -*-
"""数据层 · 规划域 —— 目标岗位知识点地图（role_plan）与知识框架 MOC 树（build_outline）。

两者都是「取卡片 + 取进度 + 翻译成前端好渲染的形状」的聚合函数，
自己不存任何状态。
"""
from .cards import all_cards
from .catalog import _kw_hits, cat_name, load_catalog, role_by_id, subject_name
from .progress import get_progress


def role_plan(role_id=None, subjects=None, user_id=None):
    """目标岗位 → 知识点地图。返回每个技能组的卡片、掌握情况与缺口。

    两条入口共用一个出口：
      role_id   预置岗位（data/roles.js）
      subjects   自定义科目组合（"java,ai,python"），不落库、用完即走

    为什么缺口按**技能词**算而不是按科目：科目「AI工程」有卡 ≠ 覆盖了这个岗位
    要的「向量检索」。技能词是岗位真正的考点，缺哪条说哪条才有用。
    """
    if role_id:
        role = role_by_id(role_id)
        if role is None:
            return None
        skills = role.get('skills') or []
        head = {'id': role.get('id'), 'name': role.get('name'),
                'desc': role.get('desc'), 'custom': False}
    else:
        subs = [s for s in (subjects or '').split(',') if s.strip()]
        if not subs:
            return None
        known = {s.get('id') for cat in load_catalog() for s in cat.get('subjects', [])}
        subs = [s.strip() for s in subs if s.strip() in known]
        if not subs:
            return None
        skills = [{'subject': s, 'weight': 2, 'keywords': []} for s in subs]
        head = {'id': 'custom', 'name': '自定义组合', 'desc': '自己勾的科目',
                'custom': True}

    prog = get_progress(user_id)
    groups, covered_n, total_kw = [], 0, 0
    for sk in sorted(skills, key=lambda x: -(x.get('weight') or 0)):
        sub = sk.get('subject')
        cards = all_cards(subject=sub)
        rows = []
        for c in sorted(cards, key=lambda x: x.get('id') or ''):
            p = prog.get(c.get('id')) or {}
            rows.append({
                'id': c.get('id'), 'title': c.get('title'),
                'oneLine': c.get('oneLine'), 'level': p.get('level', 0),
                'nextAt': p.get('nextAt'),
            })
        kws = sk.get('keywords') or []
        missing = [k for k in kws if not _kw_hits(k, cards)]
        covered = [k for k in kws if k not in missing]
        total_kw += len(kws)
        covered_n += len(covered)
        groups.append({
            'subject': sub, 'name': subject_name(sub),
            'weight': sk.get('weight') or 1,
            'count': len(rows),
            'learned': sum(1 for r in rows if r['level'] > 0),
            'mastered': sum(1 for r in rows if r['level'] == 3),
            'cards': rows,
            'covered': covered,
            'missing': missing,
        })

    return dict(head, skills=groups,
                summary={'keywords': total_kw, 'covered': covered_n,
                         # 没有技能词的岗位（roles.js 里某个角色 keywords: []）
                         # 一张卡都没覆盖，却因为「除零兜底成 100」而显示
                         # 「掌握度 100%」—— 仪表盘上最误导的一种数字。
                         # 前端看到 keywords 为空就不该展示百分比，
                         # 这里给 0 至少和「一张卡都没覆盖」一致。
                         'percent': int(round(100.0 * covered_n / total_kw))
                         if total_kw else 0,
                         'cards': sum(g['count'] for g in groups),
                         'mastered': sum(g['mastered'] for g in groups)})


# ---------- 知识框架（MOC 树） ----------
def build_outline(category=None, subject=None, user_id=None):
    """四层树：领域 → 科目 → 主题(topicPath) → 卡片。
    主题层从 topicPath 自动推导，不用另外维护一份目录。"""
    prog = get_progress(user_id)
    cards = all_cards(category=category, subject=subject)

    tree = []
    # ★ 这里曾经写成 `index[(cat, sub)] = 领域节点的 children`，于是同一个
    # category 的第二个 subject 因为 key 不同，又 append 了一个新的领域节点 ——
    # 67 张卡会长出 9 个顶层节点、其中 work 重复 5 次、kaoyan 重复 4 次，
    # 「领域 → 科目」第一层直接退化成「一科目一领域」。
    # 修法：按 cat 建索引，领域节点只在**首次见到这个 cat** 时进 tree。
    tree_index = {}                             # cat -> 领域节点
    for c in cards:
        cat = c.get('category') or 'other'
        sub = c.get('subject') or 'other'
        if cat not in tree_index:
            node = {'id': cat, 'name': cat_name(cat), 'type': 'category',
                    'count': 0, 'children': {}}
            tree.append(node)
            tree_index[cat] = node
        cat_node = tree_index[cat]
        sub_children = cat_node['children']
        if sub not in sub_children:
            sub_children[sub] = {'id': sub, 'name': subject_name(sub),
                                 'type': 'subject', 'count': 0, 'children': {}}
        sub_node = sub_children[sub]

        # 沿 topicPath 逐层下行（SpringBoot › 核心原理 › 自动装配），
        # 不只用 path[0]——否则所有卡都塌在同一层，看不出结构
        path = c.get('topicPath') or ['未归档']
        p = prog.get(c['id'])
        cur = sub_node['children']
        for i, seg in enumerate(path):
            if seg not in cur:
                cur[seg] = {'id': seg, 'name': seg, 'type': 'topic',
                            'count': 0, 'children': {}, 'cards': []}
            node = cur[seg]
            node['count'] += 1
            if i == len(path) - 1:
                node['cards'].append({
                    'id': c['id'],
                    'title': c.get('title'),
                    'oneLine': c.get('oneLine', ''),
                    'level': p.get('level', 0) if p else 0,
                    'path': ' › '.join(path)
                })
            cur = node['children']
        sub_node['count'] += 1
        cat_node['count'] += 1

    def to_list(d):
        out = []
        for v in d.values():
            n = dict(v)
            n['children'] = to_list(v['children'])
            out.append(n)
        return out

    for node in tree:
        node['children'] = [
            dict(s, children=to_list(s['children']))
            for s in node['children'].values()
        ]
        node['count'] = sum(s['count'] for s in node['children'])
    return tree
