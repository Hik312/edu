// 接口层：按「页面要用什么」分组，页面不直接拼路径。
// 路径与后端 app/routers/mini/ 一一对应（接口规范见 miniapp/README.md）。
const app = getApp();

const api = {
  // ---- 认证 /api/mini/auth ----
  login(username, password) {
    return app.request("/api/mini/auth/login", {
      method: "POST",
      data: { username, password },
    });
  },
  register(username, password, displayName) {
    return app.request("/api/mini/auth/register", {
      method: "POST",
      data: { username, password, displayName },
    });
  },
  me() {
    return app.request("/api/mini/auth/me");
  },

  // ---- 后端自检 /api/health ----
  // 裸 /api 路径的唯一豁免：它是**免鉴权的运维探针**，不属于任何一端的数据面
  // （routers/__init__.py 那条「mini 一律 /api/mini/*」管的是带调用方语义的
  // 接口；这个两端共用，DEPLOY.md 的验证命令也打它）。
  // 用途见 app.js checkBackend()：证明 BASE 指的都是本项目，
  // framework 字段恒 'fastapi'，撞端口时会拿到别的服务。
  health() {
    return app.request("/api/health");
  },

  // ---- 首页聚合 /api/mini/home ----
  home() {
    return app.request("/api/mini/home");
  },

  // ---- BKT 掌握度汇总 /api/mini/mastery ----
  // 只回 summary + params，不回 528 张卡明细 —— 首页只画一条分布条，
  // 拉明细在手机上是纯浪费流量。
  // ★ 2026-11-17 从裸 `/api/mastery?brief=1` 挪过来：按自家规范第 2 条，
  //   小程序不许打 /api/xxx（裸路径分不清调用方）。口径没变，
  //   两端都走 db.mastery_report，阈值只有一份。
  masteryBrief() {
    return app.request("/api/mini/mastery");
  },

  // ---- 卡包 /api/mini/cards ----
  // dirs: 方向 id（模块筛，如 agent），逗号分隔
  // idsOnly: true 只回 {ids, total} —— 详情页逐张浏览要一次拿全模块 id 清单
  cards({ page = 1, pageSize = 20, q = "", subject = "", domain = "", dirs = "",
    idsOnly = false } = {}) {
    const qs = `page=${page}&pageSize=${pageSize}&q=${encodeURIComponent(q)}` +
      `&subject=${encodeURIComponent(subject)}&domain=${encodeURIComponent(domain)}` +
      `&dirs=${encodeURIComponent(dirs)}` +
      (idsOnly ? "&idsOnly=1" : "");
    return app.request("/api/mini/cards?" + qs);
  },
  card(id) {
    return app.request("/api/mini/cards/" + id);
  },

  // ---- 复习 /api/mini/review ----
  // limit=0（默认）= 按**档案里的每日目标**（web 端能改，存后端 profile）。
  // ★ 别再在这里写死 20 —— 那样用户在网页端把目标设成 50，小程序仍只给 20 张，
  //   同一套账号两个数字（后端 `_plan_limit` 的注释就是为这件事写的）。
  // pick=true 只回今日自选清单里的卡（清单空 → 空队列，不退化成普通队列）
  // all=true  忽略每日目标，把今天全部到期的都给了 —— 首页那 20 张刷完、
  //            库里还剩几百张时用（后端上限 100）
  // dirs:     学习方向 id，逗号分隔。口径与 web 端 /review/due 一致，
  //            筛选发生在截断之前（后端 review_queue 里做的）。
  // by:       'level'（默认，按自评档位排）| 'bkt'（掌握度低的先学）
  queue(limit = 0, pick = false, all = false, dirs = "", by = "") {
    const p =
      (pick ? "&pick=1" : "") +
      (all ? "&all=1" : "") +
      (dirs ? "&dirs=" + encodeURIComponent(dirs) : "") +
      (by ? "&by=" + encodeURIComponent(by) : "");
    return app.request(`/api/mini/review/queue?limit=${limit}${p}`);
  },
  // level: 1 不会 / 2 模糊 / 3 会
  review(id, level) {
    return app.request("/api/mini/review/" + id, {
      method: "POST",
      data: { level },
    });
  },

  // ---- 今日自选清单 /api/mini/review/pick ----
  // 一天几百张到期刷不完 —— 用户自己点名今天刷哪些，跨天自动作废
  pick() {
    return app.request("/api/mini/review/pick");
  },
  putPick(ids) {
    return app.request("/api/mini/review/pick", {
      method: "PUT",
      data: { ids },
    });
  },
};

module.exports = api;
