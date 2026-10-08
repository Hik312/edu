const api = require("../../utils/api");
const app = getApp();

Page({
  data: {
    loading: true,
    error: "",
    card: null,
    levelName: "未标记",
    // ---- 逐张浏览（从卡包带筛选进来时才有值） ----
    browsing: false,
    modName: "",
    modEmoji: "",
    pos: 0, // 当前在清单里的下标
    total: 0,
    // ---- 今日自选清单 ----
    picked: false, // 这张卡在不在清单里
    canPick: false, // 拿到过清单才显示按钮（未登录/失败时别让人点了报错）
    pickBusy: false,
  },

  onLoad(query) {
    this.id = query.id;
    // 清单 id 先给空数组：load/goto 会读它，等 loadPick 回来再覆盖
    this.pickIds = [];
    // 筛选参数（dirs/subject/q）原样保留：翻页、相关卡跳转都要带同一份
    this.filter = {
      dirs: query.dirs || "",
      subject: query.subject || "",
      q: query.q || "",
    };
    this.modName = query.modName || "";
    this.modEmoji = query.modEmoji || "";
    this.load();
    // 有筛选、或明确点进浏览模式（browse=1）→ 拉 id 清单开翻页
    if (query.browse || this.filter.dirs || this.filter.subject || this.filter.q) {
      this.loadList();
    }
    this.loadPick();
  },

  async load() {
    this.setData({ loading: true, error: "" });
    try {
      const r = await api.card(this.id);
      const level = r.card.level || 0;
      this.setData({
        card: r.card,
        levelName: ["未标记", "不会", "模糊", "会"][level] || "未标记",
        loading: false,
        picked: this.pickIds.includes(this.id),
      });
      wx.setNavigationBarTitle({ title: r.card.title || "卡片详情" });
    } catch (e) {
      this.setData({ loading: false, error: e.msg || e.message });
    }
  },

  // 逐张浏览的 id 清单：一次 idsOnly 拿全（模块最多几百张，别按页翻）
  async loadList() {
    try {
      const r = await api.cards({
        page: 1,
        pageSize: 50,
        q: this.filter.q,
        subject: this.filter.subject,
        dirs: this.filter.dirs,
        idsOnly: true,
      });
      const ids = r.ids || [];
      const pos = ids.indexOf(this.id);
      if (pos < 0) return; // 当前卡不在筛选里（如相关卡跳过来的）→ 不进浏览模式
      this.ids = ids;
      this.setData({
        browsing: true,
        pos,
        total: ids.length,
        modName: this.modName,
        modEmoji: this.modEmoji,
      });
    } catch (e) {
      // 拿不到清单只是少了翻页条，单卡照常看
    }
  },

  async loadPick() {
    try {
      const r = await api.pick();
      this.pickIds = r.ids || [];
      this.setData({ canPick: true, picked: this.pickIds.includes(this.id) });
    } catch (e) {
      this.pickIds = []; // 未登录/失败：藏起按钮，别让人点了报错
      this.setData({ canPick: false, picked: false });
    }
  },

  // ---- 上一张 / 下一张：换 id 重新拉，清单状态跟着走 ----
  prev() {
    if (this.data.pos <= 0) return;
    this.goto(this.ids[this.data.pos - 1]);
  },
  next() {
    if (this.data.pos >= this.ids.length - 1) return;
    this.goto(this.ids[this.data.pos + 1]);
  },
  goto(id) {
    this.id = id;
    this.setData({ pos: this.ids.indexOf(id), picked: this.pickIds.includes(id) });
    this.load();
    wx.pageScrollTo({ scrollTop: 0, duration: 200 });
  },

  // ---- 加入 / 移出今日清单（整体覆盖式 PUT，后端过滤去重） ----
  async togglePick() {
    if (!this.data.canPick || this.data.pickBusy) return;
    this.setData({ pickBusy: true });
    const on = this.data.picked;
    // 先改本地再发请求，成功后用服务端回存的那份回填（它做了去重/截断）
    const next = on ? this.pickIds.filter((x) => x !== this.id) : this.pickIds.concat(this.id);
    try {
      const r = await api.putPick(next);
      this.pickIds = r.ids || [];
      this.setData({ picked: this.pickIds.includes(this.id) });
      wx.showToast({ title: on ? "已移出今日清单" : "已加入今日清单", icon: "none" });
    } catch (e) {
      wx.showToast({ title: e.msg || e.message, icon: "none" });
    } finally {
      this.setData({ pickBusy: false });
    }
  },

  // 相关卡跳转（detail 非 tab 页，可 push 同页栈）。
  // 带着筛选参数：相关卡在当前模块里就继续逐张浏览，不在就单看这一张。
  openRelated(e) {
    const id = e.currentTarget.dataset.id;
    const q = ["id=" + encodeURIComponent(id)];
    if (this.filter.dirs) q.push("dirs=" + encodeURIComponent(this.filter.dirs));
    if (this.filter.subject) q.push("subject=" + encodeURIComponent(this.filter.subject));
    if (this.filter.q) q.push("q=" + encodeURIComponent(this.filter.q));
    if (this.modName) q.push("modName=" + encodeURIComponent(this.modName));
    if (this.modEmoji) q.push("modEmoji=" + encodeURIComponent(this.modEmoji));
    wx.redirectTo({ url: "/pages/detail/detail?" + q.join("&") });
  },

  goReview() {
    wx.switchTab({ url: "/pages/learn/learn" });
  },
});
