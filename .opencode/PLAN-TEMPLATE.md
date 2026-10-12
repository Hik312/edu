# 知识库页面实施计划

## 目标

新增独立「知识库」页面（`/knowledge`），与现有「文档与精读」并列：

- **知识库**：资料管理 + 原文阅读 + 自动分类（本次重点）
- **文档与精读**：保留，专注转卡工具定位

## 三个核心能力

| 能力 | 方案 | 理由 |
|------|------|------|
| 源文档保存 | 上传时原始字节存 `data/store/files/<docId>.<ext>` | 现在只存解析结果，原始文件丢了 |
| PDF 在线预览 | `<iframe src="fileUrl">` 浏览器原生阅读器 | 零前端依赖，Chrome/Edge/Firefox 内置完整查看器（翻页/缩放/搜索），最快 |
| 自动分类 | 规则优先 + LLM 兜底 | 规则快但粗，LLM 准但慢/依赖模型，结合最稳 |

## 数据模型变更

文档记录（`documents.json`）新增字段：

```json
{
  "id": "doc-20260922-1",
  "title": "MySQL 索引原理",
  "category": "面试资料",
  "domain": "后端·数据库",
  "tags": ["MySQL", "索引", "B+树"],
  "rawFile": "files/doc-20260922-1.pdf",
  "...": "现有字段不变"
}
```

## 实施步骤

### Step 1: 后端 — 原始文件存储

**`back_study/core/docparse.py`** 新增：
- `save_raw(doc_id, data, ext)` → 存 `data/store/files/<doc_id>.<ext>`
- `raw_path(doc_id)` → 返回路径或 None
- `delete_raw(doc_id)` → 清理文件

**`back_study/app/routers/web/docs.py`** 改动：
- `import_doc`：解析前先存原始文件（`save_raw`），拿到 docId 后写入 `rawFile` 字段
- `delete_doc`：同时删原始文件（`delete_raw`）
- 新增 `GET /api/knowledge/file/{did}`：流式返回原始文件，鉴权走 `?t=` token（iframe 不带 Authorization 头，与 `/api/media/` 同模式）

### Step 2: 后端 — 自动分类

**新建 `back_study/core/classifier.py`**：

```
classify_doc(title, text, filename) → {category, domain, tags}
```

- **规则层**（总是运行）：
  - 扩展名 → category 初判（.pdf → "资料", .md/.txt → "笔记", .docx → "资料"）
  - 文件名关键词 → domain 初判（"MySQL" → "后端·数据库", "Java" → "后端·Java" 等）
- **LLM 层**（`llm.status().ok` 时运行）：
  - 送标题 + 前 2000 字，让模型输出 `{"category":"","domain":"","tags":[]}`
  - 解析后覆盖规则结果（模型给了的就用模型的）
- **兜底**：LLM 不可用或返回不合法 → 用规则结果；规则也没命中 → `category='未分类'`

**`import_doc` 里调用**：解析完文档后调 `classify_doc`，结果写入 doc 的 `category/domain/tags`。

### Step 3: 前端 — API 层

**新建 `web/src/api/knowledge.js`**：
- `listKnowledge()` → `GET /api/docs`（复用现有列表接口）
- `getFileUrl(docId)` → 拼 `/api/knowledge/file/{docId}?t=token`
- `importKnowledge(body)` → `POST /api/import/doc`（复用现有导入）
- `updateDocClass(docId, cls)` → `PUT /api/docs/{docId}`（预留，手动调整分类）

### Step 4: 前端 — 知识库页面

**新建 `web/src/views/knowledge/KnowledgeView.vue`**，三栏布局：

```
┌─────────────┬──────────────────────┬────────────┐
│ 分类树        │  原文阅读区            │ AI 注解     │
│             │                      │ (可收起)    │
│ ▸ 全部资料    │  PDF → iframe        │            │
│ ▸ 论文       │  md/txt → marked渲染  │  精读结果    │
│ ▸ 笔记       │  无原始文件 → chapters │  遗忘提醒    │
│ ▸ 面试资料    │                      │            │
│             │  章节导航（左侧锚点）    │            │
└─────────────┴──────────────────────┴────────────┘
```

- 分类树：按 `category → domain` 两级分组，点击筛选
- 阅读区：
  - PDF → `<iframe :src="getFileUrl(docId)">` 浏览器原生渲染
  - md/txt → 正文直接渲染（marked）
  - 无原始文件 → 回落到现有 chapters 阅读
- 顶部：导入按钮（复用现有导入逻辑）、搜索框
- AI 注解侧栏：精读结果 + 遗忘提醒（P2 完善，先留占位）

### Step 5: 路由 + 侧栏

- `web/src/router/index.js`：加 `/knowledge` 路由
- `web/src/layouts/AppLayout.vue`：ICON 加 `knowledge`，NAV 的"内容"组加 `{ name: 'knowledge', label: '知识库' }`

### Step 6: 验证

- 上传 PDF → 原始文件保存 → iframe 能打开
- 上传 md → 正文渲染
- 无 LLM → 规则分类兜底
- 有 LLM → LLM 分类覆盖
- DocsView 转卡链路不受影响

## 本期不做（后续迭代）

- 知识库文档级 RAG 索引（P3）
- 精读注解侧栏完整实现（P2，先留占位）
- docx 在线预览（只提供下载 + 文字预览）
- 手动调整分类的 UI（预留 API，不做页面）
