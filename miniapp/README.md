# Study 卡片库 · 小程序端

微信小程序骨架：翻卡复习 + 卡包搜索 + 进度统计。账号与网页端**同一套**
（/api/mini/* 签发的 token 就是网页端那个 JWT），进度共用。

接口规范（加接口/改参数前先读）：[`docs/小程序接口规范.md`](../docs/小程序接口规范.md)

## 目录

```
miniapp/
  app.js               登录态 + request 封装（BASE、token、{ok:false}→异常）
  app.json             5 个页面 + 4 个 tab
  app.wxss             暗色主题变量、card/chip/btn 公共样式
  utils/api.js         接口层：页面不直接拼路径，按域分组
  pages/index/         首页：统计四宫格 + 今日待复习 CTA + 分类/方向入口
  pages/learn/         学习：复习队列翻卡，「不会/模糊/会」三键作答
  pages/cards/         卡包：搜索（空格=都要命中）+ 科目筛选 + 下拉刷新/触底加载
  pages/detail/        详情：机制步骤、场景、类比、面试问法、相关卡跳转
  pages/mine/          我的：登录/注册、进度统计、退出
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

1. 后端起服务（仓库根）：
   ```
   back_study\.venv\Scripts\python.exe back_study\run.py 8099
   ```
2. 微信开发者工具 → 导入项目 → 选 `miniapp/` 目录（AppID 用测试号即可）。
3. 项目设置勾掉 **「不校验合法域名」**（开发期直连 `127.0.0.1:8099`）。
4. 本地改端口/上线换域名：只动 `app.js` 顶部 `BASE`；上线要在小程序后台
   配 https 合法域名。

## 约定

- 页面只在 `utils/api.js` 里引用路径；改接口先改规范文档，再改 api.js。
- 公共样式用 `app.wxss` 的变量（`--bg/--accent/…`），页面 wxss 只写页面特有部分。
- 错误展示用后端 `msg`（`{ok:false,msg}`），不要自己编文案。
- 图示（diagram）小程序端只显示种类占位，逐步播放器在网页端 —— 不重复实现。
