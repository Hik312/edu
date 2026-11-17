-- ---------------------------------------------------------------------------
-- 原理卡片学习平台 —— MySQL 表结构（MySQL 8.0+）
--
-- 这份文件是给人看的「可读版」；程序实际建表走 core/store/mysql.py 里的
-- DDL 常量（同一套语句，代码里那份保证 --init 一步到位）。
-- 想手工建库的话，直接照抄这个文件也能跑起来。
--
--      mysql -uroot -p < back_study/core/store/schema.sql
--      # 然后灌内容：python back_study/scripts/dbseed.py --sync
--
-- 设计取舍说明（别照着「教科书三范式」改，这里是有意的）：
--
--   * cards.payload 存 JSON 而不是把 mechanism / diagram / related 拆成
--     七八张子表。理由：这些字段永远是「整张卡一起读、一起写」，
--     从不单独查询某张卡的某一个 diagram 帧。拆表的收益是查询灵活，
--     代价是每次读卡都要 5 次 JOIN —— 对这个场景是净亏。
--     真正需要按列查的东西（category / subject / domain / title）
--     都提成了独立列并建了索引，该快的路径不会慢。
--
--   * documents.chapters 同理。一份八股文几十章，正文加起来几百 KB，
--     拆成 chapter 表以后「打开文档」要先 JOIN 再拼回来，白折腾。
--
--   * progress 反过来，**全部拆成标量列**并给 next_at 建索引。
--     因为「今日到期队列」是这个系统访问最频繁的查询，而且它天然是
--     一个 WHERE + ORDER BY，正对 SQL 的胃口。用 Python 全量拉回来再排序
--     属于把数据库当文件系统用 —— 那还不如不用数据库。
-- ---------------------------------------------------------------------------

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS `study_cards`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

USE `study_cards`;

-- ---------------------------------------------------------------------------
-- cards：内置卡（从 data/*.js 灌进来）+ 自定义卡（接口写的）
--   origin='builtin' 的行是**内容**，由 scripts/dbseed.py --sync 维护，
--   接口永远不写它；origin='custom' 的行是**数据**，接口随便改。
--   这条边界跟接入数据库之前一致，别混。
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `cards` (
  `id`         VARCHAR(96)  NOT NULL                COMMENT '卡片 id',
  `origin`     VARCHAR(16)  NOT NULL DEFAULT 'builtin' COMMENT 'builtin=源码内容 / custom=用户数据',
  `category`   VARCHAR(48)  NOT NULL DEFAULT ''     COMMENT '一级分类，如 ai/tech',
  `subject`    VARCHAR(48)  NOT NULL DEFAULT ''     COMMENT '科目，如 java/ai',
  `domain`     VARCHAR(48)  NOT NULL DEFAULT ''     COMMENT '领域，如 工作/考研',
  `topic_path` JSON             NULL                COMMENT '主题路径数组',
  `title`      VARCHAR(255) NOT NULL DEFAULT '',
  `one_line`   VARCHAR(512) NOT NULL DEFAULT ''     COMMENT '一句话概括，列表页只读这几个列',
  `src_file`   VARCHAR(96)  NOT NULL DEFAULT ''     COMMENT '内置卡来源文件名，同步时用来算增量',
  `payload`    JSON         NOT NULL                COMMENT '整张卡的完整 JSON',
  `fingerprint` CHAR(16)    NOT NULL DEFAULT ''     COMMENT '内容指纹，用于判断库里是否已过期',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_cards_origin` (`origin`),
  KEY `ix_cards_scope`  (`category`, `subject`),
  KEY `ix_cards_domain` (`domain`),
  KEY `ix_cards_fp`     (`fingerprint`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='卡片（内置内容 + 自定义数据）';

-- 中文全文检索：ngram 分词器是 MySQL 内置的，不用装插件。
-- 单独用 ALTER 建，因为有些精简版 MySQL 不带 ngram parser，
-- 建索引失败不该拖垮整次初始化（失败时接口仍然能用 LIKE 兜底）。
-- CREATE FULLTEXT INDEX `ft_cards` ON `cards` (`title`, `one_line`) WITH PARSER ngram;

-- ---------------------------------------------------------------------------
-- progress：复习进度（SM-2）。全标量列 + next_at 索引 = 到期队列一条 SQL
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `progress` (
  `user_id`    VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '归属用户；''=匿名桶（脚本/迁移用）',
  `card_id`    VARCHAR(96)  NOT NULL,
  `level`      TINYINT      NOT NULL DEFAULT 0  COMMENT '0未标记 1不会 2模糊 3会',
  `interval_d` INT          NOT NULL DEFAULT 0  COMMENT '当前间隔（天）',
  `ef`         DECIMAL(4,2) NOT NULL DEFAULT 2.50 COMMENT 'SM-2 难度因子',
  `reps`       INT          NOT NULL DEFAULT 0  COMMENT '连续答对次数',
  `next_at`    DATE             NULL            COMMENT '下次复习日',
  `updated_at` DATE             NULL,
  -- ★ 主键必须带 user_id：不带的话 ON DUPLICATE KEY UPDATE 判重只看 card_id，
  --   两个用户复习同一张卡写的还是同一行（2026-10-03 踩过：探针把真人进度全盖掉）。
  PRIMARY KEY (`user_id`, `card_id`),
  KEY `ix_progress_due`   (`user_id`, `next_at`),
  KEY `ix_progress_level` (`user_id`, `level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='复习进度（按用户隔离）';

-- ---------------------------------------------------------------------------
-- notes：笔记（独立笔记 + 挂在卡片下的「我的理解」，后者有 card_id）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `notes` (
  `id`         VARCHAR(96)  NOT NULL,
  `user_id`    VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '归属用户；''=匿名桶',
  `card_id`    VARCHAR(96)      NULL            COMMENT '非空 = 这张卡的「我的理解」',
  `category`   VARCHAR(48)  NOT NULL DEFAULT '',
  `subject`    VARCHAR(48)  NOT NULL DEFAULT '',
  `title`      VARCHAR(255) NOT NULL DEFAULT '',
  `body`       MEDIUMTEXT       NULL,
  `tags`       JSON             NULL,
  `created_at` DATE             NULL,
  `updated_at` DATE             NULL,
  -- 同 progress：主键必须带 user_id，否则两人笔记会互相覆盖
  PRIMARY KEY (`user_id`, `id`),
  KEY `ix_notes_card`    (`user_id`, `card_id`),
  KEY `ix_notes_scope`   (`user_id`, `category`, `subject`),
  KEY `ix_notes_updated` (`user_id`, `updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='笔记（按用户隔离）';

-- ---------------------------------------------------------------------------
-- documents：整份导入的资料（md/txt/pdf 切成章节）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `documents` (
  `id`          VARCHAR(96)  NOT NULL,
  `title`       VARCHAR(255) NOT NULL DEFAULT '',
  `source`      VARCHAR(255) NOT NULL DEFAULT '' COMMENT '原始文件名',
  `category`    VARCHAR(48)  NOT NULL DEFAULT '' COMMENT '导入时用户选的类型：资料/论文/笔记',
  `subject`     VARCHAR(48)  NOT NULL DEFAULT '',
  `domain`      VARCHAR(48)  NOT NULL DEFAULT '',
  `chapters`    JSON             NULL            COMMENT '章节数组（含正文与 AI 精读结果）',
  `tags`        JSON             NULL            COMMENT '标签数组（分类器产出，前端树与搜索用）',
  `raw_file`    VARCHAR(255) NOT NULL DEFAULT '' COMMENT '原始文件相对路径，如 files/doc-x.pdf；空=没留原件',
  `is_paper`    TINYINT      NOT NULL DEFAULT 0 COMMENT '1=论文：只显示原件，不分章',
  `doc_text`    MEDIUMTEXT        NULL            COMMENT '留档原文全文（RAG/全文检索用，与原件分离）',
  `stats`       JSON             NULL            COMMENT '分章统计 {chapters,chars,headings}，列表页显示用',
  `parse`       JSON             NULL            COMMENT '内容解析报告 {at,modelOk,msg,chapters[]}，出卡前的剔除确认',
  `ai_done`     INT          NOT NULL DEFAULT 0,
  `ai_total`    INT          NOT NULL DEFAULT 0,
  `ai_model`    VARCHAR(96)  NOT NULL DEFAULT '',
  `ai_provider` VARCHAR(32)  NOT NULL DEFAULT '',
  `created_at`  DATE             NULL,
  `updated_at`  DATE             NULL,
  PRIMARY KEY (`id`),
  KEY `ix_docs_scope` (`category`, `subject`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文档（章节化资料）';

-- ---------------------------------------------------------------------------
-- drafts：导入缓冲区。草稿不是卡，补齐字段才入库
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `drafts` (
  `id`         VARCHAR(96)  NOT NULL,
  `title`      VARCHAR(255) NOT NULL DEFAULT '',
  `payload`    JSON         NOT NULL,
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='待入库草稿';

-- ---------------------------------------------------------------------------
-- meta：键值杂项。目前只放内置卡的内容指纹，用来判断库里是不是落后于
-- data/*.js（落后了 /api/storage 会报 stale，不会偷偷用旧内容）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `meta` (
  `k` VARCHAR(48)  NOT NULL,
  -- 2026-10-11 由 VARCHAR(255) 放宽到 TEXT：知识库的文件夹树整个存在
  -- meta.kb_tree 这一行，255 字符连三层节点名都放不下。
  `v` TEXT            NOT NULL,
  PRIMARY KEY (`k`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='键值杂项';

-- ---------------------------------------------------------------------------
-- chat_messages：AI 问答会话记录（按用户隔离）。
--   L1 会话内多轮：存前端发来的历史记录，便于刷新恢复、多端同步。
--   设计取舍：
--     * role/text/sources 存 JSON/文本，不拆字段（整条消息整体读写，不单独查询某字段）。
--     * status 标记生成态：done=已完成 / generating=生成中 / error=出错 → 支持「刷新后显示半截」与「续流」。
--     * 仅保留最近 200 条/用户，防止无限膨胀（写入时裁剪）。
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `chat_messages` (
  `id`          VARCHAR(96)  NOT NULL                     COMMENT '消息 id（msg_时间戳_随机）',
  `user_id`     VARCHAR(64)  NOT NULL DEFAULT ''          COMMENT '归属用户；''=匿名桶',
  `role`        VARCHAR(16)  NOT NULL                     COMMENT 'user / assistant',
  `text`        MEDIUMTEXT      NULL                      COMMENT '消息正文（已渲染为 HTML 的 markdown）',
  `sources`     JSON            NULL                      COMMENT '引用卡片 id 数组',
  `steps`       JSON            NULL                      COMMENT 'Agent 步骤条 [{text, done}]',
  `verify`      JSON            NULL                      COMMENT '校验建议 [{card_id, title, summary, issues[], proposed_patch}]',
  `status`      VARCHAR(16)  NOT NULL DEFAULT 'done'      COMMENT 'done/generating/error',
  `mode`        VARCHAR(16)  NOT NULL DEFAULT 'flow'      COMMENT 'flow/react',
  `web_search`  TINYINT(1)     NOT NULL DEFAULT 0         COMMENT '是否开启联网',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`, `id`),
  KEY `ix_chat_updated` (`user_id`, `updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 问答会话（按用户隔离）';

-- ---------------------------------------------------------------------------
-- users：账号。三端统一到这一张表 —— web 用「用户名 + 密码」，小程序走 openid，
-- 同一个人的两个入口可以绑到同一行上。
--
-- 用户名唯一索引天然大小写不敏感（建库用 utf8mb4_general_ci），
-- 与 JSON 后端的 lower() 语义一致 —— 两版存储在这点上要是不同，
-- 会出现「MySQL 能注册两个同名用户、切回 JSON 只剩一个」这种极难查的问题。
--
-- 注意：progress / notes / documents 目前**还没有 user_id**。
-- 加登录只做到「有账号、能登录」，数据隔离是下一步（要配一次数据迁移，
-- 不能顺手加列了事，否则现有进度会变成「找不到」）。
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id`            INT          NOT NULL AUTO_INCREMENT,
  `username`      VARCHAR(32)  NOT NULL DEFAULT '',
  `password_hash` VARCHAR(160) NOT NULL DEFAULT ''  COMMENT 'pbkdf2_sha256$轮数$盐$摘要',
  `display_name`  VARCHAR(64)  NOT NULL DEFAULT '',
  `role`          VARCHAR(16)  NOT NULL DEFAULT 'user',
  `openid`        VARCHAR(64)      NULL            COMMENT '微信小程序登录用',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_users_name` (`username`),
  UNIQUE KEY `uq_users_openid` (`openid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户账号';

-- ---------------------------------------------------------------------------
-- 论文译文（2026-10-11）
-- ★ 为什么单独建表而不是塞进 documents 或 meta：
--   documents 是文档本体，一篇论文的译文能到几百 KB，塞进去会让每次
--     读文档列表都拖着走；meta.v 虽然是 TEXT（64KB），但它存的是
--     「单例状态」（kb_tree 这类），译文是**每份文档各自的**。
--   一段一行的结构还有个更实际的好处：**断点续译**。
--     261 段翻到第 200 段断了，前 200 段已经落库，重跑只补后面的；
--     存在一个大 JSON 字段里就做不到「写一行算一行」。
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `doc_translations` (
  `doc_id`     VARCHAR(96) NOT NULL,
  `seg_i`      INT         NOT NULL COMMENT '段序号，与 translate.segment() 的输出一致',
  `src_hash`   CHAR(16)    NOT NULL DEFAULT '' COMMENT '原文指纹：原文变了这条译文就该作废',
  `zh`         MEDIUMTEXT  NULL,
  `status`     VARCHAR(12) NOT NULL DEFAULT '' COMMENT 'ok / warn / bad（回译校验结果）',
  `score`      FLOAT           NULL COMMENT '回译对齐分，NULL=未校验',
  `missing`    VARCHAR(160) NOT NULL DEFAULT '' COMMENT '缺失的占位符序号，逗号分隔',
  `model`      VARCHAR(96)  NOT NULL DEFAULT '',
  `updated_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`doc_id`, `seg_i`),
  KEY `k_translation_doc` (`doc_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='论文逐段译文（可断点续译）';

CREATE TABLE IF NOT EXISTS `doc_glossary` (
  `doc_id`     VARCHAR(96) NOT NULL,
  `en`         VARCHAR(80)  NOT NULL,
  `zh`         VARCHAR(64)  NOT NULL DEFAULT '',
  `locked`     TINYINT      NOT NULL DEFAULT 0 COMMENT '1=用户手动锁定的，重抽术语表时不覆盖',
  `updated_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`doc_id`, `en`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文档术语表（用户可编辑，锁定的不会被覆盖）';
