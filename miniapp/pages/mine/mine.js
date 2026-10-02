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
      this.setData({ stats: r.stats });
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
    this.setData({ busy: true, error: "" });
    try {
      const r =
        mode === "login"
          ? await api.login(username, password)
          : await api.register(username, password, displayName || username);
      app.login(r.token, r.user);
      this.setData({ user: r.user, busy: false });
      this.loadStats();
    } catch (e) {
      this.setData({ busy: false, error: e.msg || e.message });
    }
  },

  logout() {
    app.logout();
    this.setData({ user: null, stats: null, password: "" });
    wx.showToast({ title: "已退出", icon: "none" });
  },
});
