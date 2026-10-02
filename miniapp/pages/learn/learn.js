const api = require("../../utils/api");
const app = getApp();

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
    this.reload();
  },

  async reload() {
    this.setData({ loading: true, error: "", revealed: false, detail: null });
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
      this.setData({
        queue: r.queue,
        total: r.queue.length,
        doneCount: 0,
        loading: false,
        cur: r.queue[0] || null,
        pickMode: pick.length > 0,
        pickCount: pick.length,
      });
    } catch (e) {
      if (e.status === 401) {
        app.goLogin();
        this.setData({ loading: false, error: "登录后才能同步复习进度" });
      } else {
        this.setData({ loading: false, error: e.msg || e.message });
      }
    }
  },

  // 改用自动队列：清空清单（后端整体覆盖写），回到普通队列
  async clearPick() {
    if (this.data.submitting) return;
    this.setData({ submitting: true });
    try {
      await api.putPick([]);
      this.setData({ submitting: false });
      this.reload();
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
      const queue = this.data.queue.slice(1);
      this.setData({
        queue,
        doneCount: this.data.doneCount + 1,
        cur: queue[0] || null,
        revealed: false,
        detail: null,
        submitting: false,
      });
    } catch (e) {
      this.setData({ submitting: false });
      wx.showToast({ title: e.msg || e.message, icon: "none" });
    }
  },
});
