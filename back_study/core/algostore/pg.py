# -*- coding: utf-8 -*-
"""算法库 · PostgreSQL 实现。

**⚠ 本机尚未验证（2026-09-29）**：venv 里没装 psycopg，且 PG 要密码才能连
（免密试连失败）。代码按 psycopg 3 的 API 写，等拿到密码 + 装了驱动之后
必须真跑一遍 `ALGO_STORE=pg` 再算数。默认配置是 json，不会走到这里。

**为什么算法数据要放 PG 而不是继续用 MySQL**：

- `algo_params` 用 **JSONB** 存拟合参数 —— 参数结构会随模型变（BKT 四个标量、
  以后可能是 AKT 的一堆矩阵），JSONB 不用每次改表。
- 事件流是时序 append-only，PG 的分区表和窗口函数做「每人每知识点的学习曲线」
  比 MySQL 顺手。
- **后期 pgvector**：RAG 的向量直接放同一个库，省掉再维护一个向量库。
  这是 PG 真正的价值，不是一个"又一个数据库"。

三张表见 `DDL`。建表是幂等的（CREATE TABLE IF NOT EXISTS），缺表自动建，
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
        sql += ' ORDER BY at ASC, id ASC LIMIT %s'
        args.append(int(limit or 500))
        rows = self._q(sql, args, fetch=True)
        keys = ('id', 'user_id', 'card_id', 'kc', 'level', 'correct',
                'at', 'elapsed_ms')
        return [dict(zip(keys, r)) for r in rows]

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
