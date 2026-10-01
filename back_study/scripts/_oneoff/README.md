# _oneoff —— 一次性脚本留档

这里的脚本**都已经执行完毕，不再是日常工具链的一部分**。留着是为了：

1. 以后要批量改卡片数据结构时，可以照着改一个来用（比从零写快）；
2. 记录当年数据是怎么变成现在这个形状的。

**别在 scripts/ 主目录里找它们** —— 2026-09-26 从这个目录挪进来的。

## 目录里有什么

| 脚本 | 干过什么 | 现在还需要吗 |
|---|---|---|
| `normalize-data.js` | 把 `data/*.js` 的单引号 JS 字面量改成严格 JSON 字面量（Python `json.loads` 要能读） | 不需要。现在文件已是严格 JSON，新增科目照格式写即可 |
| `migrate-cats.js` | `domain` → `category` + `subject`，已跑完 10 张卡 | 不需要。但加 category 时可以参考 MAP 的写法 |
| `_add_related.js` | 给卡片批量写 `related` 关联（`{id, kind, note}`） | 不需要。是"写入格式"的范本：`kind` 只许 `prereq`/`extends`/`compare`，且必须带 `note` |

## 跑之前注意

这三个脚本的路径是 `path.join(__dirname, '..', '..', '..', 'data')` —— **三个 `..`**，
因为它们比主目录的脚本深一层。旧笔记里写的两层是挪动之前的写法，别照抄。

另外它们**直接覆写 `data/*.js` 源文件**（没有备份、没有 dry-run）。
再跑之前先手动复制一份 `data/`，或者先确认脚本逻辑还符合当前契约 ——
卡片契约现在的必填字段比当初多（`scene` 至少 2 条、`topicPath` 等），
老脚本生成的结果大概率过不了 `node back_study/scripts/check.js`。
