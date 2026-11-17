# -*- coding: utf-8 -*-
"""批量文档摄取：把 data/docs 下的 markdown / PDF 走
   parse_document →（逐章）enrich + to_card → save_drafts。

这是「深度」来源，和 scripts/gen_cards.py（按大纲铺广度）互补：
- gen_cards：依据 catalog 大纲批量生成，覆盖广、偏概念。
- gen_docs：把你自己的讲义 / 笔记 / 面经 / 教材章节吃进来，
  逐章用本地 Ollama 精读，产出带类比 / 原理拆解的草稿卡，
  进草稿池等人手补 scene 后入库。

复用现有能力，不加新抽取逻辑：
- importer.parse_document  分章
- llm.enrich + llm.to_card 逐章精读并转卡（和前端 /docs 同一套）
- importer.save_drafts     落盘到草稿池（尊重 json / mysql 后端）

运行：
  python scripts/gen_docs.py                    # 默认扫 data/docs
  python scripts/gen_docs.py --dir my_notes --domain "求职·Java" --subject java
  python scripts/gen_docs.py --dry-run          # 只统计，不落盘
  python scripts/gen_docs.py --no-llm          # 本地启发式，不调模型（草稿只含原理拆解，缺类比）

注：精读产出的草稿 scene 只有 1 条占位（项目硬规矩要 >=2 才能入库），
    属正常 —— 这些草稿进池子后，补上真实场景再 publish 即可。
"""
import argparse
import hashlib
import os
import sys

# ---- 路径：与 db.py / gen_cards.py 保持一致 ----
# 本文件 .../back_study/scripts
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACK = os.path.dirname(_HERE)            # .../back_study
_ROOT = os.path.dirname(_BACK)           # .../study（data 的上级）
DATA_DIR = os.path.join(_ROOT, 'data')
DOCS_DIR = os.path.join(DATA_DIR, 'docs')

# 让 `import importer` / `import llm` / `import db` 能命中 back_study 下的模块
# （importer / llm 实际在 core/ 下，和 gen_cards.py 一样把 core 也加进来）
_CORE = os.path.join(_BACK, 'core')
for _p in (_BACK, _CORE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 这两个 import 会顺带拉起 db（→ security → PyJWT）。
# 后端 .venv 已装齐 jwt + langchain，正常可用；装不上就尽早报错给提示，不要静默退化。
import importer
import llm


def _read_text(path):
    """读文件正文。md 直接读；pdf 走 importer 的抽取（缺 pypdf 返回 None）。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.md', '.markdown', '.txt'):
        return open(path, encoding='utf-8').read()
    if ext == '.pdf':
        try:
            data = open(path, 'rb').read()
            return importer.extract_pdf_bytes(data)
        except RuntimeError as e:
            if 'no_pypdf' in str(e):
                print('  ! 跳过 %s：未安装 pypdf（pip install pypdf）' % os.path.basename(path))
            else:
                print('  ! 跳过 %s：PDF 抽取失败（%s）' % (os.path.basename(path), e))
            return None
        except Exception as e:
            print('  ! 跳过 %s：%s' % (os.path.basename(path), e))
            return None
    print('  ! 跳过 %s：不支持的扩展名 %s' % (os.path.basename(path), ext))
    return None


def _list_files(directory):
    out = []
    for name in sorted(os.listdir(directory)):
        if name.startswith('.'):
            continue
        p = os.path.join(directory, name)
        if os.path.isfile(p):
            out.append(p)
    return out


def _slug(s):
    return ''.join(c for c in (s or '') if c.isalnum() or c in '-_')[:16] or 'x'


def _card_from_chapter(ch, ai, opts, filebase, idx):
    """复用 llm.to_card，但塞进稳定的唯一 id（避免同标题不同文档互相覆盖）。"""
    cid = 'doc-%s-%s-%d' % (_slug(filebase),
                            hashlib.md5(ch.get('title', '').encode('utf-8')).hexdigest()[:4], idx)
    o = dict(opts)
    o['id'] = cid
    return llm.to_card(ch, ai, o)


def ingest_file(path, opts, use_llm, model=None, chapter_limit=None):
    """摄取单个文件。返回 (草稿列表, 章节数, 跳过数)。"""
    name = os.path.basename(path)
    filebase = os.path.splitext(name)[0]
    text = _read_text(path)
    if not text or not text.strip():
        return [], 0, 0
    doc = importer.parse_document(text, {'title': opts.get('title'),
                                         'filename': name})
    chapters = doc.get('chapters') or []
    # 纯标题章节（body 太短）精读不出东西，和前端一样先跳过
    targets = [(i, c) for i, c in enumerate(chapters)
               if len((c.get('body') or '').strip()) >= 20]
    if chapter_limit:
        targets = targets[:chapter_limit]
    total_ch = len(targets)

    if not use_llm:
        # 无模型：整篇走本地启发式，产出偏浅的草稿（有 mechanism 但无类比 / scene 缺）
        cards = importer.parse_local(text, opts)
        for i, c in enumerate(cards):
            c['id'] = 'doc-%s-local-%d' % (_slug(filebase), i)
        return cards, len(chapters), 0

    if not targets:
        return [], len(chapters), 0

    # 逐章精读：1 章单调，多章批量（enrich_many 内部带对齐质检，对不上整批退回单章）
    try:
        if len(targets) == 1:
            i, ch = targets[0]
            ai = llm.enrich(ch.get('title'), ch.get('body'), model=model, self_check=True)
            res = [ai]
        else:
            items = [{'title': c.get('title'), 'body': c.get('body')} for _, c in targets]
            res, _ = llm.enrich_many(items, model=model, batch=4)
    except RuntimeError as e:
        print('  ! %s：精读调用失败（%s），该文件改用本地启发式' % (name, e))
        cards = importer.parse_local(text, opts)
        for i, c in enumerate(cards):
            c['id'] = 'doc-%s-local-%d' % (_slug(filebase), i)
        return cards, len(chapters), 0

    cards = []
    skipped = 0
    for (i, ch), ai in zip(targets, res):
        if not ai or not isinstance(ai, dict) or not (ai.get('oneLine') or ai.get('mechanism')):
            skipped += 1
            continue
        cards.append(_card_from_chapter(ch, ai, opts, filebase, i))
    return cards, total_ch, skipped


def main():
    ap = argparse.ArgumentParser(description='批量文档摄取 → 草稿卡（深度来源）')
    ap.add_argument('--dir', default=DOCS_DIR,
                    help='放 markdown / PDF 的目录（默认 data/docs）')
    ap.add_argument('--domain', help='领域名，如「求职·Java」（写入草稿的 domain）')
    ap.add_argument('--category', help='一级分类 id（写入草稿的 category）')
    ap.add_argument('--subject', help='二级科目 id（写入草稿的 subject）')
    ap.add_argument('--topic', help='统一追加到 topicPath 顶层之外的分组标签')
    ap.add_argument('--model', help='指定 Ollama 模型（默认 llm.pick_model）')
    ap.add_argument('--limit', type=int, help='最多处理前 N 个文件')
    ap.add_argument('--chapters', type=int, help='每个文件最多精读前 N 章')
    ap.add_argument('--no-llm', action='store_true', help='不调模型，用本地启发式')
    ap.add_argument('--dry-run', action='store_true', help='只统计，不落盘')
    args = ap.parse_args()

    if not os.path.isdir(args.dir):
        os.makedirs(args.dir, exist_ok=True)
        print('目录 %s 不存在，已创建。把 markdown / PDF 放进去再运行。' % args.dir)
        return

    # 模型可用性：可见地降级，而不是悄悄退化
    llm_ok = bool(llm.status().get('ok'))
    use_llm = llm_ok and not args.no_llm
    if args.no_llm:
        print('模式：本地启发式（--no-llm），不调模型')
    elif llm_ok:
        print('模式：本地 Ollama 逐章精读（%s）' % (args.model or llm.pick_model()))
    else:
        print('警告：Ollama/模型不可用，改用本地启发式。装好模型后重跑可得带类比的精读卡。')

    opts = {
        'domain': args.domain or '待归类',
        'category': args.category or '',
        'subject': args.subject or '',
        'topicPath': ['导入'] + ([args.topic] if args.topic else []),
    }
    print('写入草稿的归属：domain=%s category=%s subject=%s topicPath=%s'
          % (opts['domain'], opts['category'] or '∅', opts['subject'] or '∅', opts['topicPath']))

    files = _list_files(args.dir)
    if args.limit:
        files = files[:args.limit]
    if not files:
        print('没有可处理的文件（%s）。支持的扩展名：.md/.markdown/.txt/.pdf' % args.dir)
        return

    # 已存在的草稿 id 收集一次，避免重复摄取同一文档产生重复草稿
    existing = set()
    try:
        existing = set(d.get('id') for d in importer.list_drafts())
    except Exception:
        pass

    all_cards = []
    stats = {'files': 0, 'chapters': 0, 'cards': 0, 'skipped': 0, 'dup': 0}
    for path in files:
        print('→ %s' % os.path.basename(path))
        cards, ch, skip = ingest_file(path, opts, use_llm, args.model, args.chapters)
        stats['files'] += 1
        stats['chapters'] += ch
        stats['skipped'] += skip
        for c in cards:
            if c.get('id') in existing:
                stats['dup'] += 1
                continue
            existing.add(c.get('id'))
            all_cards.append(c)
            stats['cards'] += 1

    # 去重（同一运行内）
    seen = set()
    uniq = []
    for c in all_cards:
        if c.get('id') in seen:
            continue
        seen.add(c.get('id'))
        uniq.append(c)

    if args.dry_run:
        print('\n[dry-run] 将生成草稿 %d 张（来自 %d 文件 / %d 章节，跳过空章 %d，重复 %d），未落盘。'
              % (len(uniq), stats['files'], stats['chapters'], stats['skipped'], stats['dup']))
        for c in uniq[:10]:
            print('   · %s  %s' % (c['id'], c.get('title')))
        if len(uniq) > 10:
            print('   … 其余 %d 张' % (len(uniq) - 10))
        return

    if uniq:
        n = importer.save_drafts(uniq)
        print('\n完成：%d 文件 / %d 章节 → 新增草稿 %d 张（草稿池现有 %d 张）。'
              % (stats['files'], stats['chapters'], len(uniq), n))
    else:
        print('\n没有新增草稿（文件可能为空、或都已摄取过）。')
    print('下一步：前端「文档与精读」→ 草稿列表里补 scene（>=2 条）→ 发布成卡。')


if __name__ == '__main__':
    sys.exit(main())
