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

#: 个人数据的用户桶。真实 uid 一律 str 化：MySQL 侧 id 是 int
#: （用户表自增），JSON 侧是字符串，不统一就会变成'1' 和 1 两份数据。
ANON = ''


def _uid(user_id):
    return ANON if user_id is None else str(user_id)


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
      `user_id`    VARCHAR(64)  NOT NULL DEFAULT '',
      `card_id`    VARCHAR(96)  NOT NULL,
      `level`      TINYINT      NOT NULL DEFAULT 0,
      `interval_d` INT          NOT NULL DEFAULT 0,
      `ef`         DECIMAL(4,2) NOT NULL DEFAULT 2.50,
      `reps`       INT          NOT NULL DEFAULT 0,
      `next_at`    DATE             NULL,
      `updated_at` DATE             NULL,
      PRIMARY KEY (`user_id`, `card_id`),
      KEY `ix_progress_due`   (`user_id`, `next_at`),
      KEY `ix_progress_level` (`user_id`, `level`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS `notes` (
      `id`         VARCHAR(96)  NOT NULL,
      `user_id`    VARCHAR(64)  NOT NULL DEFAULT '',
      `card_id`    VARCHAR(96)      NULL,
      `category`   VARCHAR(48)  NOT NULL DEFAULT '',
      `subject`    VARCHAR(48)  NOT NULL DEFAULT '',
      `title`      VARCHAR(255) NOT NULL DEFAULT '',
      `body`       MEDIUMTEXT       NULL,
      `tags`       JSON             NULL,
      `created_at` DATE             NULL,
      `updated_at` DATE             NULL,
      PRIMARY KEY (`user_id`, `id`),
      KEY `ix_notes_card`    (`user_id`, `card_id`),
      KEY `ix_notes_scope`   (`user_id`, `category`, `subject`),
      KEY `ix_notes_updated` (`user_id`, `updated_at`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS `documents` (
      `id`          VARCHAR(96)  NOT NULL,
      `title`       VARCHAR(255) NOT NULL DEFAULT '',
      `source`      VARCHAR(255) NOT NULL DEFAULT '',
      `category`    VARCHAR(48)  NOT NULL DEFAULT '',
      `subject`     VARCHAR(48)  NOT NULL DEFAULT '',
      `domain`      VARCHAR(48)  NOT NULL DEFAULT '',
      `chapters`    JSON             NULL,
      `tags`        JSON             NULL,
      `raw_file`    VARCHAR(255) NOT NULL DEFAULT '',
      `is_paper`    TINYINT      NOT NULL DEFAULT 0,
      `doc_text`    MEDIUMTEXT        NULL,
      `tree`       JSON             NULL,
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
      -- ★ 2026-10-11 由 VARCHAR(255) 放宽到 TEXT：知识库的文件夹树整个存在
      --   meta.kb_tree 这一行里，255 字符连三层节点名都放不下。
      --   改列类型是 DDL 里唯一不能「加列」解决的一类，必须显式 ALTER。
      --   用 TEXT 而不是 JSON 是因为 meta 是**字符串**键值表，
      --   塞结构化数据进来只会让两个后端（json/mysql）的读写语义不一致。
      `v` TEXT            NOT NULL,
      PRIMARY KEY (`k`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS `chat_messages` (
      `id`          VARCHAR(96)  NOT NULL,
      `user_id`     VARCHAR(64)  NOT NULL DEFAULT '',
      `role`        VARCHAR(16)  NOT NULL,
      `text`        MEDIUMTEXT      NULL,
      `sources`     JSON            NULL,
      `steps`       JSON            NULL,
      `verify`      JSON            NULL,
      `status`      VARCHAR(16)  NOT NULL DEFAULT 'done',
      `mode`        VARCHAR(16)  NOT NULL DEFAULT 'flow',
      `web_search`  TINYINT(1)     NOT NULL DEFAULT 0,
      `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`user_id`, `id`),
      KEY `ix_chat_updated` (`user_id`, `updated_at`)
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
    # ★ 与 schema.sql 保持逐字一致。schema.sql 是给人读的、mysql.py 这份是
    #   给程序跑的 —— 两处不同步时症状极怪：新建的库少一张表，
    #   而老库（先有 schema.sql 后加的这张）反而一路正常，直到写译文才炸。
    """CREATE TABLE IF NOT EXISTS `doc_translations` (
      `doc_id`     VARCHAR(96) NOT NULL,
      `seg_i`      INT         NOT NULL,
      `src_hash`   CHAR(16)    NOT NULL DEFAULT '',
      `zh`         MEDIUMTEXT  NULL,
      `status`     VARCHAR(12) NOT NULL DEFAULT '',
      `score`      FLOAT           NULL,
      `missing`    VARCHAR(160) NOT NULL DEFAULT '',
      `model`      VARCHAR(96)  NOT NULL DEFAULT '',
      `updated_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`doc_id`, `seg_i`),
      KEY `k_translation_doc` (`doc_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS `doc_glossary` (
      `doc_id`     VARCHAR(96) NOT NULL,
      `en`         VARCHAR(80)  NOT NULL,
      `zh`         VARCHAR(64)  NOT NULL DEFAULT '',
      `locked`     TINYINT      NOT NULL DEFAULT 0,
      `updated_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`doc_id`, `en`)
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
        # ★ 2026-10-11：论文不显示原件的根因 —— 这几列**从来没建过**。
        #   raw_file / is_paper 没列 → doc_put 写不进去、_doc_of 读不出来 →
        #   前端 canShowOriginal 恒为 false，论文被当成抽取文本显示。
        #   症状是「原件明明在 data/store/files/ 里，页面却给文本版」。
        #   tags / doc_text 同理：标签和留档原文一起静默丢失。
        ('documents', 'tags', 'JSON NULL'),
        ('documents', 'raw_file', "VARCHAR(255) NOT NULL DEFAULT ''"),
        ('documents', 'is_paper', 'TINYINT NOT NULL DEFAULT 0'),
        ('documents', 'doc_text', 'MEDIUMTEXT NULL'),
        # 2026-10-03 数据隔离：progress / notes 加user_id。
        # 光加列不够 —— 主键也得从 (card_id) 变成 (user_id, card_id)，
        # 否则 INSERT ... ON DUPLICATE KEY UPDATE 照样按 card_id 冲突，
        # 两个人的进度还是互相覆盖（列加了、主键没改 = 看着对、行为没变）。
        ('progress', 'user_id', "VARCHAR(64) NOT NULL DEFAULT ''"),
        ('notes', 'user_id', "VARCHAR(64) NOT NULL DEFAULT ''"),
    )

    #: **整张表**缺失的老库要补建的（不是加列，所以不能放进 _ADDED_COLUMNS）。
    #: 译文表是「多列 + 复合主键 + 索引」，用 ALTER 一列列补会漏掉主键 ——
    #: 没主键的表在 INSERT ... ON DUPLICATE KEY UPDATE 下退化成纯插入，
    #: 断点续译每跑一次就多一份重复译文，而表看起来「有数据、也正常」。
    _ADDED_TABLES = (
        ('doc_translations', """CREATE TABLE IF NOT EXISTS `doc_translations` (
             `doc_id` VARCHAR(96) NOT NULL, `seg_i` INT NOT NULL,
             `src_hash` CHAR(16) NOT NULL DEFAULT '', `zh` MEDIUMTEXT NULL,
             `status` VARCHAR(12) NOT NULL DEFAULT '', `score` FLOAT NULL,
             `missing` VARCHAR(160) NOT NULL DEFAULT '',
             `model` VARCHAR(96) NOT NULL DEFAULT '',
             `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
             PRIMARY KEY (`doc_id`, `seg_i`), KEY `k_translation_doc` (`doc_id`)
           ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""),
        ('doc_glossary', """CREATE TABLE IF NOT EXISTS `doc_glossary` (
             `doc_id` VARCHAR(96) NOT NULL, `en` VARCHAR(80) NOT NULL,
             `zh` VARCHAR(64) NOT NULL DEFAULT '', `locked` TINYINT NOT NULL DEFAULT 0,
             `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
             PRIMARY KEY (`doc_id`, `en`)
           ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""),
    )

    #: **列类型**要改的（不是加列，是 MODIFY）。
    #: 格式：表名 → (列名, 目标定义, 用于判断「还没改」的反向条件)
    #: `_ADDED_COLUMNS` 只解决 ADD COLUMN，而「VARCHAR(255) 改成 TEXT」
    #: 在 DDL 层面**不是加列能解决的** —— 必须 MODIFY，且判断依据也得换：
    #: 不能问「这列在不在」（一直在），得问「类型对不对」。
    _RECOLUMN_TYPES = (
        # meta.v：知识库的文件夹树整个存在 kb_tree 这一行，255 不够放。
        # 判「已改」用 CHARACTER_MAXIMUM_LENGTH > 255 —— 比字符串比类型稳，
        # 换MySQL 版本改了类型名也不会误判。
        ('meta', 'v', 'TEXT NOT NULL', ('meta', 'v', 'CHARACTER_MAXIMUM_LENGTH', 255)),
    )

    #: 主键/索引要改的表。补列之后必须重建主键，否则隔离不生效。
    #: 格式：表名 → 新主键的列列表（按顺序）
    _REKEY_TABLES = (
        ('progress', ('user_id', 'card_id')),
        ('notes', ('user_id', 'id')),
    )

    def _migrate_schema(self, dbname):
        """幂等补表 + 补列 + 改主键，返回改了哪些（给启动横幅用）。"""
        done = []
        # 先补表：_ADDED_TABLES 里的是 CREATE TABLE IF NOT EXISTS，
        # 对已存在的表直接跳过，对缺的表建出来。放在补列之前 ——
        # 顺序反了的话补列阶段会去 ALTER 一张不存在的表，直接报错刷屏。
        for _name, ddl in self._ADDED_TABLES:
            row = self._one("""SELECT COUNT(*) AS n FROM information_schema.TABLES
                               WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s""",
                            (dbname, _name))
            if row and row['n']:
                continue
            try:
                self._q(ddl)
                done.append(_name)
            except Exception as e:
                sys.stderr.write('[store] 建表 %s 失败：%s\n' % (_name, str(e)[:120]))
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
        done += self._recolumn(dbname)
        done += self._rekey(dbname)
        return done

    def _recolumn(self, dbname):
        """改列类型（幂等）。判「改过没」用 information_schema 里的实际类型/长度，
        不能问「列在不在」—— 那些列一直都在，要判断的是类型变没变。

        ★ 注意判断方向：是「**不等于**旧值才要改」。
          写成「等于就跳过」的话，每次启动都在做无意义的 ALTER 尝试 ——
          表现出来是 added 永远空、列永远是旧类型，非常难看出是判断反了。
          TEXT 的 CHARACTER_MAXIMUM_LENGTH 是 65535，不等于 255，正好能判出来。"""
        done = []
        for table, col, definition, (t2, c2, field, old_val) in self._RECOLUMN_TYPES:
            row = self._one("""SELECT `%s` AS v FROM information_schema.COLUMNS
                               WHERE TABLE_SCHEMA=%%s AND TABLE_NAME=%%s
                                 AND COLUMN_NAME=%%s""" % field,
                            (dbname, table, col))
            if not row:
                continue
            cur = row['v']
            if cur is not None and str(cur).lower() != str(old_val).lower():
                continue                     # 已经是目标类型（或更宽），幂等跳过
            try:
                self._q('ALTER TABLE `%s` MODIFY COLUMN `%s` %s' % (table, col, definition))
                done.append('%s.%s' % (table, col))
            except Exception as e:
                sys.stderr.write('[store] 改列 %s.%s 失败：%s\n'
                                 % (table, col, str(e)[:120]))
        return done

    def _rekey(self, dbname):
        """把 progress / notes 的主键改成 (user_id, …)。

        ★ 为什么必须显式改主键，不能只靠加列：
        `INSERT ... ON DUPLICATE KEY UPDATE` 判重只看**主键/唯一索引**。
        主键还是 (card_id) 的话，两个用户复习同一张卡写的还是同一行 ——
        加了 user_id 列、查询也带了 user_id 过滤，但**写**的那一步仍在
        静默覆盖。「加了列就以为隔离了」是这类改动最隐蔽的失败方式：
        读路径看着全对，写路径悄悄吃掉数据。
        """
        done = []
        for table, cols in self._REKEY_TABLES:
            want = ','.join('`%s`' % c for c in cols)
            try:
                cur = self._q("""SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE
                                 WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
                                   AND CONSTRAINT_NAME='PRIMARY'
                                 ORDER BY ORDINAL_POSITION""", (dbname, table), fetch=True)
                have = tuple(r['COLUMN_NAME'] for r in cur)
                if have == cols:
                    continue
                if not have:
                    continue                      # 表还没建（不可能，但别猜）
                # 先删主键名索引，再按新列建 —— MySQL 不支持 ADD PRIMARY KEY
                # 直接改列，必须 DROP + ADD。
                self._q('ALTER TABLE `%s` DROP PRIMARY KEY' % table)
                self._q('ALTER TABLE `%s` ADD PRIMARY KEY (%s)' % (table, want))
                done.append('%s 主键→(%s)' % (table, ','.join(cols)))
                sys.stderr.write('[store] %s 主键已从 (%s) 迁移为 (%s)\n'
                                 % (table, ','.join(have), ','.join(cols)))
            except Exception as e:
                sys.stderr.write('[store] %s 改主键失败：%s\n' % (table, str(e)[:160]))
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

    def progress_all(self, user_id=None):
        rows = self._q('SELECT * FROM progress WHERE user_id=%s',
                       (_uid(user_id),), fetch=True)
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

    def notes_all(self, user_id=None):
        rows = self._q('SELECT * FROM notes WHERE user_id=%s '
                       'ORDER BY updated_at DESC, id', (_uid(user_id),), fetch=True)
        return [_note_of(r) for r in rows]

    def docs_all(self):
        rows = self._q('SELECT * FROM documents', fetch=True)
        return [_doc_of(r) for r in rows]

    def drafts_all(self):
        return [json_loads(r['payload'], {})
                for r in self._q('SELECT payload FROM drafts ORDER BY created_at, id',
                                 fetch=True)]

    # ---------------- 到期队列：这条 SQL 是上数据库的主要理由 ----------------
    def due_cards(self, category=None, subject=None, domain=None, include_all=False,
                  user_id=None):
        """一次 JOIN 出「卡 + 进度 + 逾期天数」，且已按复习优先级排好。

        ★ JOIN 条件里**必须有 `p.user_id=%s`**：progress 主键已经是
        (user_id, card_id)，不加这个条件就是**笛卡尔积** —— 每张卡会匹配到
        所有人的每一行进度，队列长度直接翻几倍，而且 level/nextAt 全是别人的。
        这类错误不会报错，只会让复习页莫名其妙全是「已掌握」。

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
        # 拼进 WHERE 的每一片都是这里的字面量，值一律走 %s 占位符由驱动转义 ——
        # 所以 `' AND '.join(w)` 这个拼接是安全的。**加条件时只加字面量字符串，
        # 不要把参数值 f-string 进来**（列名也不可能来自外部：只有上面四个 if）。
        #
        # ★★ SQL 字符串里**绝对不能写注释**（-- 或 #）。
        #   本文件的中文注释里带着 `「」` 和单引号，进到 SQL 串里会让 MySQL 语法报错
        #   （实测1064，报错点出现在注释的中间位置，很難联想到是注释），
        #   而 due_list 有 Python 降级路径 → 表现为「队列能出来但悄悄变慢了」，
        #   只有翻降级横幅才发现 SQL 早就废了。解释一律写在 Python 注释里。
        #
        # ORDER BY 里的 overdue 用**与 SELECT 完全相同的 CASE**：
        #   裸的 `DATEDIFF(CURDATE(), p.next_at)` 遇 next_at IS NULL 返回 NULL，
        #   整列排序键变 NULL、行为未定义（实际退化成只剩 c.id 兜底=
        #   「先按 level 分档、档内不排逾期」，与 Python 路径不一致）。
        #   口径必须和 SELECT 对齐，否则同两个字段讲的是两件事。
        #
        # 没标记过（LEFT JOIN 落空）算「待学」，永远在队列里。
        # ★ `next_at IS NULL` 必须单列一项：SQL 里 `NULL <= CURDATE()`
        #   求值为 NULL（不是 true），整个 WHERE 把这行**静默丢掉**。
        #   而 Python 路径的 safe_next_at(db.py) 把 next_at 为空判成「今天到期」——
        #   同一份数据换个后端，队列内容就变了（换后端的触发条件是
        #   「内置卡指纹过期」或显式降级，不是罕见操作）。
        #   判据要和 safe_next_at 逐字对齐，别只写 <=。
        uid = _uid(user_id)
        if not include_all:
            w.append('(p.card_id IS NULL OR p.next_at IS NULL OR p.next_at <= CURDATE())')
        # JOIN 上的 user_id 条件**必须**在这里（而不是只靠 WHERE 过滤）：
        # 只在 WHERE 里加 `p.user_id=%s`，那些「没标记过」的卡 p.user_id 是 NULL，
        # 会被这个条件一起滤掉 → 未标记的卡全部从队列消失（LEFT JOIN 被降级成
        # INNER JOIN 的典型症状，不报错、只是队列变短）。
        #
        # 拼装用 str.replace 而不是 `%` 格式化：`%s` 格式化会把整个模板里的占位符
        # 按顺序吃掉，而 w 的片段里本来就含 %s（那些是留给驱动的），
        # 两者混用必然错位 —— 而且错位时报错点在驱动层，很难联想到是模板拼装。
        sql = """
            SELECT c.payload, c.id AS cid,
                   p.card_id AS p_cid, p.level, p.interval_d, p.ef, p.reps,
                   p.next_at, p.updated_at,
                   CASE WHEN p.next_at IS NULL THEN NULL
                        ELSE DATEDIFF(CURDATE(), p.next_at) END AS overdue
            FROM cards c
            LEFT JOIN progress p ON p.card_id = c.id AND p.user_id = @UID@
            WHERE @WHERE@
            ORDER BY FIELD(COALESCE(p.level, 0), 1, 2, 0, 3),
                     (p.card_id IS NULL) DESC,
                     CASE WHEN p.next_at IS NULL THEN NULL
                          ELSE DATEDIFF(CURDATE(), p.next_at) END DESC,
                     c.id
        """.replace('@UID@', '%s').replace('@WHERE@', ' AND '.join(w))
        a = [uid] + a                             # JOIN 的 uid 排在所有 WHERE 值之前
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
    def progress_put(self, cid, rec, user_id=None):
        self._q("""
            INSERT INTO progress (user_id, card_id, level, interval_d, ef, reps,
                                  next_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              level=VALUES(level), interval_d=VALUES(interval_d), ef=VALUES(ef),
              reps=VALUES(reps), next_at=VALUES(next_at), updated_at=VALUES(updated_at)
        """, (_uid(user_id), cid, int(rec.get('level') or 0),
              int(rec.get('interval') or 0), float(rec.get('ef') or 2.5),
              int(rec.get('reps') or 0),
              rec.get('nextAt') or None, rec.get('updatedAt') or None))

    def progress_del(self, cid, user_id=None):
        self._q('DELETE FROM progress WHERE user_id=%s AND card_id=%s',
                (_uid(user_id), cid))

    def progress_clear(self, user_id=None):
        if user_id == '*':
            self._q('DELETE FROM progress')
            return
        self._q('DELETE FROM progress WHERE user_id=%s', (_uid(user_id),))

    # ---------------- 写：笔记 ----------------
    def note_put(self, note, user_id=None):
        n = dict(note)
        self._q("""
            INSERT INTO notes (id, user_id, card_id, category, subject, title, body,
                               tags, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              card_id=VALUES(card_id), category=VALUES(category),
              subject=VALUES(subject), title=VALUES(title), body=VALUES(body),
              tags=VALUES(tags), updated_at=VALUES(updated_at)
        """, (n.get('id'), _uid(user_id), n.get('cardId') or None,
              n.get('category') or '', n.get('subject') or '',
              (n.get('title') or '')[:255],
              n.get('body') or '', json_dumps(n.get('tags') or []),
              n.get('createdAt') or None, n.get('updatedAt') or None))

    def note_del(self, nid, user_id=None):
        self._q('DELETE FROM notes WHERE user_id=%s AND id=%s', (_uid(user_id), nid))

    # ---------------- 写/读：聊天消息 ----------------
    def chat_all(self, user_id=None, limit=200):
        """按时间倒序取最近 limit 条（用于刷新恢复）"""
        rows = self._q(
            'SELECT * FROM chat_messages WHERE user_id=%s '
            'ORDER BY updated_at DESC LIMIT %s',
            (_uid(user_id), limit), fetch=True)
        return [self._chat_of(r) for r in reversed(rows)]

    def chat_put(self, msg, user_id=None):
        """写一条消息（新建或更新）。msg 必须含 id, role, text, sources, steps, verify, status, mode, web_search"""
        m = dict(msg)
        m['user_id'] = _uid(user_id)
        # sources/steps/verify 可能是列表/None，存 JSON
        for k in ('sources', 'steps', 'verify'):
            v = m.get(k)
            m[k] = json_dumps(v) if v is not None else '[]'
        m.pop('created_at', None)
        m.pop('updated_at', None)
        self._q("""
            INSERT INTO chat_messages (id, user_id, role, text, sources, steps, verify,
                                       status, mode, web_search)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              role=VALUES(role), text=VALUES(text), sources=VALUES(sources),
              steps=VALUES(steps), verify=VALUES(verify),
              status=VALUES(status), mode=VALUES(mode), web_search=VALUES(web_search),
              updated_at=VALUES(updated_at)
        """, (m.get('id'), _uid(user_id), m.get('role'), m.get('text'),
              m['sources'], m['steps'], m['verify'],
              m.get('status', 'done'), m.get('mode', 'flow'),
              1 if m.get('web_search') else 0))

    def chat_del(self, msg_id, user_id=None):
        self._q('DELETE FROM chat_messages WHERE user_id=%s AND id=%s',
                (_uid(user_id), msg_id))

    def chat_clear(self, user_id=None):
        self._q('DELETE FROM chat_messages WHERE user_id=%s', (_uid(user_id),))

    def _chat_of(self, row):
        return {
            'id': row['id'],
            'role': row['role'],
            'text': row['text'],
            'sources': json_loads(row['sources'], []),
            'steps': json_loads(row['steps'], []),
            'verify': json_loads(row['verify'], []),
            'status': row['status'],
            'mode': row['mode'],
            'web_search': bool(row['web_search']),
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }

    # ---------------- 写：文档 ----------------
    def doc_put(self, doc):
        d = dict(doc)
        self._q("""
            INSERT INTO documents (id, title, source, category, subject, domain,
                                   chapters, tags, raw_file, is_paper, doc_text,
                                   stats, parse, ai_done, ai_total, ai_model,
                                   ai_provider, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              title=VALUES(title), source=VALUES(source), category=VALUES(category),
              subject=VALUES(subject), domain=VALUES(domain),
              chapters=VALUES(chapters), tags=VALUES(tags),
              raw_file=VALUES(raw_file), is_paper=VALUES(is_paper),
              doc_text=VALUES(doc_text),
              stats=VALUES(stats), parse=VALUES(parse), ai_done=VALUES(ai_done),
              ai_total=VALUES(ai_total), ai_model=VALUES(ai_model),
              ai_provider=VALUES(ai_provider), updated_at=VALUES(updated_at)
        """, (d.get('id'), (d.get('title') or '')[:255], (d.get('source') or '')[:255],
              d.get('category') or '', d.get('subject') or '', d.get('domain') or '',
              json_dumps(d.get('chapters') or []),
              json_dumps(d.get('tags') or []),
              (d.get('rawFile') or '')[:255],
              1 if d.get('isPaper') else 0,
              d.get('text') or None,
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

    # ---------------- 论文译文 / 术语表 ----------------
    def trans_all(self, did):
        """读一份文档的全部译文。返回 {seg_i: {...}}。"""
        rows = self._q('SELECT * FROM doc_translations WHERE doc_id=%s'
                       ' ORDER BY seg_i', (did,), fetch=True)
        out = {}
        for r in rows:
            out[int(r['seg_i'])] = {
                'zh': r.get('zh') or '',
                'srcHash': (r.get('src_hash') or ''),
                'status': (r.get('status') or ''),
                # score 可能是 NULL（没校验过）。**必须转 float 或 None** ——
                # 直接把 Decimal 塞进返回值，前端 JSON 序列化会报 TypeError，
                # 而报错点在响应编码阶段，看不出是哪一列的问题。
                'score': (float(r['score']) if r.get('score') is not None else None),
                'missing': [int(x) for x in (r.get('missing') or '').split(',') if x],
                'model': (r.get('model') or ''),
            }
        return out

    def trans_put(self, did, seg_i, zh, src_hash='', status='', score=None,
                  missing=None, model=''):
        self._q("""INSERT INTO doc_translations
                   (doc_id, seg_i, src_hash, zh, status, score, missing, model,
                    updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s, NOW())
                   ON DUPLICATE KEY UPDATE
                     src_hash=VALUES(src_hash), zh=VALUES(zh),
                     status=VALUES(status), score=VALUES(score),
                     missing=VALUES(missing), model=VALUES(model),
                     updated_at=NOW()""",
                (did, int(seg_i), src_hash, zh, status, score,
                 ','.join(str(x) for x in (missing or [])), model))

    def trans_clear(self, did):
        self._q('DELETE FROM doc_translations WHERE doc_id=%s', (did,))

    def glossary_all(self, did):
        rows = self._q('SELECT * FROM doc_glossary WHERE doc_id=%s ORDER BY en',
                       (did,), fetch=True)
        return [{'en': r['en'], 'zh': r.get('zh') or '',
                 'locked': bool(r.get('locked') or 0)} for r in rows]

    def glossary_put(self, did, en, zh, locked=False):
        self._q("""INSERT INTO doc_glossary (doc_id, en, zh, locked, updated_at)
                   VALUES (%s,%s,%s,%s, NOW())
                   ON DUPLICATE KEY UPDATE
                     zh=VALUES(zh), locked=VALUES(locked), updated_at=NOW()""",
                (did, en, zh, 1 if locked else 0))

    def glossary_del(self, did, en):
        self._q('DELETE FROM doc_glossary WHERE doc_id=%s AND en=%s', (did, en))

    # ---------------- 内置卡：灌种子 / 查过期 ----------------
    def get_meta(self, k, default=''):
        r = self._one('SELECT v FROM meta WHERE k=%s', (k,))
        return r['v'] if r else default

    def set_meta(self, k, v):
        # ⚠️ 这里原来有 `str(v)[:255]` —— meta.v 放宽到 TEXT 之后这个截断就成了
        # **静默的数据损坏**：知识库的文件夹树 JSON 一存就被砍到 255 字符，
        # 读回来是个非法 JSON，报错却指向「前端树乱了」而不是「后端存丢了」。
        # 写长文本前先想清楚上限在哪，别留一个看不见的 255。
        self._q("""INSERT INTO meta (k, v) VALUES (%s,%s)
                   ON DUPLICATE KEY UPDATE v=VALUES(v)""", (k, str(v)))

    def seed_builtin(self, cards, force=False):
        """把 data/*.js 里的内置卡灌进 cards 表。

        不是每次启动都灌：先比整批指纹，一致就跳过（20 张卡无所谓，
        2000 张卡每次都重写就是灾难）。`force=True` 强制重灌。

        删掉的行也要处理 —— 卡从 data/*.js 里删掉后，库里那份不该留着，
        否则接口会返回一张「源码里已经不存在」的卡。
        """
        digest = cards_digest(cards)
        # 跳过条件用 builtin_stale 而不是只比指纹：指纹是**灌之前算的**，
        # 行后来被删掉它照样对得上（出过一次：库里少 3 张、状态还报「未过期」）。
        if not force and not self.builtin_stale(cards):
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
        """指纹对不上，或**行集合对不上**（少行/多行都算）。

        只比指纹不够：指纹记录的是「上次灌了什么」，灌完之后行被删掉、
        被手工改过，指纹依然相等 —— 状态会一直报「未过期」，但接口在
        少给卡。id 集合是真相，多一次轻量查询换掉这个盲区。
        """
        if self.get_meta(KEY_FINGERPRINT) != cards_digest(cards):
            return True
        want = {c.get('id') for c in cards if c.get('id')}
        have = {r['id'] for r in
                self._q("SELECT id FROM cards WHERE origin='builtin'", fetch=True)}
        return want != have

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
         # ★ tags / raw_file / is_paper / text 曾经**读不出来** —— 表里没这几列，
         #   doc_put 写进去也白写。前端 canShowOriginal 判 rawFile，
         #   于是论文永远显示抽取文本而不是原件。都走 r.get 兜底老库。
         'tags': json_loads(r.get('tags'), []),
         'rawFile': r.get('raw_file') or '',
         'isPaper': bool(r.get('is_paper') or 0),
         'text': r.get('doc_text') or '',
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
