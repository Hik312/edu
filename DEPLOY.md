# 部署与 AI 的取舍

**一句话结论：AI 精读是整条链路的最后一道可选工序，关掉它不影响任何核心功能。**

平台是两层结构：

- **底层（零 AI）**：卡片库、复习调度、笔记、知识框架、知识图谱、文档导入与分章阅读 —— 纯逻辑，任何机器都能跑。
- **顶层（可选）**：AI 精读（把一章正文整理成「一句话 / 类比 / 重点 / 原理拆解」）—— 唯一需要大模型的地方。没有它就少一个按钮，不是少半个应用。

> 后端**只有一个实现**：FastAPI 的 `back_study/run.py`，启动前要
> `pip install -r back_study/requirements.txt`（fastapi / uvicorn / **PyJWT** 是必需的）。
>
> 以前还有个零依赖版 `back_study/server.py`（一个包都不用装），**2026-09-26 已移除** ——
> 鉴权改用 PyJWT 之后它名不副实，而留着它意味着每个接口写两遍、冒烟跑两遍。
> 本文所有命令都写 `back_study/run.py`。

> 数据存哪儿也是**可切换的**：默认单文件 JSON，配上 MySQL 就换成数据库。
> 见下面「存储：什么时候该上数据库」一节。

---

## 三种部署形态

### 形态 1：电脑当服务器，手机同 WiFi 看（零成本，推荐）

```bash
python back_study/run.py 8080 --lan
```

启动时会直接把手机该访问的地址打出来：

```
serving  E:\AAA_实验室项目\study\web
API      http://127.0.0.1:8080/api/health
本机访问 http://127.0.0.1:8080/
交互文档 http://127.0.0.1:8080/docs
卡片 20 张（自定义 0）· 今日待复习 20
存储    MySQL 127.0.0.1:3306/study_cards · 卡 20 · 进度 0 · 笔记 0 · 文档 1
AI       本地模型 qwen3:8b（离线、免费）
手机同 WiFi: http://10.71.215.180:8080/     ← 真实网卡排第一
手机同 WiFi: http://192.168.88.1:8080/      ← 其余网卡也列出，虚拟网卡沉底
           若连不上：确认同一 WiFi + 放行防火墙 8080 端口（第一个通常是对的）
```

`存储` 那一行还有两种形态，都能正常服务，但**不能看错**：

```
存储    JSON 文件 data/store/（单机够用，多端同步要上 MySQL）
        !! 配置想用 mysql，实际回退成 json：127.0.0.1:3306 连不上（...）
```

带 `!!` 就是「你以为在用数据库，其实写进文件了」。原因也会写在 `/api/storage` 的
`degraded` 字段里，不用翻日志。

**AI 在这里是能用的** —— 直接复用本机 Ollama，离线免费。

注意几点：

- 电脑要开着，睡眠/关机就断（这是这个方案唯一的代价）。
- Windows 首次启动可能弹防火墙授权，勾「专用网络」放行。
- 手机和电脑必须在同一个 WiFi（不能一个连 5G 一个连有线到不同网段）。
- **地址探测按「像不像真实内网」打分排序**（`back_study/core/netinfo.py`，两版共用）：
  `gethostbyname` 在装了 VirtualBox / Hyper-V 的机器上会返回 `192.168.56.1` 这类 Host-Only
  地址；开了 TUN 模式的代理软件又会让 UDP 出口 IP 变成 `198.18.0.1`（fake-ip 段）——
  两种做法都会把手机引到死路。现在真实内网段加分、这些特殊段扣分，实测真实地址
  `10.71.215.180` 稳定排第一，虚拟网卡沉底但保留（万一你确实要在虚拟网络里用）。

### 形态 2：云服务器后端 + Qoder Sites 前端（公网 / 参赛提交）

前端是静态托管（Qoder Sites），后端在自己的云服务器上，AI 走云端 API。
三块各司其职：Sites 只发静态文件、跑不了 Python；1 核 2G 服务器跑不动 7B 模型。

```
浏览器 → Qoder Sites（web/dist 静态）
       → https://api.你的域名/api → nginx → 127.0.0.1:8081 FastAPI → MySQL
                                            → 硅基流动云端 API（对话/向量/视觉）
```

一键产物在 `back_study/deploy/`：systemd unit、`start_backend.sh`（真正 source
环境变量的入口）、nginx 配置、env 模板、setup.sh。

1. 服务器安全组**只放 80/443**；域名解析到服务器公网 IP（港澳台/海外节点免备案）。
2. 代码上服务器：git clone 仓库 + **单独 scp 本机 `study/data/`** ——
   卡片数据在 .gitignore 里，clone 下来是空库，setup.sh 会检查并拦下。
3. `bash back_study/deploy/setup.sh api.你的域名`
   （装依赖 → venv → systemd → nginx → certbot HTTPS，全自动）。
4. 编辑 `<仓库根>/app.env`：填 `LLM_API_KEY`（硅基流动控制台取）和
   `CORS_ORIGINS`（第 6 步拿到的 Sites 地址），`systemctl restart edupath`。
   密钥只进这一个文件（chmod 600），不进仓库、不进命令行历史。
   ⚠️ 变量**必须**写在这份文件里：systemd 的 `EnvironmentFile` 不跑 shell
   （引号、行内注释、变量展开静默失效），宝塔面板「环境变量」那栏压根不进守护进程
   —— 两种都表现为「配置写了、服务读到的是默认值」，且不报错。
5. 预置管理员：`.venv/bin/python scripts/make_admin.py <用户名> -`
   （密码交互输入）。模板里 `ADMIN_FIRST=0`：路人先注册只拿普通用户，
   不会像单机形态那样首个注册者自动成 admin。
6. 前端构建并发布：`web/` 下
   `VITE_API_BASE=https://api.你的域名/api npm run build`，
   把 `web/dist` 发布到 Qoder Sites；拿到的 Sites 地址回填第 4 步的
   `CORS_ORIGINS` 再重启一次后端。

验证：`curl https://api.你的域名/api/health` 返回 ok;浏览器开 Sites 地址
注册登录、背卡复习、文档问答（流式回答应逐段出字，不是整段砸出来）。

产物里已经处理掉的坑：

- nginx `proxy_buffering off`：不关的话 SSE 流式变成「转圈几十秒整段砸出来」。
- `client_max_body_size 16m`：与后端请求体闸门对齐，否则大 PDF 先吃 nginx 的 413。
- `proxy_read_timeout 300s`：云端精读一章可能跑一两分钟，默认 60s 会半路掐断。
- 后端只绑 127.0.0.1：公网入口只有 nginx 一个，服务端口不直接暴露。
- CORS 白名单：不写 Sites 地址，浏览器直接拦跨域请求（表现为全站接口报错）。

**本仓库线上这一套（宝塔 + 阿里云轻量，2026-11-16 起在跑）和上面步骤的差别：**

- 代码在 `/www/wwwroot/python/`（仓库根）+ `/www/wwwroot/python/back_study/`，
  venv 用宝塔建的 `edupath`：`/www/server/pyporject_evn/edupath/bin/python`
  （`pyporject_evn` 是宝塔自己拼错的，照抄）。数据在同级 `/www/wwwroot/python/data/`。
- **端口 8081，不是 8080**：这台机器 8080 被一个旧 Java 项目占着（`*:8080`），别去动它。
- HTTPS 用宝塔签发的 Let's Encrypt + 「网站 → 反代」，不是 certbot；
  入口 `https://edu.312783.xyz/api`。
- 进程由 **systemd `edupath` 单元**管（`deploy/edupath.service` + `deploy/start_backend.sh`
  两份文件的实际内容）。宝塔「网站 → Python项目」的启动/重启按钮在这台机器上
  **点了不拉起进程**（状态一直「未启动」、项目日志字节数不变），120 秒守护也不重启
  被外部 kill 的进程，「开机启动」默认还没勾 —— 所以别把它当进程管理器。
  改完配置统一 `systemctl restart edupath`；自愈已实测（`pkill` 后约 7 秒 health 回 200）。
- 主存储是 **MySQL**（库 `study`、账号 `study`，只监听 127.0.0.1）。踩过的坑：
  `core/store/schema.sql` 头部硬编码 `CREATE DATABASE study_cards ... USE study_cards`，
  而宝塔建的库名是 `study`、业务账号没有建库权限 → 直接 `mysql <` 会 ERROR 1044。
  导进已有库要把这两段剥掉：
  `sed -E '/CREATE DATABASE/,/;$/d; /^USE /d' schema.sql | mysql -u study -p'密码' study`。
  之后 `python back_study/scripts/dbseed.py --sync` 灌内置卡、`--import-json` 迁存量数据。

AI 仍是两条路，改 `app.env` 即可：**路线 A** `AI=off` 直接关掉精读（最省事，
其余功能全在）；**路线 B** 云端 API（env 模板默认，比本地 7B 质量好、按量付费）。
关掉 AI 时前端不会留个死按钮，而是把那一栏换成说明文字 —— 见下面「四种状态」。

### 形态 3：纯静态，连服务器都不要

卡片数据本来就是本地 JS（`data/*.js`），平台是 PWA、有 Service Worker。
可以把整个目录丢到静态托管（GitHub Pages / 对象存储 / 任意静态空间），手机加书签即可。

| 能用 | 不能用 |
|---|---|
| 卡片库、卡片墙、复习调度、笔记（存浏览器本地） | 文档导入、AI 精读 |

因为后两者要有 Python 进程：分章算法在后端，精读要连模型。
**如果只背卡片，这是最省事的方案。**

> 纯静态形态下**用不了 MySQL** —— 数据库是后端在连，没有后端就没有数据库。
> 不过复习进度会写浏览器 localStorage，单机背卡照样能用。

---

## 存储：什么时候该上数据库

| | JSON 文件（默认） | MySQL（可选） |
|---|---|---|
| 要装什么 | 什么都不用 | `pip install pymysql` + 一个 MySQL 8.0 |
| 多端同时写 | 有覆盖风险 | 事务保证 |
| 几千张卡 | 每次请求全量读进内存，明显慢 | 索引查询，量级不影响写法 |
| 备份 | 复制 `data/store/` 目录 | `mysqldump` |
| 换机器 | 拷目录就行 | 要导库 |
| 装不上/起不来时 | —— | 自动回退到 JSON，照常服务 |

**判断标准很简单**：只有你一台机器、一个设备在写 → JSON 就够了，别给自己加运维负担。
一旦出现「多台设备同时在写进度」「卡片涨到几千张」—— 上 MySQL。
（参赛这一套选了 MySQL：公网谁能注册谁就能写，进度/笔记/自定义卡落库比拷目录好备份，
也免得 `data/store/` 被当成 .gitignore 里的数据漏在服务器本地。）

### 上的步骤

```bash
# 1. 装驱动
back_study/.venv/Scripts/python.exe -m pip install pymysql

# 2. 打开配置（这个文件在 .gitignore 里，密码不会进版本库）
#    编辑 back_study/config.local.json：把 STORE 改成 "mysql"，填连接信息

# 3. 建库建表 + 把 data/*.js 灌进去
python back_study/scripts/dbseed.py --sync

# 4. 如果 data/store/*.json 里已有存量数据（进度/笔记/文档），搬进库（单向，会先备份）
python back_study/scripts/dbseed.py --import-json

# 5. 起服务，确认横幅上写的是 MySQL 而不是 JSON
python back_study/run.py 8080
```

关掉数据库同样是改一个字：`STORE` 改成 `"json"`。**不用改代码，也不用重启配置别的东西。**

### 云服务器上要注意

- MySQL 默认只监听 `127.0.0.1`。后端和数据库在同一台机器时**保持默认就好**，
  不要为了「方便」去开 `0.0.0.0:3306` —— 那等于把库直接挂公网上。
- 密码别用 root 账号跑业务库。建个只对 `study_cards` 有权限的账号：
  ```sql
  CREATE USER 'cards'@'127.0.0.1' IDENTIFIED BY '强密码';
  GRANT ALL PRIVILEGES ON study_cards.* TO 'cards'@'127.0.0.1';
  FLUSH PRIVILEGES;
  ```
  然后把 `config.local.json` 里的 `user` 换成 `cards`。
- `config.local.json` 里是明文密码，权限设紧一点（Linux 下 `chmod 600`）。

---

## 四种 AI 状态，前端都有对应处理

| 服务端情况 | 前端表现 | 其余功能 |
|---|---|---|
| 完全没有后端（静态托管） | 文档页提示「AI 精读要连后端」 | 卡片/复习/笔记正常（走本地数据） |
| 有后端，但连不上 Ollama | 提示三条出路 + 「重新检测」按钮 | **全部正常**，文档照常读 |
| 启动时设了 `AI=off` | 提示「已关闭」+ 「重新检测」按钮 | **全部正常** |
| 一切就绪 | 显示模型名，逐章精读 + 进度 | 全部正常 |

「重新检测」按钮是为「先起了服务、后来才把 Ollama 拉起来」这个常见顺序准备的，
点一下重新探测，不用整个页面刷新。

---

## 实测证据：AI 挂掉时其他功能真的不受影响

把 `OLLAMA_HOST` 指向一个死端口（模拟服务器上没装 Ollama），启动后逐个打接口：

```
AI 状态: ok=False  provider=ollama
         msg: 这台机器上没连上 Ollama（...）。三选一：① 装 Ollama ... ② 走云端 ... ③ 设 AI=off ...

health      HTTP 200      catalog     HTTP 200      cards   20 张
stats       HTTP 200      graph       HTTP 200      docs     1 份
outline     HTTP 200      notes       HTTP 200      文档阅读 15 章，已精读 10 章保留
drafts      HTTP 200      review/due  HTTP 200

只有这一条失败：
enrich      HTTP 502  →  「没找到可用模型。跑 `ollama pull qwen2.5:7b-instruct` 再试」
```

失败的是 **502 而不是 500**，且带人话文案 —— 这是刻意设计的：
「AI 不可用」是一个**正常状态**，不是异常，前端据此渲染提示而不是弹错误。

`AI=off` 时同理，`enrich` 返回「本服务关了 AI 精读（启动时设了 AI=off）」，其余接口全 200。

---

## 环境变量总表

| 变量 | 作用 | 示例 |
|---|---|---|
| `STORE` | `mysql` 用数据库，`json` 用文件（默认） | `mysql` |
| `MYSQL_HOST` / `MYSQL_PORT` | 数据库地址与端口 | `127.0.0.1` / `3306` |
| `MYSQL_USER` / `MYSQL_PASSWORD` | 数据库账号 | `cards` / `***` |
| `MYSQL_DB` | 库名 | `study_cards` |
| `AI` | `off` 直接关闭精读模块 | `AI=off` |
| `OLLAMA_HOST` | Ollama 地址（可指向另一台机器） | `http://192.168.1.5:11434` |
| `LLM_PROVIDER` | `cloud` 时走云端 | `cloud` |
| `LLM_API_KEY` | 云端密钥 | `sk-xxx` |
| `LLM_BASE_URL` | 云端接口地址（代码自动补 `/v1`） | `https://api.siliconflow.cn` |
| `LLM_MODEL` | 云端对话模型名 | `deepseek-ai/DeepSeek-V3.2` |
| `LLM_EMBED_MODEL` | 云端 embedding 模型名 | `BAAI/bge-m3` |
| `LLM_VLM_MODEL` | 云端视觉模型名（图表解读） | `Qwen/Qwen2.5-VL-7B-Instruct` |
| `ADMIN_FIRST` | `0` 关掉「首个注册者自动成 admin」（公开部署必设） | `0` |
| `CORS_ORIGINS` | 前端来源白名单，逗号分隔（公开部署必设） | `https://xx.qoder.site` |
| `VITE_API_BASE` | **前端构建期**变量：后端 API 地址，静态托管时必填 | `https://api.xx.com/api` |

存储配置优先级：**环境变量 > `back_study/config.local.json` > 默认值**。
AI 优先级：`AI=off` > 云端（需 `LLM_PROVIDER=cloud` + key）> Ollama。

---

## 怎么选

- **自己手机上看、电脑常开着** → `--lan`，AI 免费用，质量够（7B 约 6 秒/章）。
- **想让电脑休息 / 分享给别人** → 云服务器 + `AI=off`；要质量就配云端 key。
- **只背卡、不看导入的资料** → 纯静态托管，最省事。

> 补一句实话：本地 7B 的「类比」偶尔还是像说明书，「原理拆解」有时只是把重点换个说法。
> 真要质量，云端通道（路线 B）明显更好。代码两条路都留着，切一个环境变量的事。
