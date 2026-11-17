# -*- coding: utf-8 -*-
"""存储后端契约。

**为什么要抽这一层**：db.py 原本把「读哪个文件、怎么解析」和「进度怎么算、
队列怎么排」搅在一起。要换 MySQL 就得动业务逻辑，一动就两边不一致。
现在把「存哪儿」隔离成后端，「怎么算」留在 db.py —— 换后端不碰业务代码。

**契约要点**（改动这里之前先想清楚）：

1. 所有方法都是**同步**的。pymysql 和本地文件 IO 都是同步的，FastAPI 那边
   端点写同步 `def`，由 starlette 丢进线程池 —— 别在这里引入 async：
   一旦有方法变异步，所有调用点都得跟着改，而收益是零（本来就没有并发 IO 可等）。
2. `builtin_all()` 返回 `None` 表示「后端不管内置卡，交回文件层」。
   JSON 后端就是这么干的（内容源 data/*.js 由 git 管，本来就该是文件）。
   MySQL 后端会把内置卡灌进表里，于是能拿 SQL 直接 JOIN 进度查队列。
3. 参数/返回值一律用 **dict / list**，字段名与卡片 JSON 完全一致。
   不要在这里做字段改名或结构转换 —— 转换一旦有两份，就会出现
   「网页显示 level、接口返回 lv」这类问题。
4. 写方法要对**单行**友好（`*_put` / `*_del`）。整表覆盖的 `*_replace`
   只给「列表式」调用方兜底，热路径（打复习进度、写 AI 精读）必须走单行，
   否则一次评级要把整个 documents 表重写一遍。
5. **个人数据必须按 user_id 隔离**（2026-10-03 加）。progress / notes 是
   per-user 的，MySQL 侧主键是 `(user_id, card_id)` / `(user_id, id)`。
   以前两处主键都只有 card_id / id，于是两个用户复习同一张卡会**互相覆盖**
   —— 不是"看到别人的数据"这种明显故障，而是后写的把先写的静默顶掉，
   谁的档位、间隔、笔记都丢了，且没有任何日志。实测踩过：探针账号把本人
   6 行进度全盖成自己的。
   `user_id=None` 一律当**匿名公共桶**（user_id='' 那一档），只给脚本 /
   迁移 / 种子数据用。业务端点必须传真实 uid —— 鉴权看的是
   「响应里有没有个人数据」，不是方法名上带没带 put。
"""
import json
import os
import sys


class Store(object):
    """所有后端的基类。方法没实现就抛，避免「以为接了其实没接」。"""

    name = 'base'
    #: 支持内置卡（data/*.js 灌进库）的后端为 True
    holds_builtin = False

    # ---------------- 读 ----------------
    def builtin_all(self):
        """内置卡列表；None = 不由本后端负责（调用方回落到 data/*.js）。"""
        return None

    def custom_all(self):
        raise NotImplementedError

    def progress_all(self, user_id=None):
        """某人的全部进度：{card_id: {level, interval, ef, reps, nextAt, updatedAt}}。

        `user_id=None` 读匿名公共桶，**不是**「读所有人的」。
        """
        raise NotImplementedError

    def notes_all(self, user_id=None):
        raise NotImplementedError

    def docs_all(self):
        raise NotImplementedError

    def docs_brief(self):
        """只返回**列表页需要的轻字段**，不含 chapters / text。

        ★ 为什么必须有这个方法：`documents` 表的 `chapters` 是 JSON、
          `doc_text` 是 MEDIUMTEXT（装得下整篇论文，最大 16MB）。
          列表页一个字段都不用它们，却因为走 `docs_all()` → `SELECT *`
          把每篇论文全文从 DB 捞一遍 —— 文档越多越慢，且内存峰值是
          全部论文的总量。**字段少读是这里唯一的优化**，
          所以约定：SQL 只 SELECT 列表要用的列。
        """
        raise NotImplementedError

    def doc_get(self, did):
        """按 id 取**单篇完整文档**（含 chapters / text）。

        取单篇也要用 `WHERE id=%s`，不能 `docs_all()` 回来线性扫描 ——
        后者是 O(N)，而 ID 前缀（doc-YYYYMMDD-N）本身就有序，
        加个索引即可。
        """
        raise NotImplementedError

    def drafts_all(self):
        raise NotImplementedError

    # ---------------- 写：卡片 ----------------
    def custom_put(self, card):
        raise NotImplementedError

    def custom_del(self, cid):
        raise NotImplementedError

    def custom_replace(self, lst):
        raise NotImplementedError

    # ---------------- 写：进度 ----------------
    def progress_put(self, cid, rec, user_id=None):
        raise NotImplementedError

    def progress_del(self, cid, user_id=None):
        raise NotImplementedError

    def progress_clear(self, user_id=None):
        """`user_id=None` 只清匿名桶；要清所有人得显式传 `user_id='*'`。"""
        raise NotImplementedError

    # ---------------- 写：笔记 ----------------
    def note_put(self, note, user_id=None):
        raise NotImplementedError

    def note_del(self, nid, user_id=None):
        raise NotImplementedError

    # ---------------- 写/读：聊天消息 ----------------
    def chat_all(self, user_id=None, limit=200):
        """按时间倒序取最近 limit 条（用于刷新恢复）"""
        raise NotImplementedError

    def chat_put(self, msg, user_id=None):
        """写一条消息（新建或更新）。"""
        raise NotImplementedError

    def chat_del(self, msg_id, user_id=None):
        raise NotImplementedError

    def chat_clear(self, user_id=None):
        raise NotImplementedError

    # ---------------- 写：文档 ----------------
    def doc_put(self, doc):
        raise NotImplementedError

    def doc_del(self, did):
        raise NotImplementedError

    # ---------------- 写：草稿 ----------------
    def draft_replace(self, lst):
        raise NotImplementedError

    # ---------------- 用户 ----------------
    # 为什么要放存储层而不是直接读文件：MySQL 后端下 users 是一张表，
    # JSON 后端下是一个文件 —— 业务层不该知道这个区别。
    # 同时这也是 BKT 的前置条件：掌握度是 per-user 的，没有稳定的 user_id
    # 就没法给「每个人」建学习者模型。
    def user_all(self, with_secret=False):
        """全部用户。**默认剔除口令哈希**，`with_secret=True` 才原样返回。

        ★ 参数必须写进契约：两个后端从前对它的处理是**相反**的 ——
        mysql 默认剔除 password_hash、json 完全忽略这个参数原样吐出来，
        而签名里连参数都没有。契约里不写，下一个实现就会再写歪一次。
        出口这一层（db.public_user）确实兜住了口令哈希，但不能靠「下游
        记得兜」来做安全 —— 任何一次「顺手 return 上游对象」都会漏。
        内部需要哈希的调用方（登录校验、口令迁移）显式传 True。
        """
        raise NotImplementedError

    def user_by_name(self, username):
        """按用户名查（大小写不敏感）。返回 dict 或 None。"""
        raise NotImplementedError

    def user_get(self, uid):
        raise NotImplementedError

    def user_put(self, user):
        """新建或更新用户，**返回 id**。

        返回值是硬要求：JSON 后端没有 AUTO_INCREMENT，id 得自己发（现有最大 +1）；
        MySQL 后端靠 LAST_INSERT_ID()。两个后端都必须返回，否则
        `db.create_user` 拿到 None，签发出来的 token 里 sub 就是字符串 "None" ——
        表面看注册成功，实际上刷新一下就掉登录，且日志里没有任何错误。
        """
        raise NotImplementedError

    def user_count(self):
        raise NotImplementedError

    # ---------------- 状态 ----------------
    def info(self):
        """给 /api/health 和 /api/storage 看的运行时状态。不要塞敏感信息。"""
        return {'store': self.name}

    def close(self):
        pass


# ---------------------------------------------------------------- JSON 工具
# JSON 后端用，MySQL 后端拼 payload 时也用。放基类文件里当公共工具，
# 免得两个后端各写一份（各写一份的下场是缩进/ensure_ascii 不一致，
# 于是 diff 里每次都是全文件改动）。
def read_json(path, fallback, ensure_dir=None):
    try:
        if not os.path.exists(path):
            return fallback
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:                      # 文件损坏时不要让服务崩掉
        print('[store] 读取失败，回退默认值 %s: %s' % (path, e), file=sys.stderr)
        return fallback


def write_json(path, obj, ensure_dir=None):
    d = ensure_dir or os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        # 2026-11-15 补 fsync：os.replace 只保证「替换这个动作是原子的」，
        # 不保证 tmp 的内容真的落了盘 —— 掉电时可能 replace 成功了、
        # 内容却是空的/半截（写回缓存作怪）。flush + fsync 先把内容钉到
        # 磁盘再 replace。代价是每次写多一次盘寻，而这里的写都是人工操作
        # 量级（标记一张卡 / 存一条笔记），换得起。
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)                       # 原子替换：写一半崩溃不留坏文件


def json_dumps(obj):
    """写进 MySQL JSON 列时的统一序列化。ensure_ascii=False 是为了让人
    在 Navicat / Workbench 里直接看得懂中文，不然满屏 \\u4e2d\\u6587。"""
    return json.dumps(obj, ensure_ascii=False)


def json_loads(raw, fallback=None):
    """MySQL JSON 列读回来。可能是 str / bytes / 已经是 dict（驱动会自作主张）。"""
    if raw is None:
        return fallback
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode('utf-8', 'ignore')
    try:
        return json.loads(raw)
    except Exception:
        return fallback
