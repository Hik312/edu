// 全局：登录态 + 请求封装 + 跨页传参
//
// 账号体系与 web 端同一套（/api/mini/auth/* 签发的 token 就是 web 那个 JWT），
// 所以这里只存 token，不做第二套会话。
//
// ★ BASE 三个必须同时对：
//   ① **协议** —— 真机/正式版只允许 https（微信直接拦 http 请求）。
//      线上后端是 nginx 反代 → 127.0.0.1:8081，入口 `https://edu.312783.xyz`。
//      注意这里填的是**主机根**，路径由各接口自己带 `/api/...`。
//   ② **主机** —— 开发者工具/真机调试勾上「不校验合法域名」才允许 localhost；
//      `127.0.0.1` 在真机指的是**手机自己**，本地联调要换成电脑的局域网 IP，
//      且手机和电脑同一 Wi-Fi。
//   ③ **端口** —— 本地后端是 **8081**（`run.py` 默认值），不是 8080：
//      这台机器上 8080 历史上撞过 Ollama，服务器上 8080 是一个旧 Java 项目。
//      撞端口最阴的地方是**它回 200**，只是内容根本不是本项目 ——
//      所以 onLaunch 会打一次 `/api/health`，用 `framework` 字段（恒 `fastapi`）
//      证明「BASE 指的确实是 EduPath」，结果在「我的」页能看到。
//
// 本地联调就换这一行（勾掉「不校验合法域名」）：
// const BASE = "http://127.0.0.1:8081";
const BASE = "https://edu.312783.xyz";

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
    // /api/health 的自检结果（{ok, store, cards, llm, foreign} 或 {ok:false,msg}）。
    // 见 checkBackend()：「登录不行」到底是密码错还是 BASE 指错了端口，
    // 以前只能猜 —— 现在「我的」页直接写着连的是哪个后端。
    health: null,
  },

  onLaunch() {
    // 先自检后端，再验 token —— 没登录的时候这条信息最有用（登录失败多半是
    // 地址错，不是密码错），放在 token 判断之后就把未登录的用户挡在门外了。
    this.checkBackend();
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

  // 后端自检：证明 BASE 指的确实是 EduPath，而不是端口上别的服务。
  // ★ 永远 resolve（连不上也当数据回 `{ok:false,msg}`）—— 它在 onLaunch 里
  //   跑，一个未处理的 rejection 会把启动流程打断；而页面要的也只是
  //   「显示连的是哪个后端」，不是「要不要因此崩」。
  // 并发去重：onLaunch 和「我的」页 onShow 会同时来问，共用同一个请求。
  checkBackend(force) {
    const cached = this.globalData.health;
    if (!force && cached && Date.now() - cached.at < 60 * 1000) {
      return Promise.resolve(cached);
    }
    if (this._healthReq) return this._healthReq;
    this._healthReq = this.request("/api/health")
      .then((r) => ({
        ok: true,
        store: r.store,
        cards: r.cards,
        llm: !!r.llm,
        today: r.today,
        // framework 恒 'fastapi'。对不上就是打到别的服务了 —— 8080 上那个
        // 旧 Java 项目回的是 200 + JSON，看着完全像通了，这才是它难查的地方。
        foreign: r.framework !== "fastapi",
        at: Date.now(),
      }))
      .catch((e) => ({
        ok: false,
        net: !!e.net,
        // 网络不通和后端报错分开说：前者是 BASE/没起服务，后者才轮到看 msg。
        msg: e.net ? "连不上 " + BASE : e.message || "后端返回异常",
        at: Date.now(),
      }))
      .then((h) => {
        this._healthReq = null;
        this.globalData.health = h;
        return h;
      });
    return this._healthReq;
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
