# -*- coding: utf-8 -*-
"""数据层包入口 —— `import db` 的门面。

★ 2026-11-15 拆包：core/db.py（2119 行，93 个函数）按域拆成这个包。
  全仓调用方 100% 是 `import db` + 模块属性访问（核实过，没有
  `from db import x`），所以这里显式 re-export 全部公开名后，
  **任何调用方一行都不用改**。check.js 的 pyFiles 清单同步改成了
  逐文件列出本包（编译检查不漏文件）。

依赖方向（单向，改之前想清楚）：

    base ← builtin ← cards ← catalog
                       ↑
        progress ← { graph, bkt, plan }
        （progress 里 set_level → bkt.mastery_of 是函数体内的惰性 import，
          因为 bkt 反过来要 progress 的 events_of —— 那是数据流闭环，
          模块层面保持单向）

    docs / notes / profiles / users / plan 落在各自的域文件，
    跨域调用一律 from .xxx import 具体函数。

「db.X 当 API 用」的模块别名（外部有真实引用，不能丢）：
    db.algostore   profile.py 直接 db.algostore.get()
    db.store_pkg   （历史上供 main.py 间接用）
    db.cache       拟合脚本清缓存用
    db.algo        算法注册表的转发入口
"""
from .base import (BACK_DIR, CORE_DIR, DATA_DIR, FILE_CATALOG, ROOT, STORE_DIR,
                   _next_daily_id, _read_json, _write_json, add_days, algo,
                   algostore, backend, cache, diff_days, ensure_store,
                   read_text, safe_next_at, schedule, storage_info, store_pkg,
                   today_str)
from .base import _next_daily_id as next_daily_id  # noqa: F401  语义别名，不用下划线也能调
from .bkt import (bkt_params, fit_bkt, fit_fsrs, fsrs_params, mastery_all,
                  mastery_map, mastery_of, sort_by_mastery)
from .builtin import (_source_cards_ref, _src_files_key, builtin_cards,
                      builtin_stale, load_source_cards)
from .cards import (_OVERRIDE_PATH, _bump_cards_ver, all_cards,
                    apply_card_patch, load_custom, load_overrides,
                    revert_override, save_custom, save_overrides)
from .catalog import (FILE_DIRECTIONS, FILE_ROLES, _kw_hits, card_hit,
                      cat_name, direction_counts, direction_kws,
                      load_catalog, load_directions, load_roles, role_by_id,
                      subject_name)
from .docs import (delete_doc, glossary_all, glossary_del, glossary_put,
                   get_doc, load_docs, load_docs_brief, load_drafts,
                   rename_deck, save_drafts, set_doc_ai, trans_all,
                   trans_clear, trans_put, upsert_doc)
from .graph import (_GRAPH_CACHE, _G_SEMANTIC, build_graph, community_summary,
                    graph_insight, graph_path, graph_rank_of, graph_raw,
                    graph_recommend, neighbors)
from .notes import delete_note, load_notes, upsert_note
from .plan import build_outline, role_plan
from .profiles import (FILE_PROFILES, get_today_pick, load_profiles,
                       profile_of, save_profile, set_today_pick)
from .progress import (CORRECT_LEVEL, EVENTS_ALL, OVERDUE_NEVER, clear_progress,
                       due_list, events_count, events_of, get_progress,
                       log_review, mastery_report, reset_progress, review_queue,
                       set_level, stats)
from .users import (create_user, public_user, update_user_profile, user_all,
                    user_by_name, user_count, user_get, verify_login)

# `import security` 的转发：老 db.py 顶层 import 过 security（users 域用），
# 历史上个别脚本顺手用过 db.security —— 虽然没人登记，删掉的风险大于留着。
# （从 users 模块转交：`from . import security` 会去找 db.security 子模块，
#   那不存在，包初始化期直接 ImportError。）
from .users import security as security  # noqa: F401
