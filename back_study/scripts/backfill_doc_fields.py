# -*- coding: utf-8 -*-
"""回填 documents.raw_file —— 论文不显示原件的存量修复。

★ 事故回顾：`documents` 表从来没有 `raw_file` / `is_paper` / `doc_text` / `tags`
  这几列。`doc_put` 写进去的原件路径在入库那一刻就被**静默丢掉**了（SQL 里
  根本没有那一列），文件本体却好好地躺在 `data/store/files/<docId>/`。
  于是前端 `canShowOriginal` 恒为 false → 论文被当成抽取文本显示，
  而磁盘上原件明明在。这是最典型的「加了字段的读取却以为已经持久化」的坑。

所以这个脚本的判据只有一个：**磁盘上有原件文件，就把它写回 DB**。
不猜、不重导入（重导入会换新 id、丢章节进度）。

论文顺便补两样：is_paper=1，以及从原件重抽一份纯文本进 doc_text
（阅读仍走原件，这份文本只供全文检索 / RAG）。

幂等：可重复跑。· 必须在 back_study/ 下用 .venv 跑（要 pymysql）。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import db          # noqa: E402
import docparse    # noqa: E402


def backfill(raw_text=True):
    fixed = []
    for d in db.load_docs():
        did = d.get('id')
        if not did:
            continue
        patch = {}
        path = docparse.raw_path(did, os.path.splitext(d.get('rawFile') or '')[1])
        if not d.get('rawFile') and path:
            ext = os.path.splitext(path)[1]
            patch['rawFile'] = 'files/%s%s' % (did, ext)

        # 论文判定：用户当初选的类型优先；没得选就按文件是 PDF 且自称论文
        if not d.get('isPaper') and (d.get('category') == '论文'):
            patch['isPaper'] = True

        # 补 doc_text：以前从未入库，全库都搜不到正文。
        # 论文/资料一视同仁 —— 有原件就在本地重抽，不用重新导入。
        if raw_text and not d.get('text') and path:
            try:
                with open(path, 'rb') as f:
                    blob = f.read()
                patch['text'] = docparse.extract(blob, os.path.basename(path))['text'][:400000]
                st = dict(d.get('stats') or {})
                st['chars'] = len(patch['text'])
                patch['stats'] = st
            except Exception as e:                       # 抽不出就只记原件，不报错
                sys.stderr.write('[backfill] %s 抽文本失败：%s\n' % (did, str(e)[:100]))

        if not patch:
            continue
        db.upsert_doc(dict(d, **patch))
        fixed.append((did, sorted(patch)))
    return fixed


if __name__ == '__main__':
    rows = backfill(raw_text='--no-text' not in sys.argv)
    if not rows:
        print('没有需要回填的文档')
    for did, keys in rows:
        print('已回填 %s：%s' % (did, ', '.join(keys)))