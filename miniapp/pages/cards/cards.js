const api = require("../../utils/api");
const app = getApp();

const PAGE_SIZE = 20;

Page({
  data: {
    loading: false,
    error: "",
    q: "",
    subject: "", // 从首页 chip 传来（globalData.pendingSubject）
    subjectName: "",
    dirs: "", // 选中的方向 id（模块筛，如 agent）；空 = 全部
    modName: "", // 方向中文名，逐张浏览时带到详情页当标题
    directions: [], // 方向目录（含 count），从 home 聚合缓存取
    cards: [],
    page: 1,
    hasMore: true,
    total: 0,
    pulling: false,
  },

  onShow() {
    const s = app.globalData.pendingSubject;
    const d = app.globalData.pendingDir;
    if (s || d) {
      app.globalData.pendingSubject = null;
      app.globalData.pendingDir = null;
      this.setData({
        subject: s || "",
        subjectName: s ? this.subjectNameOf(s) : "",
        dirs: d || "",
        modName: d ? this.dirNameOf(d) : "",
        cards: [],
        page: 1,
      });
      this.fetch(true);
    } else if (!this.data.cards.length && !this.data.loading) {
      this.fetch(true);
    }
  },

  onPullDownRefresh() {
    this.setData({ pulling: true });
    this.fetch(true).finally(() => {
      this.setData({ pulling: false });
      wx.stopPullDownRefresh();
    });
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) this.fetch(false);
  },

  subjectNameOf(id) {
    const cat = (app.globalData.catalogCache || []).find((c) =>
      (c.subjects || []).some((s) => s.id === id));
    const hit = cat && (cat.subjects || []).find((s) => s.id === id);
    return hit ? hit.name : id;
  },

  dirNameOf(id) {
    const d = (this.data.directions || []).find((x) => x.id === id);
    return d ? d.name : id;
  },

  // 方向目录只从 home 拿一次（卡包页自己不重拉：home 是聚合端点，
  // 缓存在 globalData，首页/卡包共用）
  async ensureDirections() {
    if (this.data.directions.length) return;
    if (app.globalData.directionsCache) {
      this.setData({ directions: app.globalData.directionsCache });
      return;
    }
    try {
      const r = await api.home();
      app.globalData.directionsCache = r.directions;
      this.setData({ directions: r.directions || [] });
    } catch (e) {
      // 拿不到方向目录只是少了 chips，卡列表照常能用
    }
  },

  async fetch(reset) {
    const page = reset ? 1 : this.data.page;
    this.setData({ loading: true, error: "" });
    try {
      await this.ensureDirections();
      const r = await api.cards({
        page,
        pageSize: PAGE_SIZE,
        q: this.data.q,
        subject: this.data.subject,
        dirs: this.data.dirs,
      });
      const list = (r.cards || []).map((c) => ({
        ...c,
        levelName: ["未标记", "不会", "模糊", "会"][c.level] || "未标记",
      }));
      this.setData({
        cards: reset ? list : this.data.cards.concat(list),
        page: page + 1,
        hasMore: !!r.hasMore,
        total: r.total,
        loading: false,
      });
    } catch (e) {
      this.setData({ loading: false, error: e.msg || e.message });
    }
  },

  onInput(e) {
    this.setData({ q: e.detail.value });
  },

  onSearch() {
    this.fetch(true);
  },

  pickDir(e) {
    const id = e.currentTarget.dataset.id || "";
    this.setData({
      dirs: id,
      modName: id ? this.dirNameOf(id) : "",
      cards: [],
      page: 1,
    });
    this.fetch(true);
  },

  clearFilter() {
    this.setData({ subject: "", subjectName: "", dirs: "", modName: "" });
    this.fetch(true);
  },

  // 带着当前筛选进详情：点列表里任意一张都能接着上一张/下一张翻
  openDetail(e) {
    const q = [
      "id=" + e.currentTarget.dataset.id,
      "dirs=" + encodeURIComponent(this.data.dirs),
      "subject=" + encodeURIComponent(this.data.subject),
      "q=" + encodeURIComponent(this.data.q),
      "modName=" + encodeURIComponent(this.data.modName),
    ].join("&");
    wx.navigateTo({ url: "/pages/detail/detail?" + q });
  },

  // 逐张浏览：入口按钮（从第一张开始）。browse=1 让详情页即便没有筛选
  // （全库浏览）也拉 ids 清单开翻页 —— 单靠筛选参数判断会漏掉这种情形。
  browse() {
    if (!this.data.cards.length) return;
    const q = [
      "id=" + this.data.cards[0].id,
      "dirs=" + encodeURIComponent(this.data.dirs),
      "subject=" + encodeURIComponent(this.data.subject),
      "q=" + encodeURIComponent(this.data.q),
      "modName=" + encodeURIComponent(this.data.modName),
      "browse=1",
    ].join("&");
    wx.navigateTo({ url: "/pages/detail/detail?" + q });
  },
});
