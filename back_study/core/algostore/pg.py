# -*- coding: utf-8 -*-
"""算法库 · PostgreSQL 实现。

**✅ 本机已验证（2026-10-09）**：psycopg 3.3.6 + PG 16.15 真连通过，
`events_* / mastery_* / params_* / sessions_*` 全部实跑验证过（含建表幂等、
limit 边界、清空）。下面那句「未验证」是 2026-09-29 写的，已过时。

**为什么算法数据要放 PG 而不是继续用 MySQL**：

- `algo_params` 用 **JSONB** 存拟合参数 —— 参数结构会随模型变（BKT 四个标量、
  以后可能是 AKT 的一堆矩阵），JSONB 不用每次改表。
- 事件流是时序 append-only，PG 的分区表和窗口函数做「每人每知识点的学习曲线」
  比 MySQL 顺手。
- **后期 pgvector**：RAG 的向量直接放同一个库，省掉再维护一个向量库。
  这是 PG 真正的价值，不是一个"又一个数据库"。

四张表见 `DDL`。建表是幂等的（CREATE TABLE IF NOT EXISTS），缺表自动建，
所以第一次连上不用手动跑脚本。
"""

import threading

from .base import AlgoStore

DDL = (
    """CREATE TABLE IF NOT EXISTS review_events (
         id          BIGSERIAL PRIMARY KEY,
         user_id     VARCHAR(64)  NOT NULL,
         card_id     VARCHAR(96)  NOT NULL,
         kc          VARCHAR(96)  NOT NULL,
         level       SMALLINT     NOT NULL,
         correct     SMALLINT     NOT NULL,
         at          DATE         NOT NULL,
         elapsed_ms  INT,
         created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
       )""",
    """CREATE INDEX IF NOT EXISTS ix_events_user_kc
         ON review_events (user_id, kc, at)""",
    """CREATE TABLE IF NOT EXISTS mastery (
         user_id     VARCHAR(64)  NOT NULL,
         kc          VARCHAR(96)  NOT NULL,
         p           DOUBLE PRECISION NOT NULL,
         updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
         PRIMARY KEY (user_id, kc)
       )""",
    """CREATE TABLE IF NOT EXISTS algo_params (
         key         VARCHAR(64)  PRIMARY KEY,
         value       JSONB        NOT NULL,
         updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
       )""",
    # ★ 学习时长会话（个人中心埋点，2026-10-09 加）。
    #   之前只有 jsonfile 后端实现了 sessions_*，PG 这边缺 → 前端「学习时长」
    #   恒为 0 且看不出原因。补上之后 PG 配置也能正常统计。
    #   字段与 base.SESSION_KEYS 对齐：
    #     id / user_id / card_id / duration_seconds / level / ts / session_id
    #   `ts` 用 VARCHAR(24) 而不是 TIMESTAMPTZ —— 前端上报的是
    #   'YYYY-MM-DD' 或 'YYYY-MM-DDTHH:MM:SS' 两种形态，前者没有时分秒，
    #   强转 TIMESTAMPTZ 要么报错要么被猜成当天 00:00，反而制造歧义。
    #   而且报表只按**天**聚合（见 core/report.py 的 _day()），不需要时间精度。
    """CREATE TABLE IF NOT EXISTS review_sessions (
         id               BIGSERIAL PRIMARY KEY,
         user_id          VARCHAR(64)  NOT NULL,
         card_id          VARCHAR(96),
         duration_seconds INT          NOT NULL,
         level            SMALLINT,
         ts               VARCHAR(24)  NOT NULL,
         session_id       VARCHAR(96),
         created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
       )""",
    # 索引与 review_events 同思路：查询恒定带 user_id，再按时间取尾部窗口。
    """CREATE INDEX IF NOT EXISTS ix_sessions_user_ts
         ON review_sessions (user_id, ts, id)""",
)


class PgAlgoStore(AlgoStore):
    name = 'pg'

    def __init__(self, host='127.0.0.1', port=5432, user='postgres',
                 password='', dbname='study_algo', **_kw):
        self.cfg = dict(host=host, port=int(port), user=user,
                        password=password, dbname=dbname)
        #: 连不上时的原因，工厂要把它打进降级信息里
        self.last_error = ''
        self._local = threading.local()

    # ---------------- 连接 ----------------
    def _conn(self):
        """每线程一条连接。

        psycopg 的连接**不能跨线程复用**（和 pymysql 一个毛病）：FastAPI 把同步
        端点丢进线程池，一个连接被两个线程拿去用会直接报错。所以放 thread-local。
        """
        conn = getattr(self._local, 'conn', None)
        if conn is None:
            import psycopg                      # 延迟 import：没装也不影响默认路径
            conn = psycopg.connect(**self.cfg)
            conn.autocommit = True
            self._local.conn = conn
            self._ensure_schema(conn)
        return conn

    def _ensure_schema(self, conn):
        with conn.cursor() as cur:
            for sql in DDL:
                cur.execute(sql)

    def _q(self, sql, args=None, fetch=False):
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return cur.fetchall() if fetch else None

    # ---------------- 自检 ----------------
    def ping(self):
        try:
            self._q('SELECT 1', fetch=True)
            self.last_error = ''
            return True
        except Exception as e:
            self.last_error = '%s: %s' % (type(e).__name__, e)
            return False

    # ---------------- 事件流 ----------------
    def events_append(self, ev):
        row = self._q("""
            INSERT INTO review_events
              (user_id, card_id, kc, level, correct, at, elapsed_ms)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING id, user_id, card_id, kc, level, correct, at, elapsed_ms
        """, (str(ev.get('user_id')), ev.get('card_id'), ev.get('kc'),
              int(ev.get('level') or 0), int(1 if ev.get('correct') else 0),
              ev.get('at'), ev.get('elapsed_ms')), fetch=True)[0]
        return dict(zip(('id', 'user_id', 'card_id', 'kc', 'level',
                         'correct', 'at', 'elapsed_ms'), row))

    def events_of(self, user_id, kc=None, card_id=None, limit=500):
        sql = ('SELECT id, user_id, card_id, kc, level, correct, at, elapsed_ms'
               ' FROM review_events WHERE user_id=%s')
        args = [str(user_id)]
        if kc:
            sql += ' AND kc=%s'
            args.append(kc)
        if card_id:
            sql += ' AND card_id=%s'
            args.append(card_id)
        # ★ 契约是「最近 limit 条，再按正序返回」（见 base.events_of 的说明）。
        # 取尾部窗口只能先 DESC 再翻转 —— 直接 `ORDER BY at ASC LIMIT n`
        # 拿到的是**最旧**的 n 条，与 jsonfile 的 `out[-limit:]` 正好相反。
        # limit <= 0 / None = 不截断，走 LIMIT ALL；不能写 `limit or 500`，
        # 那会把「要全量」悄悄变成「要 500 条」，连绕开的办法都没有。
        if limit and limit > 0:
            sql += ' ORDER BY at DESC, id DESC LIMIT %s'
            args.append(int(limit))
        else:
            sql += ' ORDER BY at DESC, id DESC LIMIT ALL'
        rows = self._q(sql, args, fetch=True)
        rows = list(reversed(rows))          # 翻回时间正序
        keys = ('id', 'user_id', 'card_id', 'kc', 'level', 'correct',
                'at', 'elapsed_ms')
        out = []
        for r in rows:
            ev = dict(zip(keys, r))
            # at 是 DATE 列，psycopg 给的是 datetime.date；jsonfile 那边是字符串。
            # 不归一化就有个隐藏炸弹：哪天有接口直接序列化这张表，
            # json.dumps 不认 date，直接 500。
            if ev.get('at') is not None and not isinstance(ev['at'], str):
                ev['at'] = str(ev['at'])[:10]
            out.append(ev)
        return out

    def events_count(self, user_id=None):
        if user_id is None:
            return self._q('SELECT count(*) FROM review_events',
                           fetch=True)[0][0]
        return self._q('SELECT count(*) FROM review_events WHERE user_id=%s',
                       (str(user_id),), fetch=True)[0][0]

    def events_clear(self, user_id=None):
        if user_id is None:
            self._q('TRUNCATE review_events')
        else:
            self._q('DELETE FROM review_events WHERE user_id=%s', (str(user_id),))

    # ---------------- 学习时长会话 ----------------
    # ★ 之前这三个方法是空的（只有 jsonfile 实现了），PG 配置下
    #   「学习时长」恒显示 0h，且看不出是功能坏了还是用户没学。
    #   2026-10-09 补齐。实现要点与 events_of 一致（见那里的注释）。

    _SESSION_KEYS = ('id', 'user_id', 'card_id', 'duration_seconds',
                     'level', 'ts', 'session_id')

    def sessions_append(self, sess):
        row = self._q("""
            INSERT INTO review_sessions
              (user_id, card_id, duration_seconds, level, ts, session_id)
            VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING id, user_id, card_id, duration_seconds, level, ts, session_id
        """, (str(sess.get('user_id')), sess.get('card_id'),
              int(sess.get('duration_seconds') or 0),
              int(sess.get('level') or 0), sess.get('ts'),
              sess.get('session_id') or ''), fetch=True)[0]
        return dict(zip(self._SESSION_KEYS, row))

    def sessions_of(self, user_id, card_id=None, limit=500):
        sql = ('SELECT id, user_id, card_id, duration_seconds, level, ts, session_id'
               ' FROM review_sessions WHERE user_id=%s')
        args = [str(user_id)]
        if card_id:
            sql += ' AND card_id=%s'
            args.append(card_id)
        # ★ 与 events_of 完全同契约：「取**最近** limit 条再按正序返回」。
        # 直接 ORDER BY ts ASC LIMIT n 拿到的是**最旧**的 n 条 ——
        # 与 jsonfile 的 out[-limit:] 相反，会让「最近学了什么」变成「最早学的」。
        if limit and limit > 0:
            sql += ' ORDER BY ts DESC, id DESC LIMIT %s'
            args.append(int(limit))
        else:
            sql += ' ORDER BY ts DESC, id DESC LIMIT ALL'
        rows = self._q(sql, args, fetch=True)
        rows = list(reversed(rows))          # 翻回时间正序
        out = []
        for r in rows:
            sess = dict(zip(self._SESSION_KEYS, r))
            # ts 是 VARCHAR，本来就是字符串；但防御性归一化一下，
            # 万一将来有人把列改成 TIMESTAMPTZ，这里不会突然 500。
            if sess.get('ts') is not None and not isinstance(sess['ts'], str):
                sess['ts'] = str(sess['ts'])[:24]
            out.append(sess)
        return out

    def sessions_count(self, user_id=None):
        if user_id is None:
            return self._q('SELECT count(*) FROM review_sessions',
                           fetch=True)[0][0]
        return self._q('SELECT count(*) FROM review_sessions WHERE user_id=%s',
                       (str(user_id),), fetch=True)[0][0]

    def sessions_clear(self, user_id=None):
        """清空会话。不是契约必需（base 里没声明），但探针/调试用得上。"""
        if user_id is None:
            self._q('TRUNCATE review_sessions')
        else:
            self._q('DELETE FROM review_sessions WHERE user_id=%s', (str(user_id),))

    # ---------------- 掌握度 ----------------
    def mastery_get(self, user_id, kc):
        rows = self._q('SELECT p FROM mastery WHERE user_id=%s AND kc=%s',
                       (str(user_id), kc), fetch=True)
        return float(rows[0][0]) if rows else None

    def mastery_put(self, user_id, kc, p, extra=None):
        self._q("""
            INSERT INTO mastery (user_id, kc, p, updated_at)
            VALUES (%s,%s,%s, now())
            ON CONFLICT (user_id, kc)
            DO UPDATE SET p=EXCLUDED.p, updated_at=now()
        """, (str(user_id), kc, float(p)))

    def mastery_all(self, user_id):
        rows = self._q('SELECT kc, p FROM mastery WHERE user_id=%s',
                       (str(user_id),), fetch=True)
        return {r[0]: float(r[1]) for r in rows}

    def mastery_clear(self, user_id=None):
        if user_id is None:
            self._q('TRUNCATE mastery')
        else:
            self._q('DELETE FROM mastery WHERE user_id=%s', (str(user_id),))

    # ---------------- 参数 ----------------
    def params_get(self, key, default=None):
        import json
        rows = self._q('SELECT value FROM algo_params WHERE key=%s',
                       (key,), fetch=True)
        if not rows:
            return default
        v = rows[0][0]
        return json.loads(v) if isinstance(v, str) else v

    def params_put(self, key, value):
        import json
        self._q("""
            INSERT INTO algo_params (key, value, updated_at)
            VALUES (%s, %s::jsonb, now())
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()
        """, (key, json.dumps(value, ensure_ascii=False)))
