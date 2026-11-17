#!/usr/bin/env bash
# ============================================================
# 在 D 盘下载 HuggingFace 模型（走 ModelScope 镜像，避开被墙的 HF 官方）
#
# 背景（2026-10-09 实测）：
#   huggingface.co 直连无响应 / 走本机代理返回 502（代理节点挂了）
#   hf-mirror.com 超时
#   modelscope.cn 可用，实测 **18.35 MB/s**，2.17GB 约 2 分钟
#
# 为什么不用 huggingface_hub.snapshot_download：
#   它只认 HF 的协议和域名，HF_ENDPOINT 只能指向 HF 系镜像
#   （hf-mirror.com），指到 modelscope 会 404。改 host 这条路走不通。
#   而 ModelScope 的 resolve URL 直接给302 → 阿里云 OSS CDN，
#   curl / aria2c 都能直接下，不需要装任何 SDK。
#
# 用法：
#   bash scripts/dl_hf_model.sh BAAI/bge-reranker-v2-m3 D:/models/bge-reranker-v2-m3
#   bash scripts/dl_hf_model.sh BAAI/bge-reranker-base D:/models/bge-reranker-base
#   PARTS=8 bash scripts/dl_hf_model.sh ...      # 8 线程（默认 4）
# ============================================================
set -uo pipefail

REPO="${1:-BAAI/bge-reranker-v2-m3}"
DEST="${2:-D:/models/$(basename "$REPO")}"
PARTS="${PARTS:-4}"
MS_BASE="https://modelscope.cn/models/${REPO}/resolve/master"

echo "模型   : $REPO"
echo "目标   : $DEST"
echo "线程数 : $PARTS"
echo

mkdir -p "$DEST"

# ---------- 1. 取文件清单 ----------
# ModelScope 的 repo/files 接口返回 JSON，含每个文件的 Size。
# 用它来决定分片边界，比写死文件列表可靠（换个模型也能用）。
echo "[1/4] 取文件清单..."
LIST_JSON="$(curl -s --max-time 60 "https://modelscope.cn/api/v1/models/${REPO}/repo/files?Revision=master")"
if [ -z "$LIST_JSON" ]; then
  echo "  ✗ 清单为空，先检查网络：curl -I https://modelscope.cn"
  exit 1
fi
echo "$LIST_JSON" | python -c "
import sys, json
d = json.load(sys.stdin)
for f in (d.get('Data') or {}).get('Files', []):
    sz = f.get('Size', 0)
    # 目录条目Size 为 0 且Path 不含扩展名，跳过
    if sz > 0 or '.' in f.get('Path',''):
        print('%s\t%d' % (f['Path'], sz))
" | tr -d '\r' > /tmp/_hf_files.tsv

if [ ! -s /tmp/_hf_files.tsv ]; then
  echo "  ✗ 清单解析不出文件，看一眼原始返回："
  echo "$LIST_JSON" | head -c 400
  exit 1
fi
echo "  $(wc -l < /tmp/_hf_files.tsv) 个文件"
echo

# ---------- 2. 小文件直接下（配置/词表都是几十 KB） ----------
echo "[2/4] 下载小文件..."
while IFS=$'\t' read -r path size; do
  # < 5MB 的直接 curl，不用分片
  if [ "$size" -lt 5242880 ]; then
    mkdir -p "$DEST/$(dirname "$path")"
    curl -sL --max-time 300 -o "$DEST/$path" "${MS_BASE}/${path}"
    printf "  OK  %-44s %8.1f KB\n" "$path" "$(awk -v s="$size" 'BEGIN{printf "%.1f", s/1024}')"
  fi
done < /tmp/_hf_files.tsv
echo

# ---------- 3. 大文件分片并行 ----------
# 为什么分片：单线程遇到代理抖动容易中途断流，一断就得从头再来。
# 8 片各自独立重试，坏一片只重下那一片。
echo "[3/4] 下载大文件（${PARTS} 线程分片）..."
while IFS=$'\t' read -r path size; do
  if [ "$size" -lt 5242880 ]; then continue; fi

  mkdir -p "$DEST/$(dirname "$path")"
  echo "  -> $path  $(awk -v s="$size" 'BEGIN{printf "%.2f", s/1073741824}') GB"

  chunk=$(( size / PARTS ))
  pids=""
  for i in $(seq 0 $((PARTS-1))); do
    start=$(( i * chunk ))
    if [ "$i" -eq $((PARTS-1)) ]; then
      end=$(( size - 1 ))                # 最后一片吃掉余量
    else
      end=$(( start + chunk - 1 ))
    fi
    (
      part="$DEST/$path.part$i"
      for try in 1 2 3; do
        # 每次重试都从头下这一片，片小，重来的代价可接受
        curl -sL --max-time 1800 -r "${start}-${end}" -o "$part" "${MS_BASE}/${path}" && break
        echo "    片$i 第${try}次失败，重试..." >&2
        sleep 3
      done
    ) &
    pids="$pids $!"
  done
  for p in $pids; do wait "$p"; done

  # 合并：: > 先清空，再按序追加（>> 是追加，第一次要清空）
  cat "$DEST/$path".part* > "$DEST/$path" && rm -f "$DEST/$path".part*
  got=$(wc -c < "$DEST/$path")
  if [ "$got" -eq "$size" ]; then
    printf "  OK  %-44s %.2f GB 字节数一致\n" "$path" "$(awk -v s="$got" 'BEGIN{printf "%.2f", s/1073741824}')"
  else
    printf "  ✗ %-44s 大小不符：期望 %d 实际 %d\n" "$path" "$size" "$got"
    exit 1
  fi
done < /tmp/_hf_files.tsv
echo

# ---------- 4. 校验 ----------
echo "[4/4] 校验..."
BAD=0
while IFS=$'\t' read -r path size; do
  got=$(wc -c < "$DEST/$path" 2>/dev/null || echo 0)
  if [ "$got" != "$size" ]; then
    echo "  ✗ $path  期望 $size 实际 $got"
    BAD=$((BAD+1))
  fi
done < /tmp/_hf_files.tsv

if [ "$BAD" -eq 0 ]; then
  echo "  全部文件字节数一致 ✓"
  echo
  echo "下载完成：$DEST"
  echo
  echo "怎么用："
  echo "  from sentence_transformers import CrossEncoder"
  echo "  m = CrossEncoder(r'$(echo "$DEST" | sed 's#\\#/#g')', device='cuda')"
else
  echo "  $BAD 个文件大小不符，重跑本脚本会跳过已完整的部分"
  exit 1
fi