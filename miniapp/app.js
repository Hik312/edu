// 全局：登录态 + 请求封装 + 跨页传参
//
// 账号体系与 web 端同一套（/api/mini/auth/* 签发的 token 就是 web 那个 JWT），
// 所以这里只存 token，不做第二套会话。
//
// ★ BASE 三个必须同时对：
//   ① **端口** —— 后端跑在 8080（back_study/run.py + app/main.py），
//      这里曾写成 8099，于是所有请求都 connection refused，
//      表现为「登录不行」，但代码里看不出是地址错。
//   ② **主机** —— 真机/模拟器上 `127.0.0.1` 指的是**手机自己**，不是电脑。
//      开发者工具「不校验合法域名」时可以用127.0.0.1；
//      真机预览必须换成电脑的局域网 IP，且手机和电脑要在同一 Wi-Fi。
//      → 换机器/换网络时只改这一行。
//   ③ **协议** —— 上线必须 https（微信小程序不允许 http 请求）。
const BASE = "http://127.0.0.1:8080";

App({
  globalData: {
    token: "",
    user: null,
    // 首页点分类 → 卡包页 onShow 读一次后清空（tab 页不能带参，用这个传）
    pendingSubject: null,
    pendingDomain: null,
    pendingDir: null, // 首页方向卡 → 卡包页模块筛（同 pendingSubject 的套路）
    directionsCache: null, // 首页聚合里的方向目录，卡包页 chips 复用
    // 接口响应缓存：key -> { at: 时间戳, data: 响应体 }。
    // 用途见 cachePeek/cacheFresh —— tab 页每次 onShow 都重拉会让切页看到
    // 「加载中…」闪一下，先渲染缓存再后台刷新就没这个观感问题。
    cache: {},
  },

  onLaunch() {
    const token = wx.getStorageSync("token");
    if (!token) return;
    this.globalData.token = token;
    // 本地 token 可能已过期，拿 /me 验一次。
    // ★ 只在**确实是 401** 时静默清掉；网络不通（e.net）不能清 ——
    //   地铁里进小程序、token 其实还有效，把它清掉等于逼用户重登一次。
    //   也不静默：那种情况下至少留个标记，让页面能显示「离线/连不上」。
    this.request("/api/mini/auth/me")
      .then((r) => {
        this.globalData.user = r.user;
        this.onUserReady && this.onUserReady(r.user);
      })
      .catch((e) => {
        if (e.status === 401) this.logout();
        else this.globalData.netDown = true;
      });
  },

  // 统一请求：拼 BASE、带 token、把 {ok:false,msg} 当异常抛
  //
  // ★ 失败分两类，必须分开报，否则用户（和开发者）无从下手：
  //   fail()      → **网络没通**（地址错/后端没起/断网）。wx 的 errMsg 是
  //                 "request:fail ..." 这种机器话，直接甩给用户等于没说话。
  //                 这里翻成「连不上服务器，检查 BASE 地址/后端是否启动」。
  //   status≥400  → **业务错误**（密码错/没登录/参数不对），后端有中文 msg，
  //                 直接用它是最好的。
  // 之前两者都走 `e.message`，于是「登录不行」既可能是密码错也可能是端口错，
  // 排查只能靠猜 —— BASE 写错 8099 就是这样被藏了很久。
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
            err.net = false;
            reject(err);
          }
        },
        fail(e) {
          const err = new Error(
            "连不上服务器（" + BASE + "）。请确认后端已启动、地址端口正确、手机与电脑同网。"
          );
          err.errMsg = e.errMsg;
          err.net = true;
          reject(err);
        },
      });
    });
  },

  // ---- 响应缓存（stale-while-revalidate 的「stale」这一步）----
  // 页面 onShow 先 cachePeek 渲染，网络回来再 cacheSet 覆盖：
  // 切 tab 不再闪「加载中」，弱网也不会白屏。
  cacheSet(key, data) {
    this.globalData.cache[key] = { at: Date.now(), data };
  },
  // 不管过没过期都拿出来（有就先用）
  cachePeek(key) {
    const c = this.globalData.cache[key];
    return c ? c.data : null;
  },
  // 只在 ttl 毫秒内算新鲜：新鲜就连网络请求都省了（ttl 传 0 表示总当新鲜）
  cacheFresh(key, ttl) {
    const c = this.globalData.cache[key];
    if (!c) return null;
    if (ttl && Date.now() - c.at > ttl) return null;
    return c.data;
  },
  cacheDel(key) {
    delete this.globalData.cache[key];
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
    this.globalData.netDown = false;
    wx.removeStorageSync("token");
  },

  // 未登录时统一跳「我的」tab（登录表单在那）
  goLogin() {
    wx.switchTab({ url: "/pages/mine/mine" });
    wx.showToast({ title: "请先登录", icon: "none" });
  },
});
