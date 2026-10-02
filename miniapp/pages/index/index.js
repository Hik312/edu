const api = require("../../utils/api");
const app = getApp();

Page({
  data: {
    loading: true,
    error: "",
    stats: null,
    catalog: [],
    directions: [],
    pick: [], // 今日自选清单（挑过 CTA 就按清单口径）
    loggedIn: false,
  },

  onShow() {
    this.load();
  },

  async load() {
    this.setData({ loading: true, error: "" });
    try {
      const r = await api.home();
      app.globalData.catalogCache = r.catalog; // 卡包页显示科目中文名用
      app.globalData.directionsCache = r.directions; // 卡包页模块 chips 用
      this.setData({
        stats: r.stats,
        catalog: r.catalog,
        directions: r.directions,
        pick: r.pick || [],
        loggedIn: !!app.globalData.user,
        loading: false,
      });
    } catch (e) {
      this.setData({ loading: false, error: e.msg || e.message });
    }
  },

  goLearn() {
    wx.switchTab({ url: "/pages/learn/learn" });
  },

  // tab 页带不了参数：写进 globalData，卡包页 onShow 读走并清空
  pickSubject(e) {
    app.globalData.pendingSubject = e.currentTarget.dataset.id;
    wx.switchTab({ url: "/pages/cards/cards" });
  },

  // 模块入口：方向 → 卡包页按该模块筛，进去就能逐张翻
  pickDir(e) {
    app.globalData.pendingDir = e.currentTarget.dataset.id;
    app.globalData.pendingSubject = null;
    wx.switchTab({ url: "/pages/cards/cards" });
  },

  goMine() {
    wx.switchTab({ url: "/pages/mine/mine" });
  },
});
