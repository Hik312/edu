const api = require("../../utils/api");
const app = getApp();

const PAGE_SIZE = 20;
// 卡列表第一页的缓存新鲜期。60s 内切回卡包页直接吃缓存、连网络都不打；
// 超过就先用旧的渲染、后台再刷 —— 和首页 / 学习页同一套观感优化。
const CARD_TTL = 60 * 1000;

Page({
  data: {
    loading: false,
    error: "",
    q: "",
    subject: "", // 从首页 chip 传来（globalData.pendingSubject）
    subjectName: "",
    dirs: "", // 选中的方向 id（模块筛，如 agent）；空 = 全部
    modName: "", // 方向中文名，逐张浏览时带到详情页当标题
    modEmoji: "", // 方向图标，详情页浏览条跟着显示
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
        modEmoji: d ? this.dirEmojiOf(d) : "",
        cards: [],
        page: 1,
      });
      this.fetch(true, true);
      return;
    }
    // 没带新筛选进来：已有卡就留着（切 tab 不闪），没卡先吃缓存秒开再后台刷新
    if (!this.data.cards.length) {
      const key = this.cacheKey();
      const hit = app.cachePeek(key);
      if (hit) this.applyPage(hit, false); // 先渲染缓存，不显示 loading
      // 缓存够新就就地取材；否则后台刷新（失败也留着旧画面）
      if (!app.cacheFresh(key, CARD_TTL)) this.fetch(true, !hit);
    }
  },

  // 当前筛选的缓存键：科目 / 方向 / 关键词任一变都算不同缓存
  cacheKey() {
    return "cards:" + [this.data.subject || "", this.data.dirs || "",
      this.data.q || ""].join("|");
  },

  onPullDownRefresh() {
    this.setData({ pulling: true });
    this.fetch(true, true).finally(() => {
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

  dirEmojiOf(id) {
    const d = (this.data.directions || []).find((x) => x.id === id);
    return (d && d.emoji) || "";
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

  async fetch(reset, showLoading) {
    const page = reset ? 1 : this.data.page;
    if (showLoading) this.setData({ loading: true, error: "" });
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
      // 只有重置（第一页）才写缓存：深翻页是临时状态，不该覆盖首页快照
      if (reset) {
        app.cacheSet(this.cacheKey(), {
          cards: this.data.cards,
          page: this.data.page,
          hasMore: this.data.hasMore,
          total: this.data.total,
        });
      }
    } catch (e) {
      // 后台静默刷新失败时（缓存画面还在）留着旧数据，别把已有卡打回空白
      if (this.data.cards.length) return;
      this.setData({ loading: false, error: e.msg || e.message });
    }
  },

  // 把一份「卡列表第一页」铺到页面上。缓存 / 网络两条来源都走这里，
  // 保证渲染的永远是同一套字段。
  applyPage(p, showLoading) {
    this.setData({
      cards: p.cards || [],
      page: p.page || 1,
      hasMore: !!p.hasMore,
      total: p.total || 0,
      loading: !!showLoading,
      error: "",
    });
  },

  onInput(e) {
    this.setData({ q: e.detail.value });
  },

  onSearch() {
    this.fetch(true, true);
  },

  pickDir(e) {
    const id = e.currentTarget.dataset.id || "";
    this.setData({
      dirs: id,
      modName: id ? this.dirNameOf(id) : "",
      modEmoji: id ? this.dirEmojiOf(id) : "",
      cards: [],
      page: 1,
    });
    this.fetch(true, true);
  },

  clearFilter() {
    this.setData({ subject: "", subjectName: "", dirs: "", modName: "", modEmoji: "" });
    this.fetch(true, true);
  },

  // 带着当前筛选进详情：点列表里任意一张都能接着上一张/下一张翻
  openDetail(e) {
    const q = [
      "id=" + e.currentTarget.dataset.id,
      "dirs=" + encodeURIComponent(this.data.dirs),
      "subject=" + encodeURIComponent(this.data.subject),
      "q=" + encodeURIComponent(this.data.q),
      "modName=" + encodeURIComponent(this.data.modName),
      "modEmoji=" + encodeURIComponent(this.data.modEmoji),
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
      "modEmoji=" + encodeURIComponent(this.data.modEmoji),
      "browse=1",
    ].join("&");
    wx.navigateTo({ url: "/pages/detail/detail?" + q });
  },
});
