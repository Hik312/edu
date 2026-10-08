const api = require("../../utils/api");
const app = getApp();

//: 队列缓存新鲜期。15s 内切回来直接用缓存，不打网络；
//: 超过就先用旧的渲染、后台刷新。answer() 会同步写缓存，
//: 所以绝不会出现「刚答过的卡又冒出来」。
const QUEUE_TTL = 15 * 1000;

Page({
  data: {
    loading: true,
    error: "",
    queue: [],
    total: 0,
    doneCount: 0,
    cur: null, // 当前卡（队列头）
    detail: null, // 翻面时懒加载的全文
    revealed: false,
    submitting: false,
    // ---- 今日自选清单 ----
    pickMode: false, // 挑过清单就只推清单（清单空回退普通队列）
    pickCount: 0,
  },

  // 详情按 id 缓存：同一张卡二次翻面不再请求
  detailCache: {},

  onShow() {
    const c = app.cachePeek("queue");
    if (c) this.apply(c);
    if (!app.cacheFresh("queue", QUEUE_TTL)) this.reload(!c);
  },

  // 一份队列状态铺到页面。缓存 / 网络 / 答题后推进，三条路都走这里。
  apply(s) {
    const queue = s.queue || [];
    this.setData({
      queue,
      total: s.total || 0,
      doneCount: s.doneCount || 0,
      cur: queue[0] || null,
      pickMode: !!s.pickMode,
      pickCount: s.pickCount || 0,
      loading: false,
      error: "",
      revealed: false,
      detail: null,
    });
  },

  async reload(showLoading) {
    if (showLoading) {
      this.setData({ loading: true, error: "", revealed: false, detail: null });
    }
    try {
      // 先问清单：挑过就走清单队列，没挑按每日目标的普通队列。
      // 清单跨天作废由后端判，这里只读结果。
      let pick = [];
      try {
        const p = await api.pick();
        pick = p.ids || [];
      } catch (e) {
        /* 拿不到清单就当没挑，普通队列照常 */
      }
      const r = await api.queue(pick.length ? 100 : 20, pick.length > 0);
      const s = {
        queue: r.queue,
        total: r.queue.length,
        doneCount: 0,
        pickMode: pick.length > 0,
        pickCount: pick.length,
      };
      app.cacheSet("queue", s);
      this.apply(s);
    } catch (e) {
      if (e.status === 401) {
        app.goLogin();
        this.setData({ loading: false, error: "登录后才能同步复习进度" });
        return;
      }
      // 后台静默刷新失败时留着旧队列，别把画面打回空白
      if (this.data.cur) return;
      this.setData({ loading: false, error: e.msg || e.message });
    }
  },

  // 改用自动队列：清空清单（后端整体覆盖写），回到普通队列
  async clearPick() {
    if (this.data.submitting) return;
    this.setData({ submitting: true });
    try {
      await api.putPick([]);
      app.cacheDel("queue");
      this.setData({ submitting: false });
      this.reload(true);
    } catch (e) {
      this.setData({ submitting: false });
      wx.showToast({ title: e.msg || e.message, icon: "none" });
    }
  },

  // 点卡背 → 懒加载全文（mechanism / scene / why）
  async reveal() {
    if (!this.data.cur || this.data.revealed) return;
    const id = this.data.cur.id;
    let detail = this.detailCache[id];
    if (!detail) {
      try {
        const r = await api.card(id);
        detail = r.card;
        this.detailCache[id] = detail;
      } catch (e) {
        wx.showToast({ title: e.msg || e.message, icon: "none" });
        return;
      }
    }
    this.setData({ revealed: true, detail });
  },

  // level: 3 会 / 2 模糊 / 1 不会 → 记录后出下一张
  async answer(e) {
    const level = Number(e.currentTarget.dataset.level);
    const cur = this.data.cur;
    if (!cur || this.data.submitting) return;
    this.setData({ submitting: true });
    try {
      await api.review(cur.id, level);
      const s = {
        queue: this.data.queue.slice(1),
        total: this.data.total,
        doneCount: this.data.doneCount + 1,
        pickMode: this.data.pickMode,
        pickCount: this.data.pickCount,
      };
      app.cacheSet("queue", s); // 缓存同步推进，切回来不会重复看到已答的卡
      this.apply(s);
      this.setData({ submitting: false });
    } catch (e) {
      this.setData({ submitting: false });
      wx.showToast({ title: e.msg || e.message, icon: "none" });
    }
  },
});
