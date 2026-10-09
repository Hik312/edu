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

  // ---- 首页聚合 /api/mini/home ----
  home() {
    return app.request("/api/mini/home");
  },

  // ---- BKT 掌握度汇总 /api/mastery?brief=1 ----
  // brief=1 只回 summary + params，不回 400 张卡明细 —— 首页只画一条分布条，
  // 拉明细在手机上是纯浪费流量。
  masteryBrief() {
    return app.request("/api/mastery?brief=1");
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
  // pick=true 只回今日自选清单里的卡（清单空 → 空队列，不退化成普通队列）
  // all=true  忽略每日目标，把今天全部到期的都给了 —— 首页那20 张刷完、
  //            库里还剩几百张时用（后端上限 100）
  queue(limit = 20, pick = false, all = false) {
    const p = (pick ? "&pick=1" : "") + (all ? "&all=1" : "");
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
