# -*- coding: utf-8 -*-
"""MySQL 后端（MySQL 8.0+，驱动 pymysql）。

**这一层为什么值得存在**：到期队列在文件后端是「把全部卡读进内存 → 逐张
比对进度 → Python 排序」，卡一多就是纯浪费。到了 MySQL 里它是一条
LEFT JOIN + ORDER BY，next_at 上有索引，卡数从 20 涨到 20000 是同一个写法。
这才是引入数据库的意义 —— 不是换个地方存 JSON。

**线程安全**：pymysql 的连接不能跨线程共用。FastAPI 把同步端点丢进线程池，
所以这里用 thread-local 连接 + ping(reconnect)。别改成模块级单例连接，
那会在并发几秒后随机报 "Packet sequence number wrong"。
"""
import hashlib
import json
import sys
import threading

from .base import Store, json_dumps, json_loads

# ---------------------------------------------------------------------------
# DDL。与 schema.sql 是同一套语句，改一处记得改另一处
# （schema.sql 是给人读的版本，这里是程序执行的版本）
# ---------------------------------------------------------------------------
DDL_DATABASE = (
    "CREATE DATABASE IF NOT EXISTS `{db}` "
    "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
)

DDL_TABLES = [
    """CREATE TABLE IF NOT EXISTS `cards` (
      `id`          VARCHAR(96)  NOT NULL,
      `origin`      VARCHAR(16)  NOT NULL DEFAULT 'builtin',
      `category`    VARCHAR(48)  NOT NULL DEFAULT '',
      `subject`     VARCHAR(48)  NOT NULL DEFAULT '',
      `domain`      VARCHAR(48)  NOT NULL DEFAULT '',
      `topic_path`  JSON             NULL,
      `title`       VARCHAR(255) NOT NULL DEFAULT '',
      `one_line`    VARCHAR(512) NOT NULL DEFAULT '',
      `src_file`    VARCHAR(96)  NOT NULL DEFAULT '',
      `payload`     JSON         NOT NULL,
      `fingerprint` CHAR(16)     NOT NULL DEFAULT '',
      `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      KEY `ix_cards_origin` (`origin`),
      KEY `ix_cards_scope`  (`category`, `subject`),
      KEY `ix_cards_domain` (`domain`),
      KEY `ix_cards_fp`     (`fingerprint`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS `progress` (
      `card_id`    VARCHAR(96)  NOT NULL,
      `level`      TINYINT      NOT NULL DEFAULT 0,
      `interval_d` INT          NOT NULL DEFAULT 0,
      `ef`         DECIMAL(4,2) NOT NULL DEFAULT 2.50,
      `reps`       INT          NOT NULL DEFAULT 0,
      `next_at`    DATE             NULL,
      `updated_at` DATE             NULL,
      PRIMARY KEY (`card_id`),
      KEY `ix_progress_due`   (`next_at`),
      KEY `ix_progress_level` (`level`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS `notes` (
      `id`         VARCHAR(96)  NOT NULL,
      `card_id`    VARCHAR(96)      NULL,
      `category`   VARCHAR(48)  NOT NULL DEFAULT '',
      `subject`    VARCHAR(48)  NOT NULL DEFAULT '',
      `title`      VARCHAR(255) NOT NULL DEFAULT '',
      `body`       MEDIUMTEXT       NULL,
      `tags`       JSON             NULL,
      `created_at` DATE             NULL,
      `updated_at` DATE             NULL,
      PRIMARY KEY (`id`),
      KEY `ix_notes_card`    (`card_id`),
      KEY `ix_notes_scope`   (`category`, `subject`),
      KEY `ix_notes_updated` (`updated_at`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS `documents` (
      `id`          VARCHAR(96)  NOT NULL,
      `title`       VARCHAR(255) NOT NULL DEFAULT '',
      `source`      VARCHAR(255) NOT NULL DEFAULT '',
      `category`    VARCHAR(48)  NOT NULL DEFAULT '',
      `subject`     VARCHAR(48)  NOT NULL DEFAULT '',
      `domain`      VARCHAR(48)  NOT NULL DEFAULT '',
      `chapters`    JSON             NULL,
      `parse`       JSON             NULL,
      `ai_done`     INT          NOT NULL DEFAULT 0,
      `ai_total`    INT          NOT NULL DEFAULT 0,
      `ai_model`    VARCHAR(96)  NOT NULL DEFAULT '',
      `ai_provider` VARCHAR(32)  NOT NULL DEFAULT '',
      `created_at`  DATE             NULL,
      `updated_at`  DATE             NULL,
      PRIMARY KEY (`id`),
      KEY `ix_docs_scope` (`category`, `subject`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS `drafts` (
      `id`         VARCHAR(96)  NOT NULL,
      `title`      VARCHAR(255) NOT NULL DEFAULT '',
      `payload`    JSON         NOT NULL,
      `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS `meta` (
      `k` VARCHAR(48)  NOT NULL,
      `v` VARCHAR(255) NOT NULL DEFAULT '',
      PRIMARY KEY (`k`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 用户表。目前只有「用户名 + 密码」一种登录方式；
    # openid 列留着是为了将来接微信登录时把 openid 写到同一行即可，不用改表。
    #
    # 用户名唯一索引**天然大小写不敏感** —— 建库时用的是 utf8mb4_general_ci，
    # 所以 Wangtong 和 wangtong 会撞唯一键，正好和 JSON 后端 lower() 的行为对上。
    # 两版存储在这点上不一致的话，用 MySQL 时能注册两个「同名」用户，
    # 换回 JSON 就只剩一个，这种 bug 极难查。
    """CREATE TABLE IF NOT EXISTS `users` (
      `id`            INT          NOT NULL AUTO_INCREMENT,
      `username`      VARCHAR(32)  NOT NULL DEFAULT '',
      `password_hash` VARCHAR(160) NOT NULL DEFAULT '',
      `display_name`  VARCHAR(64)  NOT NULL DEFAULT '',
      `role`          VARCHAR(16)  NOT NULL DEFAULT 'user',
      `openid`        VARCHAR(64)      NULL,
      `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uq_users_name` (`username`),
      UNIQUE KEY `uq_users_openid` (`openid`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]

#: 中文全文索引。ngram 分词器是内置的，但极精简的发行版可能没带，
#: 所以单独建、失败只记一笔，不让它拖垮初始化。
DDL_FULLTEXT = ("CREATE FULLTEXT INDEX `ft_cards` ON `cards` "
                "(`title`, `one_line`) WITH PARSER ngram")

KEY_FINGERPRINT = 'builtin.fingerprint'


# ---------------------------------------------------------------------------
# 指纹：判断库里灌的内置卡跟 data/*.js 是否一致。
# 用 md5 而不是时间戳 —— 内容没变就不该触发重灌（改了注释、存盘动作
# 都会动 mtime，用 mtime 判会天天提示「已过期」，喊多了就没人看了）。
# ---------------------------------------------------------------------------
def card_fingerprint(card):
    body = {k: v for k, v in card.items() if not k.startswith('_')}
    raw = json_dumps_body(body)
    return hashlib.md5(raw.encode('utf-8')).hexdigest()[:16]


def json_dumps_body(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def cards_digest(cards):
    """整批卡的指纹 = 各卡指纹排序后拼起来再哈希。顺序无关，
    这样 data/*.js 里调换两张卡的位置不会误判成内容变了。"""
    h = hashlib.md5()
    for fp in sorted(card_fingerprint(c) for c in cards):
        h.update(fp.encode('ascii'))
    return h.hexdigest()[:16]


class MySQLStore(Store):

    name = 'mysql'
    holds_builtin = True

    def __init__(self, host='127.0.0.1', port=3306, user='root', password='',
                 db='study_cards', connect_timeout=5):
        import pymysql                                   # 延迟导入：只有选了 mysql 才需要它
        import pymysql.cursors
        self._pymysql = pymysql
        self.cfg = dict(host=host, port=int(port), user=user, password=password,
                        database=db, charset='utf8mb4',
                        cursorclass=pymysql.cursors.DictCursor,
                        connect_timeout=int(connect_timeout), autocommit=True)
        self._local = threading.local()
        self._lock = threading.Lock()

    # ---------------- 连接 ----------------
    def _conn(self):
        c = getattr(self._local, 'conn', None)
        if c is not None:
            try:
                c.ping(reconnect=True)                   # 长连接被 MySQL 掐掉后自动重连
                return c
            except Exception:
                # ping 失败说明这条连接已经废了，close() 再报错也无所谓 ——
                # 下面会新建一条，所以这里静默丢弃是安全的（不是"吞异常"）。
                try:
                    c.close()
                except Exception:
                    pass
                self._local.conn = None
        c = self._pymysql.connect(**self.cfg)
        self._local.conn = c
        return c

    def _q(self, sql, args=None, fetch=False):
        with self._conn().cursor() as cur:
            cur.execute(sql, args or ())
            return cur.fetchall() if fetch else cur.rowcount

    def _one(self, sql, args=None):
        r = self._q(sql, args, fetch=True)
        return r[0] if r else None

    def ping(self):
        self._q('SELECT 1')
        return True

    def ping_server(self):
        """只探 MySQL 服务本身，**不碰具体库**。

        与 ping() 的区别很重要：库还没建的时候，带 database 参数的连接会直接
        报 1049 Unknown database —— 但初始化脚本要的正是「连上服务，然后建库」。
        """
        cfg = dict(self.cfg)
        cfg.pop('database')
        cfg.pop('cursorclass')
        cfg.pop('charset', None)
        conn = self._pymysql.connect(charset='utf8mb4', **cfg)
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT VERSION()')
                r = cur.fetchone()
                return (r[0] if isinstance(r, (tuple, list)) else r) if r else None
        finally:
            conn.close()

    # ---------------- 建库建表 ----------------
    def init_schema(self):
        """建库 + 建表 + 建中文全文索引。已存在则原样跳过，可重复执行。"""
        cfg = dict(self.cfg)
        dbname = cfg.pop('database')
        cfg.pop('cursorclass')
        boot = self._pymysql.connect(**cfg)
        try:
            with boot.cursor() as cur:
                cur.execute(DDL_DATABASE.format(db=dbname))
        finally:
            boot.close()
        for ddl in DDL_TABLES:
            self._q(ddl)
        added = self._migrate_schema(dbname)
        # FULLTEXT 单独试，失败不影响其它表
        has = self._one("""SELECT COUNT(*) AS n FROM information_schema.STATISTICS
                           WHERE TABLE_SCHEMA=%s AND TABLE_NAME='cards'
                             AND INDEX_NAME='ft_cards'""", (dbname,))
        if not has or not has['n']:
            try:
                self._q(DDL_FULLTEXT)
                return {'fulltext': True, 'added': added}
            except Exception as e:
                return {'fulltext': False, 'fulltextError': str(e)[:120],
                        'added': added}
        return {'fulltext': True, 'added': added}

    #: 后加的列。`CREATE TABLE IF NOT EXISTS` 对**已存在的表**不会改动它，
    #: 所以给老库补列必须显式 ALTER —— 不然新代码读一个不存在的列当场就炸，
    #: 而「服务正常起、一点文档列表就 500」是最难联想到建表的那类故障。
    #: 格式：表名 → [(列名, 列定义)]
    _ADDED_COLUMNS = (
        ('documents', 'stats', 'JSON NULL'),
        ('documents', 'parse', 'JSON NULL'),
    )

    def _migrate_schema(self, dbname):
        """幂等补列：缺哪列补哪列，返回补了哪些（给启动横幅用）。"""
        done = []
        for table, col, definition in self._ADDED_COLUMNS:
            row = self._one("""SELECT COUNT(*) AS n FROM information_schema.COLUMNS
                               WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
                                 AND COLUMN_NAME=%s""", (dbname, table, col))
            if row and row['n']:
                continue
            try:
                self._q('ALTER TABLE `%s` ADD COLUMN `%s` %s' % (table, col, definition))
                done.append('%s.%s' % (table, col))
            except Exception as e:
                # 补列失败不该拦启动：老库能用就先用，横幅会打出来
                sys.stderr.write('[store] 补列 %s.%s 失败：%s\n'
                                 % (table, col, str(e)[:120]))
        return done

    # ---------------- 读 ----------------
    def builtin_all(self):
        rows = self._q("SELECT payload FROM cards WHERE origin='builtin'",
                       fetch=True)
        return [json_loads(r['payload'], {}) for r in rows]

    def custom_all(self):
        rows = self._q("SELECT payload FROM cards WHERE origin='custom'", fetch=True)
        out = []
        for r in rows:
            c = json_loads(r['payload'], {})
            c['_custom'] = True                          # 与文件后端保持同一标记
            out.append(c)
        return out

    def progress_all(self):
        rows = self._q('SELECT * FROM progress', fetch=True)
        out = {}
        for r in rows:
            out[r['card_id']] = {
                'level': int(r['level'] or 0),
                'interval': int(r['interval_d'] or 0),
                # DECIMAL 取回来是 decimal.Decimal，必须转 float，
                # 否则 json.dumps 会直接抛 TypeError（接口 500）
                'ef': float(r['ef']) if r['ef'] is not None else 2.5,
                'reps': int(r['reps'] or 0),
                'nextAt': _dstr(r['next_at']),
                'updatedAt': _dstr(r['updated_at']),
            }
        return out

    def notes_all(self):
        rows = self._q('SELECT * FROM notes ORDER BY updated_at DESC, id', fetch=True)
        return [_note_of(r) for r in rows]

    def docs_all(self):
        rows = self._q('SELECT * FROM documents', fetch=True)
        return [_doc_of(r) for r in rows]

    def drafts_all(self):
        return [json_loads(r['payload'], {})
                for r in self._q('SELECT payload FROM drafts ORDER BY created_at, id',
                                 fetch=True)]

    # ---------------- 到期队列：这条 SQL 是上数据库的主要理由 ----------------
    def due_cards(self, category=None, subject=None, domain=None, include_all=False):
        """一次 JOIN 出「卡 + 进度 + 逾期天数」，且已按复习优先级排好。

        排序规则与 db.due_list 里那份 Python 实现必须一致：
            不会(1) → 模糊(2) → 未标记(0) → 会(3)，同档里逾期久的在前。
        未标记的卡 next_at 是 NULL，让它排在同档最前（对应 Python 里的 999 哨兵）。
        """
        w, a = ["c.origin IN ('builtin','custom')"], []
        if category:
            w.append('c.category=%s'); a.append(category)
        if subject:
            w.append('c.subject=%s'); a.append(subject)
        if domain:
            w.append('c.domain=%s'); a.append(domain)
        if not include_all:
            # 没标记过（LEFT JOIN 落空）算「待学」，永远在队列里
            w.append('(p.card_id IS NULL OR p.next_at <= CURDATE())')
        # 拼进 WHERE 的每一片都是这里的字面量，值一律走 %s 占位符由驱动转义 ——
        # 所以 `' AND '.join(w)` 这个拼接是安全的。**加条件时只加字面量字符串，
        # 不要把参数值 f-string 进来**（列名也不可能来自外部：只有上面四个 if）。
        sql = """
            SELECT c.payload, c.id AS cid,
                   p.card_id AS p_cid, p.level, p.interval_d, p.ef, p.reps,
                   p.next_at, p.updated_at,
                   CASE WHEN p.next_at IS NULL THEN NULL
                        ELSE DATEDIFF(CURDATE(), p.next_at) END AS overdue
            FROM cards c
            LEFT JOIN progress p ON p.card_id = c.id
            WHERE %s
            ORDER BY FIELD(COALESCE(p.level, 0), 1, 2, 0, 3),
                     (p.card_id IS NULL) DESC,
                     DATEDIFF(CURDATE(), p.next_at) DESC,
                     c.id
        """ % ' AND '.join(w)
        out = []
        for r in self._q(sql, a, fetch=True):
            card = json_loads(r['payload'], {})
            prog = None
            if r['p_cid']:
                prog = {'level': int(r['level'] or 0),
                        'interval': int(r['interval_d'] or 0),
                        'ef': float(r['ef']) if r['ef'] is not None else 2.5,
                        'reps': int(r['reps'] or 0),
                        'nextAt': _dstr(r['next_at']),
                        'updatedAt': _dstr(r['updated_at'])}
            out.append({'card': card, 'progress': prog,
                        'level': prog['level'] if prog else 0,
                        # None = 从没复习过，由上层翻译成 999 哨兵值
                        'overdue': None if r['overdue'] is None else int(r['overdue']),
                        'due': True})
        return out

    # ---------------- 写：卡片 ----------------
    def custom_put(self, card):
        self._upsert_card(card, 'custom')

    def custom_del(self, cid):
        self._q("DELETE FROM cards WHERE id=%s AND origin='custom'", (cid,))

    def custom_replace(self, lst):
        """接口里的 PUT/DELETE 是「读全量 → 改 → 写全量」的写法，
        这里做增量对齐：多余的行删掉、来的行 upsert。
        比整表 DELETE+INSERT 安全（中途失败不会把数据清空）。"""
        keep = [c.get('id') for c in lst]
        rows = self._q("SELECT id FROM cards WHERE origin='custom'", fetch=True)
        old = [r['id'] for r in rows]
        for cid in old:
            if cid not in keep:
                self.custom_del(cid)
        for c in lst:
            self.custom_put(c)

    def _upsert_card(self, card, origin):
        c = dict(card)
        c.pop('_custom', None)
        path = c.get('topicPath') or []
        self._q("""
            INSERT INTO cards (id, origin, category, subject, domain, topic_path,
                               title, one_line, src_file, payload, fingerprint)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              origin=VALUES(origin), category=VALUES(category),
              subject=VALUES(subject), domain=VALUES(domain),
              topic_path=VALUES(topic_path), title=VALUES(title),
              one_line=VALUES(one_line), src_file=VALUES(src_file),
              payload=VALUES(payload), fingerprint=VALUES(fingerprint)
        """, (c.get('id'), origin, c.get('category') or '', c.get('subject') or '',
              c.get('domain') or '', json_dumps(path) if path else None,
              (c.get('title') or '')[:255], (c.get('oneLine') or '')[:512],
              c.get('_src') or '', json_dumps(c),
              card_fingerprint(card)))

    # ---------------- 写：进度 ----------------
    def progress_put(self, cid, rec):
        self._q("""
            INSERT INTO progress (card_id, level, interval_d, ef, reps, next_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              level=VALUES(level), interval_d=VALUES(interval_d), ef=VALUES(ef),
              reps=VALUES(reps), next_at=VALUES(next_at), updated_at=VALUES(updated_at)
        """, (cid, int(rec.get('level') or 0), int(rec.get('interval') or 0),
              float(rec.get('ef') or 2.5), int(rec.get('reps') or 0),
              rec.get('nextAt') or None, rec.get('updatedAt') or None))

    def progress_del(self, cid):
        self._q('DELETE FROM progress WHERE card_id=%s', (cid,))

    def progress_clear(self):
        self._q('DELETE FROM progress')

    # ---------------- 写：笔记 ----------------
    def note_put(self, note):
        n = dict(note)
        self._q("""
            INSERT INTO notes (id, card_id, category, subject, title, body, tags,
                               created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              card_id=VALUES(card_id), category=VALUES(category),
              subject=VALUES(subject), title=VALUES(title), body=VALUES(body),
              tags=VALUES(tags), updated_at=VALUES(updated_at)
        """, (n.get('id'), n.get('cardId') or None, n.get('category') or '',
              n.get('subject') or '', (n.get('title') or '')[:255],
              n.get('body') or '', json_dumps(n.get('tags') or []),
              n.get('createdAt') or None, n.get('updatedAt') or None))

    def note_del(self, nid):
        self._q('DELETE FROM notes WHERE id=%s', (nid,))

    # ---------------- 写：文档 ----------------
    def doc_put(self, doc):
        d = dict(doc)
        self._q("""
            INSERT INTO documents (id, title, source, category, subject, domain,
                                   chapters, stats, parse, ai_done, ai_total, ai_model,
                                   ai_provider, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              title=VALUES(title), source=VALUES(source), category=VALUES(category),
              subject=VALUES(subject), domain=VALUES(domain),
              chapters=VALUES(chapters), stats=VALUES(stats), parse=VALUES(parse),
              ai_done=VALUES(ai_done),
              ai_total=VALUES(ai_total), ai_model=VALUES(ai_model),
              ai_provider=VALUES(ai_provider), updated_at=VALUES(updated_at)
        """, (d.get('id'), (d.get('title') or '')[:255], (d.get('source') or '')[:255],
              d.get('category') or '', d.get('subject') or '', d.get('domain') or '',
              json_dumps(d.get('chapters') or []),
              # ★ stats 必须存：importer.parse_document 明确产出
              # {chapters, chars, headings}，routers/docs.py 透给前端，
              # 前端文档列表显示「N 章 · M 字」。从前这一列不存在 →
              # 存进 MySQL 就没了 → 列表恒显示「0 章 · 0 字」。
              # 首页「已经入库的文档」也跟着少一块信息。
              json_dumps(d.get('stats')),
              json_dumps(d.get('parse')) if d.get('parse') else None,
              int(d.get('aiDone') or 0), int(d.get('aiTotal') or 0),
              (d.get('aiModel') or '')[:96], (d.get('aiProvider') or '')[:32],
              d.get('createdAt') or None, d.get('updatedAt') or None))

    def doc_del(self, did):
        self._q('DELETE FROM documents WHERE id=%s', (did,))

    # ---------------- 写：草稿 ----------------
    def draft_replace(self, lst):
        keep = [d.get('id') for d in lst]
        for r in self._q('SELECT id FROM drafts', fetch=True):
            if r['id'] not in keep:
                self._q('DELETE FROM drafts WHERE id=%s', (r['id'],))
        for d in lst:
            self._q("""INSERT INTO drafts (id, title, payload) VALUES (%s,%s,%s)
                       ON DUPLICATE KEY UPDATE title=VALUES(title),
                                               payload=VALUES(payload)""",
                    (d.get('id'), (d.get('title') or '')[:255], json_dumps(d)))

    # ---------------- 内置卡：灌种子 / 查过期 ----------------
    def get_meta(self, k, default=''):
        r = self._one('SELECT v FROM meta WHERE k=%s', (k,))
        return r['v'] if r else default

    def set_meta(self, k, v):
        self._q("""INSERT INTO meta (k, v) VALUES (%s,%s)
                   ON DUPLICATE KEY UPDATE v=VALUES(v)""", (k, str(v)[:255]))

    def seed_builtin(self, cards, force=False):
        """把 data/*.js 里的内置卡灌进 cards 表。

        不是每次启动都灌：先比整批指纹，一致就跳过（20 张卡无所谓，
        2000 张卡每次都重写就是灾难）。`force=True` 强制重灌。

        删掉的行也要处理 —— 卡从 data/*.js 里删掉后，库里那份不该留着，
        否则接口会返回一张「源码里已经不存在」的卡。
        """
        digest = cards_digest(cards)
        if not force and self.get_meta(KEY_FINGERPRINT) == digest:
            return {'seeded': 0, 'removed': 0, 'digest': digest, 'skipped': True}

        keep = set()
        for c in cards:
            if not c.get('id'):
                continue
            keep.add(c['id'])
            self._upsert_card(c, 'builtin')

        removed = 0
        for r in self._q("SELECT id FROM cards WHERE origin='builtin'", fetch=True):
            if r['id'] not in keep:
                self._q('DELETE FROM cards WHERE id=%s', (r['id'],))
                removed += 1

        # 内置卡没了，它的进度/关联笔记也该清掉，否则 progress 表会一直
        # 留着一堆指向不存在卡片的孤儿行，统计口径跟着错
        if removed:
            self._q("""DELETE p FROM progress p
                       LEFT JOIN cards c ON c.id = p.card_id
                       WHERE c.id IS NULL""")
        self.set_meta(KEY_FINGERPRINT, digest)
        return {'seeded': len(keep), 'removed': removed, 'digest': digest,
                'skipped': False}

    def builtin_stale(self, cards):
        return self.get_meta(KEY_FINGERPRINT) != cards_digest(cards)

    # ---------------- 用户 ----------------
    @staticmethod
    def _user_of(row, with_secret=True):
        """列名 → dict 的转换只在这里发生，和其他实体（_note_of / _doc_of）同一套做法。

        对外一律 camelCase，与卡片 JSON 的风格一致 —— 存储层不改名，
        但「列名 snake_case」是 SQL 的惯例，这两件事得有人接一下，
        这个函数就是那个接头。
        """
        if not row:
            return None
        c = row.get('created_at')
        if hasattr(c, 'strftime'):
            # 带时分秒：注册时间是排查问题时要看的，只留日期不够用
            c = c.strftime('%Y-%m-%d %H:%M:%S')
        elif c is not None:
            c = str(c)
        out = {
            'id': row['id'],
            'username': row['username'] or '',
            'displayName': row['display_name'] or '',
            'role': row['role'] or 'user',
            'openid': row['openid'],
            'createdAt': c,
        }
        if with_secret:
            out['passwordHash'] = row['password_hash'] or ''
        return out

    def user_all(self, with_secret=False):
        # 默认不带 password_hash：列表接口没有任何理由拿到它，
        # 少一个字段就少一条泄露路径
        if with_secret:
            rows = self._q('SELECT * FROM `users` ORDER BY `id`', fetch=True)
        else:
            rows = self._q('SELECT `id`,`username`,`display_name`,`role`,`openid`,'
                           '`created_at` FROM `users` ORDER BY `id`', fetch=True)
        return [self._user_of(r, with_secret=with_secret) for r in rows]

    def user_by_name(self, username):
        key = (username or '').strip()
        if not key:
            return None
        # 建库用的是 utf8mb4_general_ci，等值比较天然忽略大小写，
        # 与 JSON 后端 lower() 的语义一致
        return self._user_of(self._one(
            'SELECT * FROM `users` WHERE `username`=%s', (key,)))

    def user_get(self, uid):
        try:
            uid = int(uid)
        except (TypeError, ValueError):
            return None
        return self._user_of(self._one('SELECT * FROM `users` WHERE `id`=%s', (uid,)))

    def user_count(self):
        r = self._one('SELECT COUNT(*) AS n FROM `users`')
        return int(r['n']) if r else 0

    #: (列名, dict 里的键)。user_put 靠它做双向映射，
    #: 免得在上面的 _user_of 和这里各写一份字段清单（两份必然会漏一个）
    _USER_MAP = (
        ('username', 'username'),
        ('password_hash', 'passwordHash'),
        ('display_name', 'displayName'),
        ('role', 'role'),
        ('openid', 'openid'),
    )

    def user_put(self, user):
        """有 id 就更新，没有就新建并回填 id。

        LAST_INSERT_ID() 必须在同一个连接上取才有意义 —— 好在 _conn()
        是 thread-local 的，同线程拿到的就是同一个连接。
        """
        cols = [c for c, _ in self._USER_MAP]
        vals = tuple(user.get(k) for _, k in self._USER_MAP)
        uid = user.get('id')

        if uid:
            sets = ', '.join('`%s`=%%s' % c for c in cols)
            self._q('UPDATE `users` SET %s WHERE `id`=%%s' % sets,
                    vals + (int(uid),))
            return int(uid)

        marks = ', '.join(['%s'] * len(cols))
        self._q('INSERT INTO `users` (%s) VALUES (%s)'
                % (', '.join('`%s`' % c for c in cols), marks), vals)
        r = self._one('SELECT LAST_INSERT_ID() AS id')
        return int(r['id']) if r else None

    # ---------------- 状态 ----------------
    def info(self):
        out = {'store': self.name,
               'db': self.cfg.get('database'),
               'host': self.cfg.get('host'),
               'port': self.cfg.get('port'),
               'user': self.cfg.get('user')}
        try:
            out['version'] = self._one('SELECT VERSION() AS v')['v']
            # 表名是**写死在这个元组里的**，不来自任何外部输入，所以 % 拼接安全
            # （值类型的参数一律走 %s 占位符）。加表时这里和 DDL / 必需表探测一起改。
            for t in ('cards', 'progress', 'notes', 'documents', 'drafts', 'users'):
                out[t] = self._one('SELECT COUNT(*) AS n FROM `%s`' % t)['n']
            out['builtinDigest'] = self.get_meta(KEY_FINGERPRINT)
            out['ok'] = True
        except Exception as e:
            out['ok'] = False
            out['error'] = str(e)[:160]
        return out


# ---------------------------------------------------------------- 行 → dict
def _dstr(v):
    if v is None:
        return None
    return v.strftime('%Y-%m-%d') if hasattr(v, 'strftime') else str(v)


def _note_of(r):
    n = {'id': r['id'],
         'title': r['title'] or '',
         'body': r['body'] or '',
         'tags': json_loads(r['tags'], []),
         'createdAt': _dstr(r['created_at']),
         'updatedAt': _dstr(r['updated_at'])}
    if r['card_id']:
        n['cardId'] = r['card_id']
    if r['category']:
        n['category'] = r['category']
    if r['subject']:
        n['subject'] = r['subject']
    return n


def _doc_of(r):
    d = {'id': r['id'],
         'title': r['title'] or '',
         'source': r['source'] or '',
         'chapters': json_loads(r['chapters'], []),
         # stats 回填。用 r.get 是因为**老库可能还没补上这一列**
         # （补列由 init_schema 的 _migrate_schema 做，但要允许它失败），
         # 缺列时给 None，与 json 后端「没有 stats 就是没有」一致。
         'stats': json_loads(r.get('stats'), None),
         # parse = 内容解析报告（{at,modelOk,msg,chapters}）。老库补列前
         # r.get('parse') 是 None → 不写进 dict，与 json 后端「没有就没有」一致。
         'parse': json_loads(r.get('parse'), None),
         'aiDone': int(r['ai_done'] or 0),
         'aiTotal': int(r['ai_total'] or 0),
         'createdAt': _dstr(r['created_at']),
         'updatedAt': _dstr(r['updated_at'])}
    for k, src in (('category', 'category'), ('subject', 'subject'),
                   ('domain', 'domain'), ('aiModel', 'ai_model'),
                   ('aiProvider', 'ai_provider')):
        if r[src]:
            d[k] = r[src]
    return d
