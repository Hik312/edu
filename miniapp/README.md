# Study 卡片库 · 小程序端

微信小程序骨架：翻卡复习 + 卡包搜索 + 进度统计。账号与网页端**同一套**
（/api/mini/* 签发的 token 就是网页端那个 JWT），进度共用。

接口规范（加接口/改参数前先读）：[`docs/小程序接口规范.md`](../docs/小程序接口规范.md)

## 目录

```
miniapp/
  app.js               登录态 + request 封装（BASE、token、{ok:false}→异常）
                       + checkBackend()：打 /api/health 自证连的是本项目
  app.json             5 个页面 + 4 个 tab
  app.wxss             暗色主题变量、card/chip/btn 公共样式
  utils/api.js         接口层：页面不直接拼路径，按域分组
  pages/index/         首页：统计四宫格 + 今日待复习 CTA + 分类/方向入口
  pages/learn/         学习：复习队列翻卡，「不会/模糊/会」三键作答
  pages/cards/         卡包：搜索（空格=都要命中）+ 模块图标横滑条（emoji 筛选）+ 科目筛选 + 下拉刷新/触底加载
  pages/detail/        详情：机制步骤、场景、类比、面试问法、相关卡跳转
  pages/mine/          我的：登录/注册、进度统计、后端状态、退出
```

## 页面数据流

- **跨页传参**：tab 页不能带 query —— 首页点科目写
  `app.globalData.pendingSubject`，卡包页 `onShow` 读走即清。
- **翻卡懒加载**：队列只给 brief，点「显示答案」才 `GET /cards/{id}`，
  按 id 缓存（`learn.js` 的 `detailCache`），同一张卡不重复请求。
- **登录态**：`app.js onLaunch` 拿本地 token 验 `/me`，401 静默清除；
  各页 401 → `app.goLogin()` 跳「我的」tab。**不做** wx.login 一键登录——
  账号体系自建，与网页端共用。

## 本地跑起来

`app.js` 顶部 `BASE` 现在指向**线上** `https://edu.312783.xyz`，直接导入就能连到
真后端（真机预览也是它，前提是合法域名已配或勾了不校验）。要打本地后端：

1. 起后端（端口用 **8081**，`run.py` 的默认值）：
   ```
   back_study\.venv\Scripts\python.exe back_study\run.py 8081
   ```
   ⚠️ 别用 8080：本地 8080 历史上撞过 Ollama，服务器上 8080 是一个旧 Java 项目。
   撞端口最阴的是它**回 200 + JSON**，看起来完全像通了 —— 「我的」页那一块
   后端状态就是为这个加的（`/api/health` 的 `framework` 字段对不上就说「这不是
   EduPath 后端」）。
2. `app.js` 换成注释里那行 `const BASE = "http://127.0.0.1:8081";`
   （在开发者工具勾上**「不校验合法域名」**才允许 http/localhost）。
3. 微信开发者工具 → 导入项目 → 选 `miniapp/` 目录（AppID 用测试号即可）。
4. 真机本地联调：`127.0.0.1` 在手机上指的是**手机自己**，要换成电脑的局域网 IP
   （后端加 `--lan`），且手机和电脑同一 Wi-Fi。
5. 正式上线：小程序后台配 https 合法域名，且**小程序本身要完成备案**才能发布
   —— 开发版/体验版不受域名白名单限制，靠调试开关跑。

## 约定

- 页面只在 `utils/api.js` 里引用路径；改接口先改规范文档，再改 api.js。
- 公共样式用 `app.wxss` 的变量（`--bg/--accent/…`），页面 wxss 只写页面特有部分。
- 错误展示用后端 `msg`（`{ok:false,msg}`），不要自己编文案。
- 图示（diagram）小程序端只显示种类占位，逐步播放器在网页端 —— 不重复实现。
- 复习队列**不写死张数**：`api.queue()` 的 `limit` 默认 `0` = 按这个人档案里的
  每日目标（网页端「个人中心」能改）。写死 20 就等于同一个账号两个数字 ——
  后端 `mini/learn.py` 的 `_plan_limit` 注释就是为这件事留的。
  只有两处例外：`all=1`（用户点了「继续刷剩下的」）和挑了自选清单（清单就是
  他对「今天做多少」的显式表态）。
- 手机只拿手机用得上的字段：列表走 `_brief`（没有 mechanism/scene），
  掌握度走 `/api/mini/mastery`（只有分布，没有 528 张明细）。
