# -*- coding: utf-8 -*-
"""等 gen 跑完后串行执行剩余流水线（后台跑，日志 pipeline_rest.log）。

    python pipeline_rest.py

步骤（任一失败立即停，已完成的不重跑 —— 各步自身支持断点续跑）：
  0) 等 run_all_phase3.log 出现 [cs] 完成（60 分钟超时）
  1) add_diagrams.py all              新 89 张补图（含 arch 模板）
  2) add_diagrams.py all --retry-null 旧 null 卡用四模板提示词二轮
  3) link_related.py                  全库 related（词法召回 + LLM 精选）
  4) emit_js.py all                   jsonl → data/gen_interview_*.js
  5) verify_interview_cards.py        出库校验（含 diagram / related 契约）
  6) dbseed.py --sync                 入库
  7) node scripts/check.js            全链路，EXIT=0 收尾
"""
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))          # scripts/_interview
BK = os.path.dirname(os.path.dirname(HERE))                # back_study
ROOT = os.path.dirname(BK)                                  # study
PY = os.path.join(BK, '.venv', 'Scripts', 'python.exe')
GEN_LOG = os.path.join(HERE, 'run_all_phase3.log')
OUT_LOG = os.path.join(HERE, 'pipeline_rest.log')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)


def log(msg):
    line = '%s %s' % (time.strftime('%H:%M:%S'), msg)
    with open(OUT_LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
    print(line, flush=True)


def wait_gen(timeout_min=60):
    t0 = time.time()
    while time.time() - t0 < timeout_min * 60:
        try:
            with open(GEN_LOG, encoding='utf-8', errors='replace') as f:
                txt = f.read()
        except OSError:
            txt = ''
        # 每组结束打「[组名] 完成：…」；cs 是最后一组
        if '[cs] 完成' in txt:
            return True
        time.sleep(15)
    return False


def run(name, args, cwd):
    log('==== %s: %s' % (name, ' '.join(os.path.basename(a) for a in args)))
    t0 = time.time()
    p = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, bufsize=1,
                         universal_newlines=True, encoding='utf-8',
                         errors='replace')
    for line in p.stdout:
        with open(OUT_LOG, 'a', encoding='utf-8') as f:
            f.write('  | ' + line)
    p.wait()
    if p.returncode != 0:
        log('!!!! %s 失败 rc=%s（停在这一步）' % (name, p.returncode))
        return False
    log('==== %s 完成 %.0fs' % (name, time.time() - t0))
    return True


def main():
    open(OUT_LOG, 'a', encoding='utf-8').write('\n---- pipeline start %s ----\n'
                                               % time.strftime('%Y-%m-%d %H:%M:%S'))
    log('等 gen 完成（每 15s 查一次）…')
    if not wait_gen():
        log('!!!! 等 gen 超时（60 分钟），放弃')
        return 1
    log('gen 已完成')

    steps = [
        ('diagrams 新卡', [PY, os.path.join(HERE, 'add_diagrams.py'), 'all'], HERE),
        ('diagrams retry-null', [PY, os.path.join(HERE, 'add_diagrams.py'), 'all',
                                 '--retry-null'], HERE),
        ('related', [PY, os.path.join(HERE, 'link_related.py')], HERE),
        ('emit', [PY, os.path.join(HERE, 'emit_js.py'), 'all'], HERE),
        ('verify', [PY, os.path.join(HERE, 'verify_interview_cards.py')], HERE),
        ('dbseed', [PY, os.path.join(BK, 'scripts', 'dbseed.py'), '--sync'], BK),
        ('check', ['node', os.path.join(BK, 'scripts', 'check.js')], ROOT),
    ]
    for name, args, cwd in steps:
        if not run(name, args, cwd):
            return 1
    log('ALL DONE')
    return 0


if __name__ == '__main__':
    sys.exit(main())
