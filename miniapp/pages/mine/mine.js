const api = require("../../utils/api");
const app = getApp();

Page({
  data: {
    mode: "login", // login | register
    username: "",
    password: "",
    displayName: "",
    busy: false,
    error: "",
    user: null,
    stats: null,
  },

  onShow() {
    const user = app.globalData.user;
    this.setData({ user });
    if (user) this.loadStats();
  },

  async loadStats() {
    try {
      const r = await api.home();
      // 兜底同首页：dueTodayPlan / dueLearned / fresh 是 2026-10-03 新加的字段，
      // 对着旧后端（或后端重启前的旧响应）时缺失，wxml 会渲染出空白格。
      // 这里补齐而不是让模板写 `stats.dueTodayPlan || '-'` ——
      // 缺字段是**数据问题**，该在数据入口补，不该散在每个视图里。
      const s = Object.assign({}, r.stats || {});
      if (typeof s.dueTodayPlan !== "number") {
        s.dueTodayPlan = Math.min(s.dueToday ?? 0, 20);
      }
      if (typeof s.dueLearned !== "number") s.dueLearned = 0;
      if (typeof s.fresh !== "number") s.fresh = s.unmarked ?? 0;
      this.setData({ stats: s });
    } catch (e) {
      if (e.status === 401) app.logout();
    }
  },

  switchMode() {
    this.setData({ mode: this.data.mode === "login" ? "register" : "login", error: "" });
  },

  onField(e) {
    this.setData({ [e.currentTarget.dataset.field]: e.detail.value });
  },

  async submit() {
    const { mode, username, password, displayName } = this.data;
    if (!username || !password) {
      this.setData({ error: "用户名和密码都要填" });
      return;
    }
    // 防连点：连点五下会发五个注册请求，第四个开始后端就报「用户名已存在」，
    // 用户会以为自己刚起的名字被别人抢了。
    if (this.data.busy) return;
    this.setData({ busy: true, error: "" });
    try {
      const r =
        mode === "login"
          ? await api.login(username, password)
          : await api.register(username, password, displayName || username);
      app.login(r.token, r.user);
      this.setData({ user: r.user, busy: false, password: "" });
      this.loadStats();
      // ★ 原来登录完什么都不说，用户还停在「我的」页，以为没成功又点一次
      //   （于是撞上「用户名已存在」）。要明确告诉他：成了，且下一步去哪。
      wx.showToast({ title: mode === "login" ? "登录成功" : "注册成功", icon: "success" });
      // 首页才是「今天学什么」，登录的意义就是能开始学 —— 直接送过去
      setTimeout(() => wx.switchTab({ url: "/pages/index/index" }), 600);
    } catch (e) {
      this.setData({ busy: false, error: e.message });
    }
  },

  logout() {
    app.logout();
    this.setData({ user: null, stats: null, password: "" });
    wx.showToast({ title: "已退出", icon: "none" });
  },
});
