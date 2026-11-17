const api = require("../../utils/api");
const app = getApp();

//: home 聚合的缓存新鲜期。60s 内切回首页直接吃缓存、连网络都不打；
//: 超过就先用旧的渲染、后台再刷 —— 观感优先，数字最多旧 60s。
const HOME_TTL = 60 * 1000;

Page({
  data: {
    loading: true,
    error: "",
    stats: null,
    catalog: [],
    directions: [],
    pick: [], // 今日自选清单（挑过 CTA 就按清单口径）
    loggedIn: false,
    mastery: null, // BKT 掌握度汇总 {weak,mid,strong,computed,total}
  },

  onShow() {
    // 先用缓存秒开：有缓存就不显示「加载中…」，也不清空已有内容 ——
    // 切 tab 闪一下白屏/loading 是最容易被感知的「卡」。
    const c = app.cachePeek("home");
    if (c) this.apply(c);
    const m = app.cachePeek("mastery");
    if (m) this.setData({ mastery: m.summary });
    // 缓存够新就地取材；否则后台刷新（失败也不打断当前画面）
    if (!app.cacheFresh("home", HOME_TTL)) this.load(!c);
  },

  // 把一份 home 响应铺到页面上。缓存 / 网络两条来源都走这里，
  // 保证渲染的永远是同一套字段。
  apply(r) {
    app.globalData.catalogCache = r.catalog; // 卡包页显示科目中文名用
    app.globalData.directionsCache = r.directions; // 卡包页模块 chips 用
    // ⚠️ 补齐新字段，**别直接 r.stats 透传**。
    // 首页 wxml 用的是 stats.dueTodayPlan（后端新加的「今天实际要刷几张」，
    // = min(到期数, 20)），而 app.js 的 cache 是**纯内存**的（globalData.cache），
    // 只在本次小程序生命周期内存在。也就是说：后端重启前打开过一次、拿到的是
    // 旧结构（没有 dueTodayPlan），本次启动先 cachePeek 渲染 → 字段缺失 → 首页空白。
    // `dueToday ?? 20` 是兜底而不是正确值：真正要等下一次网络响应覆盖它。
    const s = r.stats || {};
    const st = Object.assign({}, s);
    if (typeof st.dueTodayPlan !== "number") {
      st.dueTodayPlan = Math.min(st.dueToday ?? 0, 20);
    }
    if (typeof st.dueLearned !== "number") st.dueLearned = 0;
    if (typeof st.fresh !== "number") st.fresh = st.unmarked ?? 0;
    this.setData({
      stats: st,
      catalog: r.catalog || [],
      directions: r.directions || [],
      pick: r.pick || [],
      loggedIn: true,
      loading: false,
      error: "",
    });
  },

  async load(showLoading) {
    if (showLoading) this.setData({ loading: true, error: "" });
    try {
      const r = await api.home();
      app.cacheSet("home", r);
      this.apply(r);
      // 掌握度条是「锦上添花」，绝不能拖慢首屏 —— 不 await，
      // 晚一点填上就行，拿不到也不影响其他内容。
      this.loadMastery();
    } catch (e) {
      if (e.status === 401) {
        // 没登录：交给下面的「未登录」引导卡，别报成加载失败
        this.setData({
          loading: false, loggedIn: false, stats: null,
          catalog: [], directions: [], pick: [], error: "",
        });
        return;
      }
      // 后台静默刷新失败时留着旧数据，别把已有画面打回空白
      if (this.data.stats) return;
      this.setData({ loading: false, error: e.msg || e.message });
    }
  },

  // 错误页「重试」
  reload() {
    this.load(true);
  },

  // BKT 掌握度汇总（只回 summary，不回 528 张卡明细）。
  // 单独一个请求而不是塞进 /api/mini/home：它是**派生数据** ——
  // 算法库（ALGO_STORE，现在是 JSON/Pg 那份）挂了或还没算过时它可以失败，
  // 首页其余部分照常。口径与网页端 /api/mastery?brief=1 同一份
  // （两端都走 db.mastery_report，2026-11-17 起路径收进 /api/mini/mastery）。
  async loadMastery() {
    try {
      const r = await api.masteryBrief();
      app.cacheSet("mastery", r);
      this.setData({ mastery: r.summary || null });
    } catch (e) {
      // 静默：没登录、或算法库不可用。不画那条分布条就是了。
    }
  },

  goLearn() {
    wx.switchTab({ url: "/pages/learn/learn" });
  },

  // 零状态（「今天都刷完了」）时的次要动作：去卡包学新卡
  goCards() {
    wx.switchTab({ url: "/pages/cards/cards" });
  },

  // tab 页带不了参数：写进 globalData，卡包页 onShow 读走并清空
  pickSubject(e) {
    app.globalData.pendingSubject = e.currentTarget.dataset.id;
    app.globalData.pendingDir = null; // 科目 / 方向互斥，别两个筛选叠着
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
