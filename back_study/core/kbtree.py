# -*- coding: utf-8 -*-
"""知识库文件夹树 —— PyCharm 那套「自己建文件夹往里丢文件」的模型。

## 为什么不用 category / domain 两级分类
原来的界面是 `category(资料/论文) → domain(人工智能)` 两层硬编码的树，
层级固定、名字由分类器猜、改不了也删不掉。用户真正想要的是
**自己决定怎么组织**：论文、资料、笔记全都是叶子，任何叶子下面还能再套文件夹
（资料 → RAG → (0)(1)(2) / 后端知识点 → (0)(1)(2)）。
所以分类字段降级成**纯数据**（仍入库，供搜索/筛选用），界面只认这棵树。

## 存哪
整棵树是**单例状态**（一次只有一棵树），所以存在 `meta.kb_tree` 一行里，
不是每份文档存一份。存进 meta 而不是新建表，是为了不引入第二个真相源 ——
将来若有人把树当文档属性去读，会拿到 99 份一样的副本。

## 树的数据形状
```json
[{"id": "f_ab12", "name": "RAG", "children": [], "docs": ["doc-xxx"], "collapsed": false}]
```
- 顶层就是一个数组，没有虚拟根 —— 前端自己渲染一个固定的「全部」节点。
- `docs` 存文档 **id**（不是标题）：标题会改，id 不会。
- `collapsed` 是**持久化**的：目录多起来之后，「我不想每次都看到全部展开」
  是个真实的日常状态，重开页面还记着才叫好用。
"""
import os

#: 存进 meta 的键名。别和别的 meta 键撞（卡片指纹等都在同一个表里）。
TREE_KEY = 'kb_tree'


def _new_id():
    """文件夹 id。

    ★ 必须**全局唯一**，不能只看时间戳（2026-10-11 修）：
      建一个树要连续调三次（顶层 → 二级 → 三级），**都在同一毫秒内**，
      `md5(str(time.time()))[:6]` 算出来完全一样 → 三个节点 id 相同。
      后果不是「id 不好看」，而是**树结构直接塌掉**：
        · _find 永远命中第一个同名id → 后续操作全打在错的节点上
        · move_folder 的防环检查把「自己」误判成「自己的后代」→ 永远拒绝移动
      这类 bug 极难定位：功能测试只测一级文件夹时完全正常，
      一进二级就全线崩。判据：**任何 id 生成器都必须抗「同毫秒多次调用」**。
      现在用 os.urandom，比时间戳单调但不可猜，且天然抗碰撞。"""
    return 'f_' + os.urandom(5).hex()


def _norm(nodes):
    """把从存储/前端读到的原始树规整成合法形状。

    为什么要规整而不是直接用：这份树是**用户手拖出来的**，
    历史数据、并发写、手工改库都可能留下半个节点。
    缺 name 的节点在界面上就是一行空白，children 不是 list 会直接 500。
    宁可悄悄补齐，也不要让整个左树打不开。"""
    out = []
    if not isinstance(nodes, list):
        return out
    for n in nodes:
        if not isinstance(n, dict):
            continue
        name = str(n.get('name') or '').strip()
        if not name:
            continue
        docs = n.get('docs')
        out.append({
            'id': str(n.get('id') or _new_id()),
            'name': name[:60],
            'children': _norm(n.get('children')),
            'docs': [str(d) for d in docs] if isinstance(docs, list) else [],
            'collapsed': bool(n.get('collapsed')),
        })
    return out


def load(backend):
    """读树。读不出来（空/非法 JSON）就当空树，不抛错 ——
    界面要先能用，用户重建总比打不开强。"""
    import json
    raw = ''
    try:
        raw = backend.get_meta(TREE_KEY, '')
    except Exception:
        raw = ''
    if not raw:
        return []
    try:
        return _norm(json.loads(raw))
    except Exception:
        return []


def save(backend, nodes):
    import json
    ok = backend.set_meta(TREE_KEY, json.dumps(_norm(nodes), ensure_ascii=False))
    return bool(ok)


def _find(nodes, fid):
    """在 nodes 里按 id 找节点，返回 **(nodes, 下标)**；找不到 (None, -1)。

    ★ 返回的是**包含该节点的那个列表**，而不是节点对象 ——
      移动/改名都是「在父的 children 里换一项」，拿不到父列表就没法就地改。
      树全程就地修改，不做「深拷贝出来改完再写回」：后者在两处
      （注册表 / 进程内缓存）都容易长成「改了一个副本」的版本。

    ★★ 这里曾经有个真bug（2026-10-11 修）：老代码把外层循环变量当成
      **子列表**用（`for lst in nodes: for i,n in enumerate(lst)`），
      而 nodes 本身就是「节点列表」—— 于是 enumerate(dict) 迭代的是 dict 的
      **键（字符串）**，n.get 直接 AttributeError被外层的except 吞掉，
      表现是「新建二级文件夹永远报『父文件夹不存在』」。
      一级文件夹不走_find，所以这bug 一直藏着：树只能有一层深。
     教训：**遍历辅助函数第一次写就该带一个二级用例**，
      只测一级的话这类结构错误永远测不出来。"""
    if not isinstance(nodes, list):
        return None, -1
    for i, n in enumerate(nodes):
        if not isinstance(n, dict):        # 脏数据（见 load/_norm）跳过，别让整树崩
            continue
        if n.get('id') == fid:
            return nodes, i
        got = _find(n.get('children') or [], fid)
        if got[0] is not None:
            return got
    return None, -1


def _walk(nodes, parent_id=None):
    """遍历，产出 (节点, 父节点id)。跳过非 dict 项（脏数据，见 _find）。"""
    if not isinstance(nodes, list):
        return
    for n in nodes:
        if not isinstance(n, dict):
            continue
        yield n, parent_id
        for x, p in _walk(n.get('children') or [], n.get('id')):
            yield x, p


def _is_descendant(nodes, candidate_id, ancestor_id):
    """candidate_id 是否是 ancestor_id 的后代（**不含它自己**）。

    ★ 防环用：把父节点拖进自己的子节点里会造出一个环，
      之后所有遍历都是无限递归 → 接口 500，且进程可能直接挂。
      所以必须在**写入前**判，不是渲染到一半才发现。

    ★★ 要从 ancestor_id 的**子树**往下找（2026-10-11 修）：
      之前的写法虽然拿的是_find 的返回，但整套逻辑从没在三层树上跑过，
      于是「把顶层文件夹拖进自己的**孙**文件夹」这条最典型的造环路径
      根本拦不住 —— 而造出来的环会让后续每次遍历都是无限递归。
      判据：**凡是防环逻辑，测试用例必须造三层**，只测一层等于没测。"""
    lst, i = _find(nodes, ancestor_id)
    if lst is None:
        return False
    for n, _ in _walk(lst[i].get('children') or [], ancestor_id):
        if n.get('id') == candidate_id:
            return True
    return False


def add_folder(nodes, parent_id, name):
    name = (name or '').strip()[:60]
    if not name:
        return {'ok': False, 'msg': '文件夹名不能为空'}
    # nodes 可能是从 meta 读出来的脏结构（甚至不是 list）。就地改一个非 list
    # 会AttributeError 冒到接口层 → 整个左树 500。
    # 这里返回「失败」而不是自己造一个 list 顶替：调用方（路由）拿的是
    # 刚 load 出来的对象，悄悄换掉它等于「改了但没存」。
    if not isinstance(nodes, list):
        return {'ok': False, 'msg': '文件夹树损坏，请刷新后重试'}
    node = {'id': _new_id(), 'name': name, 'children': [],
            'docs': [], 'collapsed': False}
    if not parent_id:                       # 顶层
        nodes.append(node)
    else:
        lst, i = _find(nodes, parent_id)
        if lst is None:
            return {'ok': False, 'msg': '父文件夹不存在'}
        lst[i].setdefault('children', []).append(node)
    return {'ok': True, 'node': node}


def rename_folder(nodes, fid, name):
    name = (name or '').strip()[:60]
    if not name:
        return {'ok': False, 'msg': '名字不能为空'}
    lst, i = _find(nodes, fid)
    if lst is None:
        return {'ok': False, 'msg': '文件夹不存在'}
    lst[i]['name'] = name
    return {'ok': True, 'name': name}


def delete_folder(nodes, fid, mode='doc2root'):
    """删文件夹。mode='doc2root' 把里面的文档挪到根，不丢文档。

    ★ 为什么默认不删文档：用户删一个文件夹的意图是「整理结构」，
      不是「扔掉这批论文」。默认连带删文件的话，误删就是不可逆的 ——
      而 doc_id 变了之后原件路径也跟着变（files/<docId>/），恢复成本极高。
    """
    lst, i = _find(nodes, fid)
    if lst is None:
        return {'ok': False, 'msg': '文件夹不存在'}
    node = lst.pop(i)
    if mode == 'delete':
        return {'ok': True, 'removed': node}
    moved = _collect_docs(node)
    return {'ok': True, 'moved': moved}


def _collect_docs(node):
    out = list(node.get('docs') or [])
    for c in node.get('children') or []:
        if isinstance(c, dict):
            out += _collect_docs(c)
    return out


def move_folder(nodes, fid, new_parent):
    """把文件夹移到 new_parent 下（'' = 顶层）。

    ★ 防环的**顺序**有讲究（2026-10-11 踩过）：
      先判断 `_is_descendant(nodes, new_parent, fid)`（新父是不是自己的后代），
      再判断 `new_parent == fid`。反过来写的话，「移进自己」这个最常见的
      误拖拽会被当成「移进后代」给出一条更费解的报错
      （实际上它俩在这里都成立，但顺序决定用户看到哪句话）。
    ★ `_is_descendant` 从**子树**找、不含自身，所以 `== fid` 要单独判。
    """
    lst, i = _find(nodes, fid)
    if lst is None:
        return {'ok': False, 'msg': '文件夹不存在'}
    if fid == new_parent:
        return {'ok': False, 'msg': '不能移进自己'}
    if new_parent and _is_descendant(nodes, new_parent, fid):
        return {'ok': False, 'msg': '不能移进自己的子文件夹'}
    node = lst.pop(i)
    if not new_parent:
        nodes.append(node)
        return {'ok': True}
    plist, pi = _find(nodes, new_parent)
    if plist is None:
        return {'ok': False, 'msg': '目标文件夹不存在'}
    plist[pi].setdefault('children', []).append(node)
    return {'ok': True}


def put_docs(nodes, did, target_ids):
    """把一份文档放进目标文件夹（可多选，等于「同时属于多个文件夹」）。

    先从所有文件夹里摘掉它再插进目标 —— 否则「移出文件夹」这个动作
    永远不生效：文档还留在旧文件夹的 docs 数组里。
    ★ 这就是「集合语义」：文档的位置由**唯一一份真值**决定，
      不能每个文件夹各存一份「我包含它」的副本。"""
    did = str(did)
    tset = set(str(x) for x in (target_ids or []))
    for n, _ in _walk(nodes, None):
        n['docs'] = [d for d in (n.get('docs') or []) if str(d) != did]
    for fid in tset:
        lst, i = _find(nodes, fid)
        if lst is not None and did not in lst[i].setdefault('docs', []):
            lst[i]['docs'].append(did)
    return {'ok': True}


def set_collapsed(nodes, fid, collapsed):
    lst, i = _find(nodes, fid)
    if lst is None:
        return {'ok': False, 'msg': '文件夹不存在'}
    lst[i]['collapsed'] = bool(collapsed)
    return {'ok': True}


def drop_doc(nodes, did):
    """把一份文档从所有文件夹里摘掉。

    文档被删除时必须调它 —— 树和 documents 是**两个存储**，
    删了文档不会顺手删树里的引用。结果是文件夹里挂着一个
    「永远打不开的死 id」：界面上因为按 id 查不到文档而看不见，
    看起来一切正常，但那份数据已经烂在库里了，下次按 id 恢复
    文档时会莫名其妙出现在某个文件夹里。"""
    did = str(did)
    n = 0
    for node, _ in _walk(nodes, None):
        before = len(node.get('docs') or [])
        node['docs'] = [d for d in (node.get('docs') or []) if str(d) != did]
        n += before - len(node['docs'])
    return {'ok': True, 'removed': n}