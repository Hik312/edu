// 全局：登录态 + 请求封装 + 跨页传参
//
// 账号体系与 web 端同一套（/api/mini/auth/* 签发的 token 就是 web 那个 JWT），
// 所以这里只存 token，不做第二套会话。开发期在开发者工具里勾
// 「不校验合法域名」直连本地；上线换 https 域名时只动 BASE。
const BASE = "http://127.0.0.1:8099";

App({
  globalData: {
    token: "",
    user: null,
    // 首页点分类 → 卡包页 onShow 读一次后清空（tab 页不能带参，用这个传）
    pendingSubject: null,
    pendingDomain: null,
    pendingDir: null, // 首页方向卡 → 卡包页模块筛（同 pendingSubject 的套路）
    directionsCache: null, // 首页聚合里的方向目录，卡包页 chips 复用
  },

  onLaunch() {
    const token = wx.getStorageSync("token");
    if (!token) return;
    this.globalData.token = token;
    // 本地 token 可能已过期，拿 /me 验一次，401 就静默清掉（各页会引导登录）
    this.request("/api/mini/auth/me")
      .then((r) => {
        this.globalData.user = r.user;
        this.onUserReady && this.onUserReady(r.user);
      })
      .catch(() => this.logout());
  },

  // 统一请求：拼 BASE、带 token、把 {ok:false,msg} 当异常抛
  request(path, { method = "GET", data } = {}) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: BASE + path,
        method,
        data,
        header: { Authorization: "Bearer " + this.globalData.token },
        success(res) {
          const body = res.data || {};
          if (res.statusCode >= 200 && res.statusCode < 300 && body.ok !== false) {
            resolve(body);
          } else {
            const err = new Error(body.msg || "请求失败 " + res.statusCode);
            err.status = res.statusCode;
            err.msg = body.msg;
            reject(err);
          }
        },
        fail(e) {
          reject(new Error(e.errMsg || "网络异常"));
        },
      });
    });
  },

  login(token, user) {
    this.globalData.token = token;
    this.globalData.user = user;
    wx.setStorageSync("token", token);
    this.onUserReady && this.onUserReady(user);
  },

  logout() {
    this.globalData.token = "";
    this.globalData.user = null;
    wx.removeStorageSync("token");
  },

  // 未登录时统一跳「我的」tab（登录表单在那）
  goLogin() {
    wx.switchTab({ url: "/pages/mine/mine" });
    wx.showToast({ title: "请先登录", icon: "none" });
  },
});
